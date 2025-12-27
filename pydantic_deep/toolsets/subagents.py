"""SubAgent toolset for task delegation."""

from __future__ import annotations

from typing import Union

from pydantic_ai import RunContext
from pydantic_ai.models import Model
from pydantic_ai.toolsets import FunctionToolset

from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.types import SubAgentConfig

SUBAGENT_SYSTEM_PROMPT = """
## 任务委派

你可以使用 `task` 工具将工作委派给专门的子代理。
适用场景：

1. 任务需要专门的知识或工具
2. 你想隔离复杂的子任务
3. 并行工作会有益处
4. 任务需要全新的上下文环境

子代理拥有：
- 它们自己的系统提示词和工具
- 全新的上下文（无法访问你的对话历史）
- 访问同一个文件系统

委派时：
- 提供清晰、具体的说明
- 指定预期的输出格式
- 子代理将返回其工作摘要
"""

DEFAULT_GENERAL_PURPOSE_DESCRIPTION = """
用于复杂多步骤任务的通用代理。
当任务不匹配特定的子代理类型时使用此代理。
该代理可以搜索代码、分析文件和执行研究。
"""

TASK_TOOL_DESCRIPTION = """
启动一个子代理来自主处理特定任务。

子代理将：
- 接收你的任务描述作为其提示词
- 拥有文件操作权限
- 返回其发现/行动的摘要

用于：
- 复杂的研究任务
- 多步骤操作
- 需要不同专业知识的任务
"""


def create_subagent_toolset(
    subagents: list[SubAgentConfig] | None = None,
    default_model: str | Model | None = None,
    include_general_purpose: bool = True,
    id: str | None = None,
) -> FunctionToolset[DeepAgentDeps]:
    """Create a subagent toolset for task delegation.

    Args:
        subagents: List of subagent configurations.
        default_model: Default model for subagents.
        include_general_purpose: Whether to include a general-purpose subagent.
        id: Optional unique ID for the toolset.

    Returns:
        FunctionToolset with the task tool.
    """
    subagent_configs = list(subagents or [])

    # Add general-purpose subagent if requested
    if include_general_purpose:
        gp_config = SubAgentConfig(
            name="general-purpose",
            description=DEFAULT_GENERAL_PURPOSE_DESCRIPTION,
            instructions="You are a general-purpose agent. "
            "Complete the given task thoroughly and report your findings.",
        )
        subagent_configs.append(gp_config)

    # Build description of available subagents
    subagent_descriptions = []
    for config in subagent_configs:
        subagent_descriptions.append(f"- {config['name']}: {config['description'].strip()}")

    available_subagents = (
        "\n".join(subagent_descriptions) if subagent_descriptions else "No subagents configured"
    )

    toolset: FunctionToolset[DeepAgentDeps] = FunctionToolset(id=id)

    @toolset.tool
    async def task(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        description: str,
        subagent_type: str,
    ) -> str:
        """Launch a subagent to handle a specific task.

        The subagent will work autonomously and return a summary of their work.
        Subagents have access to the same filesystem but a fresh context.

        Args:
            description: Detailed description of the task for the subagent.
            subagent_type: Type of subagent to use (e.g., "general-purpose").
        """
        # Find the subagent config
        config = None
        for c in subagent_configs:
            if c["name"] == subagent_type:
                config = c
                break

        if config is None:
            available = ", ".join(c["name"] for c in subagent_configs)
            return f"Error: Unknown subagent type '{subagent_type}'. Available: {available}"

        # Check if we have a pre-built agent
        if subagent_type in ctx.deps.subagents:
            subagent = ctx.deps.subagents[subagent_type]
        else:
            # Create the subagent using factory function to ensure proper backend reuse
            from pydantic_deep import create_deep_agent

            model = config.get("model", default_model)
            tools = config.get("tools", [])

            # Use factory function to create subagent with same backend as parent
            subagent = create_deep_agent(
                model=model,
                instructions=config["instructions"],
                backend=ctx.deps.backend,  # Reuse parent agent's DockerSandbox
                include_todos=True,
                include_filesystem=True,
                include_execute=True,
                include_skills=False,  # Subagents don't need skills system
                include_subagents=False,  # Prevent nested subagents
                include_general_purpose_subagent=False,
                enable_permission_filtering=False,
                enable_mcp_tools=False,
                tools=tools,  # Pass custom tools
            )

            # Cache the subagent
            ctx.deps.subagents[subagent_type] = subagent

        # Create isolated deps for the subagent
        subagent_deps = ctx.deps.clone_for_subagent()

        # Run the subagent
        try:
            result = await subagent.run(description, deps=subagent_deps)
            return f"Subagent '{subagent_type}' completed:\n\n{result.output}"
        except Exception as e:
            return f"Subagent '{subagent_type}' failed: {e}"

    # Update the tool's docstring with available subagents
    if task.__doc__:  # pragma: no branch
        task.__doc__ += f"\n\nAvailable subagent types:\n{available_subagents}"

    return toolset


def get_subagent_system_prompt(
    deps: DeepAgentDeps, subagent_configs: list[SubAgentConfig] | None = None
) -> str:
    """Generate dynamic system prompt for subagent tools.

    Args:
        deps: The agent dependencies.
        subagent_configs: List of subagent configurations.

    Returns:
        System prompt section for subagent tools.
    """
    prompt = SUBAGENT_SYSTEM_PROMPT

    if subagent_configs:
        prompt += "\n\n### Available Subagents\n"
        for config in subagent_configs:
            prompt += f"\n**{config['name']}**: {config['description'].strip()}\n"

    if deps.subagents:
        prompt += "\n\n### Cached Subagents\n"
        prompt += f"Active subagents: {', '.join(deps.subagents.keys())}\n"

    return prompt


# Alias for convenience
SubAgentToolset = create_subagent_toolset
