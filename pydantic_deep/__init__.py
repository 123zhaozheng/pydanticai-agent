"""pydantic-deep: Deep agent framework built on pydantic-ai.

This library provides a deep agent framework with:
- Planning via TodoToolset
- Filesystem operations via FilesystemToolset
- Subagent delegation via SubAgentToolset
- Multiple backend options for file storage
- Structured output support via output_type
- History processing/summarization for long conversations

Example:
    ```python
    from pydantic import BaseModel
    from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend
    from pydantic_deep.processors import create_summarization_processor

    # Create agent with all capabilities
    agent = create_deep_agent(
        model="openai:gpt-4.1",
        instructions="You are a helpful coding assistant",
    )

    # With structured output
    class Analysis(BaseModel):
        summary: str
        issues: list[str]

    agent = create_deep_agent(
        output_type=Analysis,
        history_processors=[
            create_summarization_processor(
                trigger=("tokens", 100000),
                keep=("messages", 20),
            )
        ],
    )

    # Create dependencies
    deps = DeepAgentDeps(backend=StateBackend())

    # Run agent
    result = await agent.run("Create a Python script", deps=deps)
    print(result.output)
    ```
"""

from pydantic_deep.agent import create_deep_agent, create_default_deps
from pydantic_deep.backends import (
    BackendProtocol,
    BaseSandbox,
    DockerSandbox,
    SandboxProtocol,
    StateBackend,
)
from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.processors import (
    SummarizationProcessor,
    create_summarization_processor,
)
from pydantic_deep.runtimes import BUILTIN_RUNTIMES, get_runtime
from pydantic_deep.sandbox_utils import (
    discover_container_files,
    get_file_info,
    list_container_directories,
)
from pydantic_deep.toolsets import FilesystemToolset, SkillsToolset, SubAgentToolset, TodoToolset
from pydantic_deep.types import (
    CompiledSubAgent,
    EditResult,
    ExecuteResponse,
    FileData,
    FileInfo,
    GrepMatch,
    ResponseFormat,
    RuntimeConfig,
    Skill,
    SkillDirectory,
    SkillFrontmatter,
    SubAgentConfig,
    Todo,
    UploadedFile,
    WriteResult,
)

__version__ = "0.1.0"

__all__ = [
    # Main entry points
    "create_deep_agent",
    "create_default_deps",
    "DeepAgentDeps",
    # Backends (recommended: DockerSandbox)
    "BackendProtocol",
    "SandboxProtocol",
    "StateBackend",  # In-memory backend for development
    "BaseSandbox",  # Abstract base class
    "DockerSandbox",  # Recommended: Isolated Docker environment
    # Note: FilesystemBackend and CompositeBackend are deprecated
    # Runtimes
    "RuntimeConfig",
    "BUILTIN_RUNTIMES",
    "get_runtime",
    # Sandbox utilities
    "discover_container_files",
    "list_container_directories",
    "get_file_info",
    # Toolsets
    "TodoToolset",
    "FilesystemToolset",
    "SubAgentToolset",
    "SkillsToolset",
    # Processors
    "SummarizationProcessor",
    "create_summarization_processor",
    # Types
    "FileData",
    "FileInfo",
    "WriteResult",
    "EditResult",
    "ExecuteResponse",
    "GrepMatch",
    "Todo",
    "SubAgentConfig",
    "CompiledSubAgent",
    "Skill",
    "SkillDirectory",
    "SkillFrontmatter",
    "UploadedFile",
    "ResponseFormat",
]
