"""Dependency injection container for deep agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic_deep.backends.protocol import BackendProtocol
from pydantic_deep.backends.state import StateBackend
from pydantic_deep.clients import DbClient, RedisClient
from pydantic_deep.types import Todo

if TYPE_CHECKING:
    pass


@dataclass
class DeepAgentDeps:
    """Dependencies for deep agents.

    This container holds all the state and resources needed by the agent
    and its tools during execution.

    Attributes:
        backend: File storage backend (StateBackend, DockerSandbox, etc.)
        db: Database client for permission checks and metadata
        redis: Redis client for caching
        user_id: User ID for permission filtering
        conversation_id: Conversation ID for file isolation in Docker sandbox
        file_paths: List of file paths available in the workspace (for volume-mounted files)
        todos: Task list for planning
        subagents: Pre-configured subagents available for delegation
    """

    backend: BackendProtocol = field(default_factory=StateBackend)
    db: DbClient = field(default_factory=DbClient)
    redis: RedisClient = field(default_factory=RedisClient)
    user_id: int | str | None = None  # For permission checks
    conversation_id: int | None = None  # For per-conversation file isolation
    file_paths: list[str] = field(default_factory=list)  # Available file paths in container
    todos: list[Todo] = field(default_factory=list)
    subagents: dict[str, Any] = field(default_factory=dict)  # Agent instances

    def __post_init__(self) -> None:
        """Initialize backend (currently a no-op, reserved for future use)."""
        pass

    def get_todo_prompt(self) -> str:
        """Generate system prompt section for todos."""
        if not self.todos:
            return ""

        lines = ["## Current Todos"]
        for todo in self.todos:
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[*]",
                "completed": "[x]",
            }.get(todo.status, "[ ]")
            lines.append(f"- {status_icon} {todo.content}")

        return "\n".join(lines)

    def get_files_summary(self) -> str:
        """Generate summary of available files from file_paths.
        
        This tells the agent which files are available in the container
        via volume mounts, without storing file contents in memory.
        """
        if not self.file_paths:
            return ""

        lines = ["## Available Files"]
        lines.append("")
        lines.append("The following files are available in the workspace:")
        lines.append("")
        
        for path in sorted(self.file_paths):
            lines.append(f"- `{path}`")
        
        lines.append("")
        lines.append("Use `read_file(path)` to view file contents, `grep(pattern, path)` to search,")
        lines.append("or `execute` to process these files with shell commands.")

        return "\n".join(lines)

    def get_subagents_summary(self) -> str:
        """Generate summary of available subagents."""
        if not self.subagents:
            return ""

        lines = ["## Available Subagents"]
        for name in sorted(self.subagents.keys()):
            lines.append(f"- {name}")

        return "\n".join(lines)



    def clone_for_subagent(self) -> DeepAgentDeps:
        """Create a new deps instance for a subagent.

        Subagents get:
        - Same backend (shared)
        - Same user_id (for permission checks)
        - Same conversation_id (for file isolation)
        - Same file_paths (shared file access)
        - Empty todos (isolated)
        - Empty subagents (no nested delegation)
        """
        return DeepAgentDeps(
            backend=self.backend,
            db=self.db,
            redis=self.redis,
            user_id=self.user_id,  # Preserve user_id for permissions
            conversation_id=self.conversation_id,  # Preserve conversation_id for file isolation
            file_paths=self.file_paths,  # Shared file paths
            todos=[],  # Fresh todo list
            subagents={},  # No nested subagents
        )


