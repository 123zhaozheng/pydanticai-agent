"""API endpoints for Skill management."""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.skill_service import SkillService

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ===== Response Models =====

class SkillResponse(BaseModel):
    """Response model for a skill."""
    id: int
    name: str
    description: str | None
    path: str
    version: str
    author: str | None
    tags: list[str] | None
    resources: list[str] | None
    is_active: bool
    
    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Response model for skill list."""
    skills: list[SkillResponse]
    total: int


class PermissionRequest(BaseModel):
    """Request model for adding permission."""
    can_use: bool = True
    can_manage: bool = False


class DepartmentPermissionRequest(BaseModel):
    """Request model for department permission."""
    is_allowed: bool = True


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True


# ===== Skill CRUD Endpoints =====

@router.get("", response_model=SkillListResponse)
async def list_skills(
    user_id: int = 1,  # TODO: Get from JWT token
    include_inactive: bool = Query(False, description="包含未激活的技能"),
    db: Session = Depends(get_db),
):
    """
    获取技能列表。
    
    - 默认只返回激活的技能
    - 按 user_id 的权限过滤技能
    """
    service = SkillService(db)
    skills = service.list_skills(
        include_inactive=include_inactive,
        user_id=user_id,
    )
    return SkillListResponse(skills=skills, total=len(skills))


@router.get("/{name}", response_model=SkillResponse)
async def get_skill(
    name: str,
    db: Session = Depends(get_db),
):
    """获取技能详情。"""
    service = SkillService(db)
    skill = service.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"技能 '{name}' 不存在")
    return skill


@router.post("/upload", response_model=SkillResponse)
async def upload_skill(
    file: UploadFile = File(..., description="技能 ZIP 文件 (包含 SKILL.md)"),
    user_id: int = Query(1, description="上传者用户 ID"),
    db: Session = Depends(get_db),
):
    """
    上传技能 ZIP 文件。
    
    ZIP 文件结构要求:
    - 包含 SKILL.md 文件
    - SKILL.md 中必须有 name 字段
    
    示例: pdf.zip 包含 pdf/SKILL.md
    """
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="请上传 .zip 文件")
    
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        service = SkillService(db)
        skill = service.upload_skill(tmp_path, created_by=user_id)
        return skill
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@router.delete("/{name}", response_model=MessageResponse)
async def delete_skill(
    name: str,
    delete_files: bool = Query(True, description="是否同时删除技能目录"),
    db: Session = Depends(get_db),
):
    """
    删除技能。
    
    - 默认同时删除技能目录和数据库记录
    - 设置 delete_files=false 仅删除数据库记录
    """
    service = SkillService(db)
    success = service.delete_skill(name, delete_files=delete_files)
    if not success:
        raise HTTPException(status_code=404, detail=f"技能 '{name}' 不存在")
    return MessageResponse(message=f"技能 '{name}' 已删除")


@router.post("/{name}/deactivate", response_model=MessageResponse)
async def deactivate_skill(
    name: str,
    db: Session = Depends(get_db),
):
    """停用技能 (不删除文件)。"""
    service = SkillService(db)
    success = service.deactivate_skill(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"技能 '{name}' 不存在")
    return MessageResponse(message=f"技能 '{name}' 已停用")


# ===== Permission Endpoints =====

@router.post("/{name}/permissions/role/{role_id}", response_model=MessageResponse)
async def add_role_permission(
    name: str,
    role_id: int,
    body: PermissionRequest,
    db: Session = Depends(get_db),
):
    """为角色添加技能权限。"""
    service = SkillService(db)
    perm = service.add_role_permission(
        name, role_id, 
        can_use=body.can_use,
        can_manage=body.can_manage,
    )
    if not perm:
        raise HTTPException(status_code=404, detail=f"技能 '{name}' 不存在")
    return MessageResponse(message=f"已为角色 {role_id} 添加技能 '{name}' 权限")


@router.delete("/{name}/permissions/role/{role_id}", response_model=MessageResponse)
async def remove_role_permission(
    name: str,
    role_id: int,
    db: Session = Depends(get_db),
):
    """移除角色的技能权限。"""
    service = SkillService(db)
    success = service.remove_role_permission(name, role_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"权限不存在")
    return MessageResponse(message=f"已移除角色 {role_id} 的技能 '{name}' 权限")


@router.post("/{name}/permissions/department/{department_id}", response_model=MessageResponse)
async def add_department_permission(
    name: str,
    department_id: int,
    body: DepartmentPermissionRequest,
    db: Session = Depends(get_db),
):
    """为部门添加技能权限。"""
    service = SkillService(db)
    perm = service.add_department_permission(
        name, department_id,
        is_allowed=body.is_allowed,
    )
    if not perm:
        raise HTTPException(status_code=404, detail=f"技能 '{name}' 不存在")
    return MessageResponse(message=f"已为部门 {department_id} 添加技能 '{name}' 权限")


@router.delete("/{name}/permissions/department/{department_id}", response_model=MessageResponse)
async def remove_department_permission(
    name: str,
    department_id: int,
    db: Session = Depends(get_db),
):
    """移除部门的技能权限。"""
    service = SkillService(db)
    success = service.remove_department_permission(name, department_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"权限不存在")
    return MessageResponse(message=f"已移除部门 {department_id} 的技能 '{name}' 权限")


# ===== Utility Endpoints =====

@router.get("/{name}/allowed-users", response_model=list[int])
async def get_allowed_users(
    name: str,
    db: Session = Depends(get_db),
):
    """获取有权访问该技能的用户 ID 列表。"""
    # TODO: Implement reverse lookup
    raise HTTPException(status_code=501, detail="尚未实现")
