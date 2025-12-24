"""Main agent factory for pydantic-deep."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar, overload

from pydantic_ai import Agent
from pydantic_ai._agent_graph import HistoryProcessor
from pydantic_ai.models import Model
from pydantic_ai.output import OutputSpec
from pydantic_ai.tools import DeferredToolRequests, Tool

from pydantic_deep.backends.protocol import BackendProtocol, SandboxProtocol
from pydantic_deep.backends.state import StateBackend
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
You are a helpful AI assistant with access to planning, filesystem, subagent, and skills tools.

## Capabilities
- **Planning**: Use the todo list to break down complex tasks and track progress
- **Filesystem**: Read, write, and search files
- **Subagents**: Delegate specialized tasks to subagents
- **Skills**: Load and use modular skill packages for specialized tasks

## Best Practices
1. Plan before acting - use the todo list for complex tasks
2. Read files before editing them
3. Mark tasks as in_progress when starting, completed when done
4. Delegate specialized work to appropriate subagents
5. Check available skills for specialized tasks - load skill instructions when needed
6. Be thorough but efficient
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
    include_subagents: bool = True,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    interrupt_on: dict[str, bool] | None = None,
    output_type: None = None,
    history_processors: Sequence[HistoryProcessor[DeepAgentDeps]] | None = None,
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
    include_subagents: bool = True,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    interrupt_on: dict[str, bool] | None = None,
    *,
    output_type: OutputSpec[OutputDataT],
    history_processors: Sequence[HistoryProcessor[DeepAgentDeps]] | None = None,
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
    include_subagents: bool = True,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    include_execute: bool | None = None,
    interrupt_on: dict[str, bool] | None = None,
    output_type: OutputSpec[OutputDataT] | None = None,
    history_processors: list[Callable] | None = None,
    enable_permission_filtering: bool = False,
    enable_history_cleanup: bool = False,
    enable_mcp_tools: bool = False,
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
        interrupt_on: Map of tool names to approval requirements.
            e.g., {"execute": True, "write_file": True}
        output_type: Structured output type (Pydantic model, dataclass, TypedDict).
            When specified, the agent will return this type instead of str.
        history_processors: Sequence of history processors to apply to messages
            before sending to the model. Useful for summarization, filtering, etc.
        enable_permission_filtering: Enable role-based tool and skill filtering.
            When True, tools and skills are filtered based on user permissions
            from database. Requires deps.user_id to be set.
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
    backend = backend or StateBackend()
    interrupt_on = interrupt_on or {}

    # Build toolsets list
    all_toolsets: list[AbstractToolset[DeepAgentDeps]] = []

    if include_todo:
        todo_toolset = create_todo_toolset(id="deep-todo")
        all_toolsets.append(todo_toolset)

    if include_filesystem:
        # Determine approval requirements from interrupt_on
        require_write_approval = interrupt_on.get("write_file", False) or interrupt_on.get(
            "edit_file", False
        )
        require_execute_approval = interrupt_on.get("execute", True)

        # Determine if execute should be included
        # If explicitly set, use that; otherwise auto-detect from backend type
        should_include_execute = (
            include_execute if include_execute is not None else isinstance(backend, SandboxProtocol)
        )

        fs_toolset = create_filesystem_toolset(
            id="deep-filesystem",
            include_execute=should_include_execute,
            require_write_approval=require_write_approval,
            require_execute_approval=require_execute_approval,
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
        
        # Filter skills by permission if enabled
        # Note: This requires deps.user_id to be set when running the agent
        # The filtering will happen at runtime based on the user
        skills_toolset = create_skills_toolset(
            id="deep-skills",
            directories=skill_directories,
            skills=skills,
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
    
    # Load MCP tools if enabled
    if enable_mcp_tools:
        try:
            from pydantic_ai.toolsets.fastmcp import FastMCPToolset
            from pydantic_deep.mcp_config import load_mcp_config_from_db
            
            # Load MCP config from database
            mcp_config = load_mcp_config_from_db()
            
            if mcp_config and mcp_config.get('mcpServers'):
                mcp_toolset = FastMCPToolset(mcp_config)
                all_toolsets.append(mcp_toolset)
                print(f"Loaded {len(mcp_config['mcpServers'])} MCP servers")
        except ImportError:
            print("FastMCPToolset not available (pydantic-ai version may be outdated)")
        except Exception as e:
            print(f"Failed to load MCP tools: {e}")
    
    # Update toolsets in kwargs
    agent_create_kwargs["toolsets"] = all_toolsets

    # Determine if any tools require approval (interrupt_on has True values)
    has_interrupt_tools = any(interrupt_on.values())

    if output_type is not None:
        # If interrupt_on is used, combine output_type with DeferredToolRequests
        if has_interrupt_tools:
            agent_create_kwargs["output_type"] = [output_type, DeferredToolRequests]
        else:
            agent_create_kwargs["output_type"] = output_type
    elif has_interrupt_tools:
        # No custom output_type but interrupt_on is used
        agent_create_kwargs["output_type"] = [str, DeferredToolRequests]

    if history_processors is not None:
        agent_create_kwargs["history_processors"] = list(history_processors)

    # Add permission filtering if enabled
    if enable_permission_filtering:
        from pydantic_deep.tool_filter import create_permission_filter
        agent_create_kwargs["prepare_tools"] = create_permission_filter()

    agent_create_kwargs.update(agent_kwargs)

    # Log toolsets for debugging
    import logging
    logger = logging.getLogger(__name__)
    toolset_names = [t.id if hasattr(t, 'id') else str(type(t).__name__) for t in all_toolsets]
    logger.info(f"[DeepAgent] Creating agent with {len(all_toolsets)} toolsets: {toolset_names}")
    
    # Create the agent
    agent: Agent[DeepAgentDeps, Any] = Agent(
        model,
        **agent_create_kwargs,
    )

    # Add dynamic system prompts
    @agent.instructions
    async def dynamic_instructions(ctx: Any) -> str:  # pragma: no cover
        """Generate dynamic instructions based on current state."""
        parts = []

        # Show uploaded files first (most relevant for user's current task)
        uploads_prompt = ctx.deps.get_uploads_summary()
        if uploads_prompt:
            parts.append(uploads_prompt)

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


async def run_with_files(
    agent: Agent[DeepAgentDeps, OutputDataT],
    query: str,
    deps: DeepAgentDeps,
    files: list[tuple[str, bytes]] | None = None,
    *,
    upload_dir: str = "/uploads",
) -> OutputDataT:
    """Run agent with file uploads.

    This is a convenience function that uploads files to the backend
    before running the agent. The files are accessible via file tools
    (read_file, grep, glob, execute).

    Args:
        agent: The agent to run.
        query: The user query/prompt.
        deps: Agent dependencies.
        files: List of (filename, content) tuples to upload.
        upload_dir: Directory to store uploads (default: "/uploads")

    Returns:
        Agent output (type depends on agent's output_type).

    Example:
        ```python
        from pydantic_deep import create_deep_agent, DeepAgentDeps, run_with_files
        from pydantic_deep.backends import StateBackend

        agent = create_deep_agent()
        deps = DeepAgentDeps(backend=StateBackend())

        with open("sales.csv", "rb") as f:
            result = await run_with_files(
                agent,
                "Analyze the sales data and find top products",
                deps,
                files=[("sales.csv", f.read())],
            )
        ```
    """
    # Upload files (synchronous)
    for name, content in files or []:
        deps.upload_file(name, content, upload_dir=upload_dir)

    # Run agent
    result = await agent.run(query, deps=deps)
    return result.output
