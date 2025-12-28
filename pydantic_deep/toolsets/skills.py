"""Skills toolset for pydantic-deep agents.

Skills are modular packages that extend agent capabilities. Each skill is a folder
containing a SKILL.md file with YAML frontmatter and Markdown instructions, along
with optional resource files (documents, scripts, etc.).

Progressive disclosure: Only YAML frontmatter is loaded by default. The full
instructions are loaded on-demand when the agent needs them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.types import Skill, SkillDirectory

if TYPE_CHECKING:
    pass


# Default skills directory (can be overridden)
DEFAULT_SKILLS_DIR = "~/.pydantic-deep/skills"


def parse_skill_md(content: str) -> tuple[dict[str, Any], str]:
    """Parse a SKILL.md file into frontmatter and instructions.

    Args:
        content: Full content of the SKILL.md file.

    Returns:
        Tuple of (frontmatter_dict, instructions_markdown).
    """
    # Match YAML frontmatter between --- delimiters
    frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n?"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        # No frontmatter, treat entire content as instructions
        return {}, content.strip()

    frontmatter_yaml = match.group(1)
    instructions = content[match.end() :].strip()

    # Parse YAML manually (simple key: value format)
    frontmatter: dict[str, Any] = {}
    current_key = None
    current_list: list[str] | None = None

    for line in frontmatter_yaml.split("\n"):
        line = line.rstrip()

        # Skip empty lines
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
                if (
                    value.startswith('"')
                    and value.endswith('"')
                    or value.startswith("'")
                    and value.endswith("'")
                ):
                    value = value[1:-1]
                frontmatter[key] = value
            # If no value, might be a list (will be populated by subsequent lines)

    return frontmatter, instructions


def discover_skills(
    directories: list[SkillDirectory],
    backend: Any | None = None,
) -> list[Skill]:
    """Discover skills from the filesystem.

    Args:
        directories: List of directories to search for skills.
        backend: Optional backend for virtual filesystem support.

    Returns:
        List of discovered skills (frontmatter only).
    """
    skills: list[Skill] = []

    for skill_dir in directories:
        dir_path = Path(skill_dir["path"]).expanduser()
        recursive = skill_dir.get("recursive", True)

        if not dir_path.exists():
            continue

        # Find all SKILL.md files
        pattern = "**/SKILL.md" if recursive else "*/SKILL.md"
        for skill_file in dir_path.glob(pattern):
            try:
                content = skill_file.read_text()
                frontmatter, _ = parse_skill_md(content)

                if not frontmatter.get("name"):
                    # Skip skills without a name
                    continue

                # Get list of resources (other files in the skill directory)
                skill_folder = skill_file.parent
                resources = [
                    str(f.relative_to(skill_folder))
                    for f in skill_folder.iterdir()
                    if f.is_file() and f.name != "SKILL.md"
                ]

                skill: Skill = {
                    "name": frontmatter.get("name", skill_folder.name),
                    "description": frontmatter.get("description", ""),
                    "path": str(skill_folder),
                    "tags": frontmatter.get("tags", []),
                    "version": frontmatter.get("version", "1.0.0"),
                    "author": frontmatter.get("author", ""),
                    "frontmatter_loaded": True,
                }

                if resources:
                    skill["resources"] = resources

                skills.append(skill)

            except Exception:  # pragma: no cover
                # Skip invalid skill files
                continue

    return skills


def discover_skills_from_directory(
    skills_dir: Path | str,
    skill_names: list[str] | None = None,
) -> list[Skill]:
    """从指定目录发现技能元数据。
    
    用于在创建 Agent 之前发现技能信息，以便注入到系统提示词中。
    
    Args:
        skills_dir: 技能目录路径
        skill_names: 要加载的技能名称列表，None 表示加载全部
        
    Returns:
        技能元数据列表（包含 name, description, tags 等）
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return []
    
    skills: list[Skill] = []
    
    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
            
        skill_file = skill_folder / "SKILL.md"
        if not skill_file.exists():
            continue
            
        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_skill_md(content)
            
            skill_name = frontmatter.get("name", skill_folder.name)
            
            # 如果指定了 skill_names，只加载匹配的技能
            if skill_names is not None and skill_name not in skill_names:
                continue
            
            skill: Skill = {
                "name": skill_name,
                "description": frontmatter.get("description", ""),
                "path": str(skill_folder),
                "tags": frontmatter.get("tags", []),
                "version": frontmatter.get("version", "1.0.0"),
                "author": frontmatter.get("author", ""),
                "frontmatter_loaded": True,
            }
            
            # 获取资源文件列表
            resources = [
                f.name for f in skill_folder.iterdir()
                if f.is_file() and f.name != "SKILL.md"
            ]
            if resources:
                skill["resources"] = resources
                
            skills.append(skill)
            
        except Exception:
            continue
    
    return skills


def load_skill_instructions(skill_path: str) -> str:
    """Load full instructions for a skill.

    Args:
        skill_path: Path to the skill directory.

    Returns:
        Full markdown instructions from SKILL.md.
    """
    skill_file = Path(skill_path) / "SKILL.md"

    if not skill_file.exists():
        return f"Error: SKILL.md not found at {skill_path}"

    content = skill_file.read_text()
    _, instructions = parse_skill_md(content)

    return instructions


def get_skills_system_prompt(
    deps: DeepAgentDeps,
    skills: list[Skill] | None = None,
) -> str:
    """Generate system prompt for skills.

    Args:
        deps: Agent dependencies.
        skills: List of available skills.

    Returns:
        System prompt section describing available skills.
    """
    if not skills:
        return ""

    lines = [
        "## 可用技能",
        "",
        "您可以访问扩展您能力的技能。这些技能是专门设计的模块化能力包，包含针对特定任务的详细指导和资源。",
        "",
        "### ⚠️ 技能优先原则（重要）",
        "",
        "**当用户的问题或任务与某个技能高度匹配时，请务必优先使用对应的技能来完成任务。**",
        "",
        "技能使用流程：",
        "1. 首先查看下方的技能列表，判断用户任务是否匹配某个技能",
        "2. 如果匹配，使用 `load_skill` 加载该技能的完整说明",
        "3. 严格按照技能说明中的步骤和方法执行任务",
        "4. 如果技能包含资源文件（脚本、模板等），优先使用这些资源",
        "",
        "**为什么要优先使用技能？**",
        "- 技能包含经过验证的最佳实践和标准流程",
        "- 技能资源（脚本、模板）可以大幅提高效率和准确性",
        "- 技能说明针对特定场景进行了优化",
        "",
        "### 可用技能列表",
        "",
    ]

    for skill in skills:
        tags_str = ", ".join(skill["tags"]) if skill["tags"] else ""
        tags_part = f" [{tags_str}]" if tags_str else ""
        lines.append(f"- **{skill['name']}**{tags_part}: {skill['description']}")

    return "\n".join(lines)


class SkillsToolset(FunctionToolset[DeepAgentDeps]):
    """Toolset for skills functionality."""

    pass


def create_skills_toolset(  # noqa: C901
    *,
    id: str = "skills",
    directories: list[SkillDirectory] | None = None,  # Kept for backwards compatibility
    skills: list[Skill] | None = None,  # Kept for backwards compatibility
) -> SkillsToolset:
    """Create a skills toolset.

    Note: In the sandbox-based implementation, skills are discovered dynamically
    from /workspace/skills/ at runtime, so the directories and skills parameters
    are no longer used but kept for API backwards compatibility.

    Args:
        id: Unique identifier for this toolset.
        directories: (Deprecated) List of directories to discover skills from.
        skills: (Deprecated) Pre-loaded skills.

    Returns:
        Configured SkillsToolset instance.
    """
    # Suppress unused parameter warnings
    _ = directories
    _ = skills

    toolset = SkillsToolset(id=id)

    # Note: Skills are now discovered dynamically from the container at runtime.
    # The directories/skills parameters are kept for backwards compatibility
    # but are not used in the sandbox-based implementation.

    @toolset.tool
    async def list_skills(ctx: RunContext[DeepAgentDeps]) -> str:  # pragma: no cover
        """List all available skills from the container.

        Scans /workspace/skills/ directory in the sandbox for SKILL.md files
        and returns their metadata.

        Returns:
            Formatted list of available skills.
        """
        backend = ctx.deps.backend

        # Find all SKILL.md files in the skills directory
        result = backend.execute("find /workspace/skills -name 'SKILL.md' -type f 2>/dev/null || echo ''")

        if result.exit_code != 0 or not result.output.strip():
            return "No skills available. The /workspace/skills directory is empty or not mounted."

        skill_paths = [p for p in result.output.strip().split("\n") if p]

        if not skill_paths:
            return "No skills available."

        lines = ["Available Skills:", ""]

        for skill_md_path in sorted(skill_paths):
            try:
                # Read SKILL.md file from container (use cat directly, not backend.read() which adds line numbers)
                read_result = backend.execute(f"cat {skill_md_path}")
                if read_result.exit_code != 0:
                    continue
                content = read_result.output

                if "Error:" in content:
                    continue

                # Parse frontmatter
                frontmatter, _ = parse_skill_md(content)

                if not frontmatter.get("name"):
                    continue

                # Get skill directory path
                skill_dir = skill_md_path.rsplit("/", 1)[0]

                # List resource files (excluding SKILL.md)
                resources_result = backend.execute(
                    f"find {skill_dir} -type f ! -name 'SKILL.md' -exec basename {{}} \\; 2>/dev/null || echo ''"
                )
                resources = []
                if resources_result.exit_code == 0 and resources_result.output.strip():
                    resources = [r for r in resources_result.output.strip().split("\n") if r]

                # Format output
                name = frontmatter.get("name", "Unknown")
                description = frontmatter.get("description", "")
                version = frontmatter.get("version", "1.0.0")
                tags = frontmatter.get("tags", [])
                tags_str = ", ".join(tags) if tags else "none"
                resources_str = f" (resources: {', '.join(resources)})" if resources else ""

                lines.append(f"**{name}** (v{version})")
                lines.append(f"  Description: {description}")
                lines.append(f"  Tags: {tags_str}")
                lines.append(f"  Path: {skill_dir}{resources_str}")
                lines.append("")

            except Exception as e:
                # Skip invalid skills
                import logfire
                logfire.warn("Error reading skill", skill_path=str(skill_md_path), error=str(e))
                continue

        if len(lines) == 2:  # Only header, no skills parsed
            return "No valid skills found."

        return "\n".join(lines)

    @toolset.tool
    async def load_skill(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        skill_name: str,
    ) -> str:
        """Load full instructions for a skill from the container.

        Searches for the skill by name in /workspace/skills/ and loads
        the complete SKILL.md content.

        Args:
            skill_name: Name of the skill to load.

        Returns:
            Full skill instructions in markdown format.
        """
        backend = ctx.deps.backend

        # Find skill directory by name
        find_result = backend.execute(
            f"find /workspace/skills -type d -name '*{skill_name}*' 2>/dev/null || echo ''"
        )

        if find_result.exit_code != 0 or not find_result.output.strip():
            return f"Error: Skill '{skill_name}' not found in /workspace/skills/"

        skill_dirs = [d for d in find_result.output.strip().split("\n") if d]

        if not skill_dirs:
            return f"Error: Skill '{skill_name}' not found."

        # Use the first match (could be improved with exact name matching)
        skill_dir = skill_dirs[0]
        skill_md_path = f"{skill_dir}/SKILL.md"

        # Check if SKILL.md exists
        check_result = backend.execute(f"test -f {skill_md_path} && echo 'exists' || echo 'not found'")

        if "not found" in check_result.output:
            return f"Error: SKILL.md not found in {skill_dir}"

        # Read SKILL.md
        content = backend.read(skill_md_path)

        if "Error:" in content:
            return f"Error reading SKILL.md: {content}"

        # Parse content
        frontmatter, instructions = parse_skill_md(content)

        # List resources
        resources_result = backend.execute(
            f"find {skill_dir} -type f ! -name 'SKILL.md' -exec basename {{}} \\; 2>/dev/null || echo ''"
        )
        resources = []
        if resources_result.exit_code == 0 and resources_result.output.strip():
            resources = [r for r in resources_result.output.strip().split("\n") if r]

        # Format response
        name = frontmatter.get("name", skill_name)
        version = frontmatter.get("version", "1.0.0")

        lines = [
            f"# Skill: {name}",
            f"Version: {version}",
            f"Path: {skill_dir}",
            "",
            "## Instructions",
            "",
            instructions,
        ]

        if resources:
            lines.extend(
                [
                    "",
                    "## Available Resources",
                    "",
                ]
            )
            for resource in resources:
                lines.append(f"- {skill_dir}/{resource}")
                lines.append(f"  Use `read_skill_resource('{name}', '{resource}')` to read this file")

        return "\n".join(lines)

    @toolset.tool
    async def read_skill_resource(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        skill_name: str,
        resource_name: str,
    ) -> str:
        """Read a resource file from a skill in the container.

        Skills can include additional files (scripts, templates, documents)
        that support their functionality.

        Args:
            skill_name: Name of the skill.
            resource_name: Name of the resource file within the skill.

        Returns:
            Content of the resource file.
        """
        backend = ctx.deps.backend

        # Find skill directory
        find_result = backend.execute(
            f"find /workspace/skills -type d -name '*{skill_name}*' 2>/dev/null || echo ''"
        )

        if find_result.exit_code != 0 or not find_result.output.strip():
            return f"Error: Skill '{skill_name}' not found."

        skill_dirs = [d for d in find_result.output.strip().split("\n") if d]

        if not skill_dirs:
            return f"Error: Skill '{skill_name}' not found."

        skill_dir = skill_dirs[0]

        # Construct resource path
        # Security: Use basename to prevent directory traversal
        safe_resource_name = resource_name.split("/")[-1]
        resource_path = f"{skill_dir}/{safe_resource_name}"

        # Check if resource exists
        check_result = backend.execute(f"test -f {resource_path} && echo 'exists' || echo 'not found'")

        if "not found" in check_result.output:
            # List available resources
            list_result = backend.execute(
                f"find {skill_dir} -type f ! -name 'SKILL.md' -exec basename {{}} \\; 2>/dev/null || echo ''"
            )
            available = []
            if list_result.exit_code == 0 and list_result.output.strip():
                available = [r for r in list_result.output.strip().split("\n") if r]

            return f"Error: Resource '{resource_name}' not found. Available resources: {', '.join(available) if available else 'none'}"

        # Read resource
        content = backend.read(resource_path)

        if "Error:" in content:
            return f"Error reading resource: {content}"

        return content

    @toolset.tool
    async def execute_skill_script(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        skill_name: str,
        script_name: str,
        args: str = "",
        working_dir: str = "/workspace/intermediate",
    ) -> str:
        """Execute a script from a skill in the container.

        The script will be executed with the specified arguments, and the
        working directory will be set to /workspace/intermediate by default.

        Args:
            skill_name: Name of the skill containing the script.
            script_name: Name of the script file to execute.
            args: Command-line arguments to pass to the script (optional).
            working_dir: Working directory for script execution (default: /workspace/intermediate).

        Returns:
            Script output including exit code.
        """
        backend = ctx.deps.backend

        # Find skill directory
        find_result = backend.execute(
            f"find /workspace/skills -type d -name '*{skill_name}*' 2>/dev/null || echo ''"
        )

        if find_result.exit_code != 0 or not find_result.output.strip():
            return f"Error: Skill '{skill_name}' not found."

        skill_dirs = [d for d in find_result.output.strip().split("\n") if d]

        if not skill_dirs:
            return f"Error: Skill '{skill_name}' not found."

        skill_dir = skill_dirs[0]

        # Construct script path (security: use basename)
        safe_script_name = script_name.split("/")[-1]
        script_path = f"{skill_dir}/{safe_script_name}"

        # Check if script exists
        check_result = backend.execute(f"test -f {script_path} && echo 'exists' || echo 'not found'")

        if "not found" in check_result.output:
            return f"Error: Script '{script_name}' not found in skill '{skill_name}'."

        # Execute script
        # Change to working directory and execute
        command = f"cd {working_dir} && bash {script_path} {args}"
        result = backend.execute(command, timeout=300)

        # Format output
        lines = [
            f"Script: {script_path}",
            f"Working Directory: {working_dir}",
            f"Exit Code: {result.exit_code}",
            "",
            "Output:",
            result.output,
        ]

        if result.truncated:
            lines.append("")
            lines.append("(Output was truncated due to size limit)")

        return "\n".join(lines)

    return toolset
