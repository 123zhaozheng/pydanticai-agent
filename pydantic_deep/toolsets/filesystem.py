"""Filesystem toolset for file operations."""

from __future__ import annotations

from typing import Literal

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from pydantic_deep.backends.protocol import SandboxProtocol
from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.types import GrepMatch

FILESYSTEM_SYSTEM_PROMPT = """
## 文件系统工具

你可以使用文件系统工具来读取和修改文件：

- `ls`: 列出目录中的文件
- `read_file`: 读取带行号的文件内容
- `write_file`: 创建或覆盖文件
- `edit_file`: 替换文件中的字符串
- `glob`: 查找匹配模式的文件
- `grep`: 在文件中搜索模式

### 最佳实践
- 编辑文件前务必先读取
- 小改动使用 edit_file，重写使用 write_file
- 操作文件前先用 glob 查找
"""

SANDBOX_SYSTEM_PROMPT = """
## 命令执行 (Sandbox)

你还可以使用 `execute` 工具在**隔离的沙盒环境**中运行 shell 命令。

**重要使用规则**：
1. **禁止联网安装**：沙盒是**无网隔离环境**，严禁尝试 `pip install`, `apt-get` 等联网安装命令。
2. **使用预装库**：请务必使用环境报告中列出的“已安装的库”。
3. **用途**：
   - 数据分析 (Pandas, Numpy)
   - 运行测试
   - 构建项目
   - 运行脚本
4. **安全**：对破坏性命令要谨慎（如 rm -rf）。
"""


def create_filesystem_toolset(  # noqa: C901
    id: str | None = None,
    include_execute: bool = True,
    require_write_approval: bool = False,
    require_execute_approval: bool = True,
) -> FunctionToolset[DeepAgentDeps]:
    """Create a filesystem toolset.

    Args:
        id: Optional unique ID for the toolset.
        include_execute: Whether to include the execute tool (requires SandboxProtocol backend).
        require_write_approval: Whether write_file and edit_file require approval.
        require_execute_approval: Whether execute requires approval.

    Returns:
        FunctionToolset with filesystem tools.
    """
    toolset: FunctionToolset[DeepAgentDeps] = FunctionToolset(id=id)

    @toolset.tool
    async def ls(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        path: str = "/",
    ) -> str:
        """List files and directories at the given path.

        Args:
            path: Directory path to list. Defaults to root.
        """
        entries = ctx.deps.backend.ls_info(path)

        if not entries:
            return f"Directory '{path}' is empty or does not exist"

        lines = [f"Contents of {path}:"]
        for entry in entries:
            if entry["is_dir"]:
                lines.append(f"  {entry['name']}/")
            else:
                size = entry["size"]
                size_str = f" ({size} bytes)" if size is not None else ""
                lines.append(f"  {entry['name']}{size_str}")

        return "\n".join(lines)

    @toolset.tool
    async def read_file(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        path: str,
        offset: int = 0,
        limit: int = 500,
    ) -> str:
        """Read file content with line numbers.

        Args:
            path: Path to the file to read.
            offset: Line number to start reading from (0-indexed).
            limit: Maximum number of lines to read.
        """
        return ctx.deps.backend.read(path, offset, limit)

    @toolset.tool(requires_approval=require_write_approval)
    async def write_file(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        path: str,
        content: str,
    ) -> str:
        """Write content to a file (creates or overwrites).

        This will create parent directories if needed.
        Use edit_file for making small changes to existing files.

        Args:
            path: Path to the file to write.
            content: Content to write to the file.
        """
        result = ctx.deps.backend.write(path, content)

        if result.error:
            return f"Error: {result.error}"

        lines = content.count("\n") + 1
        return f"Wrote {lines} lines to {result.path}"

    @toolset.tool(requires_approval=require_write_approval)
    async def edit_file(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Edit a file by replacing strings.

        The old_string must be unique in the file unless replace_all is True.
        Always read the file first to understand its content before editing.

        Args:
            path: Path to the file to edit.
            old_string: String to find and replace.
            new_string: Replacement string.
            replace_all: If True, replace all occurrences. Otherwise, fails if not unique.
        """
        result = ctx.deps.backend.edit(path, old_string, new_string, replace_all)

        if result.error:
            return f"Error: {result.error}"

        return f"Edited {result.path}: replaced {result.occurrences} occurrence(s)"

    @toolset.tool
    async def glob(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        pattern: str,
        path: str = "/",
    ) -> str:
        """Find files matching a glob pattern.

        Common patterns:
        - "*.py" - Python files in current directory
        - "**/*.py" - Python files recursively
        - "src/**/*.ts" - TypeScript files under src/

        Args:
            pattern: Glob pattern to match (e.g., "**/*.py").
            path: Base directory to search from.
        """
        entries = ctx.deps.backend.glob_info(pattern, path)

        if not entries:
            return f"No files matching '{pattern}' in {path}"

        lines = [f"Found {len(entries)} file(s) matching '{pattern}':"]
        for entry in entries[:100]:  # Limit output
            lines.append(f"  {entry['path']}")

        if len(entries) > 100:
            lines.append(f"  ... and {len(entries) - 100} more")

        return "\n".join(lines)

    @toolset.tool
    async def grep(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        pattern: str,
        path: str | None = None,
        glob_pattern: str | None = None,
        output_mode: Literal["content", "files_with_matches", "count"] = "files_with_matches",
    ) -> str:
        """Search for a regex pattern in files.

        Args:
            pattern: Regex pattern to search for.
            path: Specific file or directory to search.
            glob_pattern: Glob pattern to filter files (e.g., "*.py").
            output_mode: Output format - "content", "files_with_matches", or "count".
        """
        result = ctx.deps.backend.grep_raw(pattern, path, glob_pattern)

        if isinstance(result, str):
            return result  # Error message

        if not result:
            return f"No matches for '{pattern}'"

        matches: list[GrepMatch] = result

        if output_mode == "count":
            return f"Found {len(matches)} match(es) for '{pattern}'"

        if output_mode == "files_with_matches":
            files = sorted(set(m["path"] for m in matches))
            lines = [f"Files containing '{pattern}':"]
            for f in files[:50]:
                lines.append(f"  {f}")
            if len(files) > 50:
                lines.append(f"  ... and {len(files) - 50} more files")
            return "\n".join(lines)

        # content mode
        lines = [f"Matches for '{pattern}':"]
        for m in matches[:50]:
            lines.append(f"  {m['path']}:{m['line_number']}: {m['line'][:100]}")
        if len(matches) > 50:
            lines.append(f"  ... and {len(matches) - 50} more matches")
        return "\n".join(lines)

    # Add execute tool if backend supports it
    if include_execute:

        @toolset.tool(requires_approval=require_execute_approval)
        async def execute(  # pragma: no cover
            ctx: RunContext[DeepAgentDeps],
            command: str,
            timeout: int | None = 120,
        ) -> str:
            """Execute a shell command.

            Use this for running tests, builds, scripts, etc.
            Be careful with destructive commands.

            Args:
                command: The shell command to execute.
                timeout: Maximum execution time in seconds (default 120).
            """
            backend = ctx.deps.backend

            if not isinstance(backend, SandboxProtocol):
                return "Error: Execute not available - backend does not support command execution"

            result = backend.execute(command, timeout)

            output = result.output
            if result.truncated:
                output += "\n\n... (output truncated)"

            if result.exit_code is not None and result.exit_code != 0:
                return f"Command failed (exit code {result.exit_code}):\n{output}"

            return output

    return toolset


def get_filesystem_system_prompt(deps: DeepAgentDeps) -> str:
    """Generate dynamic system prompt for filesystem tools.

    Args:
        deps: The agent dependencies.

    Returns:
        System prompt section for filesystem tools.
    """
    parts = [FILESYSTEM_SYSTEM_PROMPT]

    if isinstance(deps.backend, SandboxProtocol):
        parts.append(SANDBOX_SYSTEM_PROMPT)
        
        # Add image config info if available
        image_info = _get_image_config_prompt(deps.backend)
        if image_info:
            parts.append(image_info)

    # Add files summary if any
    files_summary = deps.get_files_summary()
    if files_summary:
        parts.append(files_summary)

    return "\n".join(parts)


def _get_image_config_prompt(backend: SandboxProtocol) -> str | None:
    """Generate system prompt section for image configuration.

    Args:
        backend: The sandbox backend.

    Returns:
        Image info prompt section, or None if no config available.
    """
    # Check if backend has _image_config attribute
    image_config = getattr(backend, "_image_config", None)
    if image_config is None:
        return None

    lines = [
        "## 执行环境",
        "",
        f"**环境**: {image_config.name}",
    ]

    if image_config.description:
        lines.append(f"**描述**: {image_config.description}")

    lines.append(f"**工作目录**: {image_config.work_dir}")

    if image_config.pre_installed_packages:
        lines.append("")
        lines.append("**已安装的库** (无需 pip install):")
        for pkg in image_config.pre_installed_packages:
            lines.append(f"- {pkg}")

    if image_config.capabilities:
        lines.append("")
        lines.append(f"**能力**: {', '.join(image_config.capabilities)}")

    return "\n".join(lines)


# Alias for convenience
FilesystemToolset = create_filesystem_toolset
