"""Main agent factory for pydantic-deep."""

from __future__ import annotations
import logging

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar, overload

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.output import OutputSpec
from pydantic_ai.tools import Tool

from pydantic_deep.backends.protocol import BackendProtocol, SandboxProtocol
from pydantic_deep.backends.state import StateBackend
from pydantic_deep.backends.sandbox import DockerSandbox
from pydantic_deep.sandbox_config import build_sandbox_volumes
from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.toolsets.filesystem import (
    create_filesystem_toolset,
    get_filesystem_system_prompt,
)
from pydantic_deep.toolsets.skills import create_skills_toolset, get_skills_system_prompt
from pydantic_deep.toolsets.subagents import create_subagent_toolset, get_subagent_system_prompt
from pydantic_deep.toolsets.todo import create_todo_toolset, get_todo_system_prompt
from pydantic_deep.types import Skill, SkillDirectory, SubAgentConfig

if TYPE_CHECKING:
    from pydantic_ai.toolsets import AbstractToolset

OutputDataT = TypeVar("OutputDataT")


DEFAULT_MODEL = "openai:gpt-4.1"

DEFAULT_INSTRUCTIONS = """
你是一个有用的 AI 助手，可以使用规划、文件系统、子代理和技能工具。

## 能力
- **规划**：使用待办事项列表分解复杂任务并跟踪进度
- **文件系统**：读取、写入和搜索文件
- **子代理**：将专门任务委派给子代理
- **技能**：加载和使用模块化技能包以执行专门任务

## 最佳实践
1. 行动前先规划 - 对于复杂任务使用待办事项列表
2. 编辑文件前先读取
3. 开始任务时标记为进行中，完成时标记为已完成
4. 将专门工作委派给合适的子代理
5. 检查可用技能以执行专门任务 - 需要时加载技能说明

## 工具使用限制
- **最多重试 3 次**：如果同一个工具连续失败 3 次，停止重试并告知用户
- **搜索工具**：如果搜索结果不理想，最多尝试 2-3 种不同的关键词组合后就应该告知用户
- **避免无限循环**：如果发现自己在重复相同的操作，应该停下来重新思考或告知用户
6. 既要全面又要高效
"""


@overload
def create_deep_agent(
    model: str | Model | None = None,
    instructions: str | None = None,
    tools: Sequence[Tool[DeepAgentDeps] | Any] | None = None,
    toolsets: Sequence[AbstractToolset[DeepAgentDeps]] | None = None,
    subagents: list[SubAgentConfig] | None = None,
    skills: list[Skill] | None = None,
    skill_directories: list[SkillDirectory] | None = None,
    backend: BackendProtocol | None = None,
    include_todo: bool = True,
    include_filesystem: bool = True,
    include_subagents: bool = False,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    output_type: None = None,
    history_processors: Sequence | None = None,
    **agent_kwargs: Any,
) -> Agent[DeepAgentDeps, str]: ...


@overload
def create_deep_agent(
    model: str | Model | None = None,
    instructions: str | None = None,
    tools: Sequence[Tool[DeepAgentDeps] | Any] | None = None,
    toolsets: Sequence[AbstractToolset[DeepAgentDeps]] | None = None,
    subagents: list[SubAgentConfig] | None = None,
    skills: list[Skill] | None = None,
    skill_directories: list[SkillDirectory] | None = None,
    backend: BackendProtocol | None = None,
    include_todo: bool = True,
    include_filesystem: bool = True,
    include_subagents: bool = False,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    *,
    output_type: OutputSpec[OutputDataT],
    history_processors: Sequence | None = None,
    **agent_kwargs: Any,
) -> Agent[DeepAgentDeps, OutputDataT]: ...


def create_deep_agent(  # noqa: C901
    model: str | Model | None = None,
    instructions: str | None = None,
    tools: Sequence[Tool[DeepAgentDeps] | Any] | None = None,
    toolsets: Sequence[AbstractToolset[DeepAgentDeps]] | None = None,
    subagents: list[SubAgentConfig] | None = None,
    skills: list[Skill] | None = None,
    skill_directories: list[SkillDirectory] | None = None,
    backend: BackendProtocol | None = None,
    include_todo: bool = True,
    include_filesystem: bool = True,
    include_subagents: bool = False,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    output_type: OutputSpec[OutputDataT] | None = None,
    history_processors: list[Callable] | None = None,
    enable_permission_filtering: bool = False,
    enable_history_cleanup: bool = False,
    enable_mcp_tools: bool = True,
    user_id: int | None = None,
    conversation_id: int | None = None,
    # Selective tool/skill loading (for frontend control with permission intersection)
    mcp_tool_names: list[str] | None = None,  # Filter MCP tools by name (None = all)
    skill_names: list[str] | None = None,  # Filter skills by name (None = all)
    **agent_kwargs: Any,
) -> Agent[DeepAgentDeps, OutputDataT] | Agent[DeepAgentDeps, str]:
    """Create a deep agent with planning, filesystem, subagent, and skills capabilities.

    This factory function creates a fully-configured Agent with:
    - Todo toolset for task planning and tracking
    - Filesystem toolset for file operations
    - Subagent toolset for task delegation
    - Skills toolset for modular capability extension
    - Dynamic system prompts based on current state
    - Optional structured output via output_type
    - Optional history processing (e.g., summarization)
    - Optional permission-based tool and skill filtering

    Args:
        model: Model to use (default: Claude Sonnet 4).
        instructions: Custom instructions for the agent.
        tools: Additional tools to register.
        toolsets: Additional toolsets to register.
        subagents: Subagent configurations for the task tool.
        skills: Pre-loaded skills to make available.
        skill_directories: Directories to discover skills from.
        backend: File storage backend (default: StateBackend).
        include_todo: Whether to include the todo toolset.
        include_filesystem: Whether to include the filesystem toolset.
        include_subagents: Whether to include the subagent toolset.
        include_skills: Whether to include the skills toolset.
        include_general_purpose_subagent: Whether to include a general-purpose subagent.
        include_execute: Whether to include the execute tool. If None (default),
            automatically determined based on whether backend is a SandboxProtocol.
            Set to True to force include even when backend is None (useful when
            backend is provided via deps at runtime).
        output_type: Expected output structure (structured output).
        history_processors: List of async functions to process/transform conversation history.
        enable_permission_filtering: Enable role-based tool and skill permission filtering.
        enable_history_cleanup: Enable automatic history summarization when context is full.
        enable_mcp_tools: Enable MCP (Model Context Protocol) tools from database configuration.
        user_id: User ID for permission filtering and file isolation.
        conversation_id: Conversation ID for per-conversation file isolation in Docker sandbox.
        **agent_kwargs: Additional arguments passed to Agent constructor.

    Returns:
        Configured Agent instance. Returns Agent[DeepAgentDeps, OutputDataT] if
        output_type is specified, otherwise Agent[DeepAgentDeps, str].

    Example:
        ```python
        from pydantic import BaseModel
        from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend
        from pydantic_deep.processors import create_summarization_processor

        # Basic usage with string output
        agent = create_deep_agent(
            model="openai:gpt-4.1",
            instructions="You are a coding assistant",
        )

        # With structured output
        class CodeAnalysis(BaseModel):
            language: str
            issues: list[str]
            suggestions: list[str]

        agent = create_deep_agent(
            output_type=CodeAnalysis,
        )

        # With summarization for long conversations
        agent = create_deep_agent(
            history_processors=[
                create_summarization_processor(
                    trigger=("tokens", 100000),
                    keep=("messages", 20),
                )
            ],
        )

        deps = DeepAgentDeps(backend=StateBackend())
        result = await agent.run("Analyze this code", deps=deps)
        ```
    """
    model = model or DEFAULT_MODEL

    # Initialize backend (defaults to StateBackend)
    if backend is None:
        backend = StateBackend()  # In-memory state; use DockerSandbox for execution

    # Build toolsets list
    all_toolsets: list[AbstractToolset[DeepAgentDeps]] = []

    if include_todo:
        todo_toolset = create_todo_toolset(id="deep-todo")
        all_toolsets.append(todo_toolset)

    if include_filesystem:
        # Determine if execute should be included
        # If explicitly set, use that; otherwise auto-detect from backend type
        should_include_execute = (
            include_execute if include_execute is not None else isinstance(backend, SandboxProtocol)
        )

        fs_toolset = create_filesystem_toolset(
            id="deep-filesystem",
            include_execute=should_include_execute,
            require_write_approval=False,  # No approval required
            require_execute_approval=False,  # No approval required
        )
        all_toolsets.append(fs_toolset)

    if include_subagents:
        # For subagents, convert model to string if it's a Model instance
        subagent_model = model if isinstance(model, str) else DEFAULT_MODEL
        subagent_toolset = create_subagent_toolset(
            id="deep-subagents",
            subagents=subagents,
            default_model=subagent_model,
            include_general_purpose=include_general_purpose_subagent,
        )
        all_toolsets.append(subagent_toolset)

    # Skills toolset
    loaded_skills: list[Skill] = []
    if include_skills:
        # Discover or load skills first
        if skills:
            initial_skills = skills
        elif skill_directories:
            from pydantic_deep.toolsets.skills import discover_skills
            initial_skills = discover_skills(skill_directories)
        else:
            initial_skills = []
        
        # Filter skills by name if specified (frontend selection)
        if skill_names is not None and initial_skills:
            initial_skills = [s for s in initial_skills if s.get("name") in skill_names]
        
        # Filter skills by permission if enabled
        # Note: This requires deps.user_id to be set when running the agent
        # The filtering will happen at runtime based on the user
        skills_toolset = create_skills_toolset(
            id="deep-skills",
            directories=skill_directories,
            skills=initial_skills,  # Use filtered skills
        )
        all_toolsets.append(skills_toolset)
        
        # Track loaded skills for system prompt
        loaded_skills = initial_skills

    # Add user-provided toolsets
    if toolsets:
        all_toolsets.extend(toolsets)

    # Build base instructions
    base_instructions = instructions or DEFAULT_INSTRUCTIONS

    # Build agent creation kwargs
    agent_create_kwargs: dict[str, Any] = {
        "deps_type": DeepAgentDeps,
        "toolsets": all_toolsets,
        "instructions": base_instructions,
        "history_processors": history_processors or [],
    }
    
    # Load MCP tools if enabled (creates fresh connection per agent)
    if enable_mcp_tools:
        try:
            from pydantic_deep.toolsets.mcp import create_mcp_toolset
            mcp_toolset = create_mcp_toolset()
            if mcp_toolset:
                all_toolsets.append(mcp_toolset)
                print(f"✅ Created MCP toolset for this agent")
            else:
                print("ℹ️  No MCP servers configured")
        except Exception as e:
            print(f"❌ Failed to create MCP toolset: {e}")
    
    # Update toolsets in kwargs
    agent_create_kwargs["toolsets"] = all_toolsets

    # Set output_type if provided
    if output_type is not None:
        agent_create_kwargs["output_type"] = output_type

    if history_processors is not None:
        agent_create_kwargs["history_processors"] = list(history_processors)

    # Add permission filtering if enabled
    if enable_permission_filtering:
        from pydantic_deep.tool_filter import create_permission_filter
        agent_create_kwargs["prepare_tools"] = create_permission_filter()

    agent_create_kwargs.update(agent_kwargs)

    # Log toolsets for debugging
    logger = logging.getLogger(__name__)
    toolset_names = [t.id if hasattr(t, 'id') else str(type(t).__name__) for t in all_toolsets]
    logger.info(f"[DeepAgent] Creating agent with {len(all_toolsets)} toolsets: {toolset_names}")

    # Create the agent (deps will be passed at runtime via agent.run())
    agent: Agent[DeepAgentDeps, Any] = Agent(
        model,
        **agent_create_kwargs,
    )

    # Add dynamic system prompts
    @agent.instructions
    async def dynamic_instructions(ctx: Any) -> str:  # pragma: no cover
        """Generate dynamic instructions based on current state."""
        parts = []

        # Show available files (from volume mounts or uploads)
        files_prompt = ctx.deps.get_files_summary()
        if files_prompt:
            parts.append(files_prompt)

        if include_todo:
            todo_prompt = get_todo_system_prompt(ctx.deps)
            if todo_prompt:
                parts.append(todo_prompt)

        if include_filesystem:
            fs_prompt = get_filesystem_system_prompt(ctx.deps)
            if fs_prompt:
                parts.append(fs_prompt)

        if include_subagents:
            subagent_prompt = get_subagent_system_prompt(ctx.deps, subagents)
            if subagent_prompt:
                parts.append(subagent_prompt)

        if include_skills and loaded_skills:
            # Filter skills by user permission before showing in system prompt
            filtered_skills = loaded_skills
            if enable_permission_filtering and hasattr(ctx.deps, 'user_id') and ctx.deps.user_id:
                try:
                    from pydantic_deep.skill_filter import filter_skills_by_permission
                    filtered_skills = await filter_skills_by_permission(
                        loaded_skills, 
                        ctx.deps.user_id, 
                        ctx.deps
                    )
                except Exception as e:
                    # Permission check failed, fall back to showing all (backward compatible)
                    print(f"Skill permission filtering in system prompt failed: {e}")
            
            skills_prompt = get_skills_system_prompt(ctx.deps, filtered_skills)
            if skills_prompt:
                parts.append(skills_prompt)

        return "\n\n".join(parts) if parts else ""

    # Add user-provided tools
    if tools:
        for tool in tools:
            if isinstance(tool, Tool):
                agent.tool(tool.function)  # pragma: no cover
            else:
                agent.tool(tool)

    return agent


def create_default_deps(
    backend: BackendProtocol | None = None,
) -> DeepAgentDeps:
    """Create default dependencies for a deep agent.

    Args:
        backend: File storage backend (default: StateBackend).

    Returns:
        DeepAgentDeps instance.
    """
    return DeepAgentDeps(backend=backend or StateBackend())


