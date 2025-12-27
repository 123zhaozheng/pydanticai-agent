"""Skill management service for ZIP upload, CRUD operations, and permission filtering."""

import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from src.models.tools_skills import (
    Skill,
    RoleSkillPermission,
    DepartmentSkillPermission,
)
from src.models.user_management import User


def parse_skill_md(content: str) -> tuple[dict, str]:
    """Parse SKILL.md content into frontmatter and instructions.
    
    Args:
        content: Raw SKILL.md file content.
        
    Returns:
        Tuple of (frontmatter_dict, instructions_str).
    """
    if not content.startswith("---"):
        return {}, content
    
    # Find the closing ---
    end_index = content.find("---", 3)
    if end_index == -1:
        return {}, content
    
    frontmatter_yaml = content[3:end_index].strip()
    instructions = content[end_index + 3:].strip()
    
    # Parse YAML manually (simple key: value format)
    frontmatter: dict = {}
    current_key = None
    current_list: list[str] | None = None
    
    for line in frontmatter_yaml.split("\n"):
        line = line.rstrip()
        
        if not line:
            continue
        
        # Check for list item
        if line.startswith("  - ") and current_key:
            if current_list is None:
                current_list = []
                frontmatter[current_key] = current_list
            current_list.append(line[4:].strip())
            continue
        
        # Check for key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            
            current_key = key
            current_list = None
            
            if value:
                # Handle quoted strings
                if (value.startswith('"') and value.endswith('"') or 
                    value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                frontmatter[key] = value
    
    return frontmatter, instructions


class SkillService:
    """Service for managing skill packages with permission control."""
    
    def __init__(self, db: Session, skills_base_dir: str | None = None):
        """Initialize skill service.
        
        Args:
            db: Database session.
            skills_base_dir: Base directory for skills storage. 
                            Defaults to 'skills' in project root.
        """
        self.db = db
        
        # Determine skills directory
        if skills_base_dir:
            self.skills_dir = Path(skills_base_dir)
        else:
            # Default to project root / skills
            self.skills_dir = Path(os.environ.get(
                "PYDANTIC_DEEP_BASE_DIR", 
                Path(__file__).parent.parent.parent
            )) / "skills"
        
        # Ensure skills directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)
    
    def list_skills(
        self,
        include_inactive: bool = False,
        user_id: int | None = None,
    ) -> list[Skill]:
        """List all skills, optionally filtered by user permission.
        
        Args:
            include_inactive: Whether to include inactive skills.
            user_id: If provided, filter by user's permission.
            
        Returns:
            List of Skill objects.
        """
        query = self.db.query(Skill)
        
        if not include_inactive:
            query = query.filter(Skill.is_active == True)
        
        if user_id:
            # Get allowed skill names for user
            allowed_names = self.get_allowed_skill_names(user_id)
            query = query.filter(Skill.name.in_(allowed_names))
        
        return query.order_by(Skill.name).all()
    
    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name.
        
        Args:
            name: Skill name (directory name).
            
        Returns:
            Skill object or None.
        """
        return self.db.query(Skill).filter(Skill.name == name).first()
    
    def upload_skill(
        self,
        zip_file_path: str,
        created_by: int | None = None,
    ) -> Skill:
        """Upload and extract a skill from ZIP file.
        
        The ZIP file should contain a directory with SKILL.md inside.
        Example: pdf.zip contains pdf/SKILL.md
        
        Args:
            zip_file_path: Path to the uploaded ZIP file.
            created_by: User ID who uploaded the skill.
            
        Returns:
            Created or updated Skill object.
            
        Raises:
            ValueError: If ZIP structure is invalid or SKILL.md is missing.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract ZIP
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # Find SKILL.md
            skill_md_files = list(temp_path.rglob("SKILL.md"))
            if not skill_md_files:
                raise ValueError("ZIP 文件中未找到 SKILL.md")
            
            skill_md_path = skill_md_files[0]
            skill_dir = skill_md_path.parent
            
            # Parse SKILL.md
            skill_md_content = skill_md_path.read_text(encoding="utf-8")
            frontmatter, _ = parse_skill_md(skill_md_content)
            
            # Get skill name from frontmatter or directory name
            skill_name = frontmatter.get("name") or skill_dir.name
            if not skill_name:
                raise ValueError("无法确定技能名称,请在 SKILL.md 中设置 name 字段")
            
            # Target directory
            target_dir = self.skills_dir / skill_name
            
            # Remove existing if present
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
            # Copy skill directory to skills folder
            shutil.copytree(skill_dir, target_dir)
            
            # List resource files
            resources = []
            for file_path in target_dir.iterdir():
                if file_path.is_file() and file_path.name != "SKILL.md":
                    resources.append(file_path.name)
            
            # Create or update database record
            existing = self.get_skill(skill_name)
            
            if existing:
                # Update existing
                existing.description = frontmatter.get("description", "")
                existing.version = frontmatter.get("version", "1.0.0")
                existing.author = frontmatter.get("author", "")
                existing.tags = frontmatter.get("tags", [])
                existing.path = str(target_dir)
                existing.resources = resources
                existing.frontmatter = frontmatter
                existing.is_active = True
                self.db.commit()
                return existing
            else:
                # Create new
                skill = Skill(
                    name=skill_name,
                    description=frontmatter.get("description", ""),
                    path=str(target_dir),
                    version=frontmatter.get("version", "1.0.0"),
                    author=frontmatter.get("author", ""),
                    tags=frontmatter.get("tags", []),
                    resources=resources,
                    frontmatter=frontmatter,
                    is_active=True,
                    created_by=created_by,
                )
                self.db.add(skill)
                self.db.commit()
                self.db.refresh(skill)
                return skill
    
    def delete_skill(self, name: str, delete_files: bool = True) -> bool:
        """Delete a skill by name.
        
        Args:
            name: Skill name.
            delete_files: Whether to delete the skill directory.
            
        Returns:
            True if deleted, False if not found.
        """
        skill = self.get_skill(name)
        if not skill:
            return False
        
        # Delete directory if requested
        if delete_files and skill.path:
            skill_path = Path(skill.path)
            if skill_path.exists():
                shutil.rmtree(skill_path)
        
        # Delete from database
        self.db.delete(skill)
        self.db.commit()
        return True
    
    def deactivate_skill(self, name: str) -> bool:
        """Deactivate a skill without deleting.
        
        Args:
            name: Skill name.
            
        Returns:
            True if deactivated, False if not found.
        """
        skill = self.get_skill(name)
        if not skill:
            return False
        
        skill.is_active = False
        self.db.commit()
        return True
    
    # ===== Permission Methods =====
    
    def get_allowed_skill_names(self, user_id: int) -> list[str]:
        """Get skill names that a user has permission to use.
        
        Permission logic:
        - User must have role permission (RoleSkillPermission.can_use)
        - AND department permission (DepartmentSkillPermission.is_allowed)
        - If no department permission exists, allow by default
        
        Args:
            user_id: User ID.
            
        Returns:
            List of allowed skill names.
        """
        # Get user with role and department
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        role_id = user.role_id
        department_id = user.department_id
        
        # Get all active skills
        all_skills = self.db.query(Skill).filter(Skill.is_active == True).all()
        
        allowed = []
        for skill in all_skills:
            # Check role permission
            role_perm = self.db.query(RoleSkillPermission).filter(
                and_(
                    RoleSkillPermission.role_id == role_id,
                    RoleSkillPermission.skill_id == skill.id,
                    RoleSkillPermission.can_use == True,
                )
            ).first()
            
            if not role_perm:
                # No role permission = not allowed
                continue
            
            # Check department permission
            if department_id:
                dept_perm = self.db.query(DepartmentSkillPermission).filter(
                    and_(
                        DepartmentSkillPermission.department_id == department_id,
                        DepartmentSkillPermission.skill_id == skill.id,
                    )
                ).first()
                
                # If department permission exists and is_allowed=False, skip
                if dept_perm and not dept_perm.is_allowed:
                    continue
            
            allowed.append(skill.name)
        
        return allowed
    
    def add_role_permission(
        self,
        skill_name: str,
        role_id: int,
        can_use: bool = True,
        can_manage: bool = False,
    ) -> RoleSkillPermission | None:
        """Add role permission for a skill.
        
        Args:
            skill_name: Skill name.
            role_id: Role ID.
            can_use: Whether role can use the skill.
            can_manage: Whether role can manage the skill.
            
        Returns:
            Created permission or None if skill not found.
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return None
        
        # Check if already exists
        existing = self.db.query(RoleSkillPermission).filter(
            and_(
                RoleSkillPermission.role_id == role_id,
                RoleSkillPermission.skill_id == skill.id,
            )
        ).first()
        
        if existing:
            existing.can_use = can_use
            existing.can_manage = can_manage
            self.db.commit()
            return existing
        
        perm = RoleSkillPermission(
            role_id=role_id,
            skill_id=skill.id,
            can_use=can_use,
            can_manage=can_manage,
        )
        self.db.add(perm)
        self.db.commit()
        self.db.refresh(perm)
        return perm
    
    def remove_role_permission(self, skill_name: str, role_id: int) -> bool:
        """Remove role permission for a skill.
        
        Args:
            skill_name: Skill name.
            role_id: Role ID.
            
        Returns:
            True if removed, False if not found.
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return False
        
        perm = self.db.query(RoleSkillPermission).filter(
            and_(
                RoleSkillPermission.role_id == role_id,
                RoleSkillPermission.skill_id == skill.id,
            )
        ).first()
        
        if not perm:
            return False
        
        self.db.delete(perm)
        self.db.commit()
        return True
    
    def add_department_permission(
        self,
        skill_name: str,
        department_id: int,
        is_allowed: bool = True,
    ) -> DepartmentSkillPermission | None:
        """Add department permission for a skill.
        
        Args:
            skill_name: Skill name.
            department_id: Department ID.
            is_allowed: Whether department can access the skill.
            
        Returns:
            Created permission or None if skill not found.
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return None
        
        existing = self.db.query(DepartmentSkillPermission).filter(
            and_(
                DepartmentSkillPermission.department_id == department_id,
                DepartmentSkillPermission.skill_id == skill.id,
            )
        ).first()
        
        if existing:
            existing.is_allowed = is_allowed
            self.db.commit()
            return existing
        
        perm = DepartmentSkillPermission(
            department_id=department_id,
            skill_id=skill.id,
            is_allowed=is_allowed,
        )
        self.db.add(perm)
        self.db.commit()
        self.db.refresh(perm)
        return perm
    
    def remove_department_permission(self, skill_name: str, department_id: int) -> bool:
        """Remove department permission for a skill.
        
        Args:
            skill_name: Skill name.
            department_id: Department ID.
            
        Returns:
            True if removed, False if not found.
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return False
        
        perm = self.db.query(DepartmentSkillPermission).filter(
            and_(
                DepartmentSkillPermission.department_id == department_id,
                DepartmentSkillPermission.skill_id == skill.id,
            )
        ).first()
        
        if not perm:
            return False
        
        self.db.delete(perm)
        self.db.commit()
        return True
