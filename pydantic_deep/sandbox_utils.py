"""Utility functions for Docker sandbox operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_deep.backends.sandbox import DockerSandbox


def discover_container_files(sandbox: DockerSandbox) -> list[str]:
    """Discover all available files in the container workspace.

    Scans the following directories in the container:
    - /workspace/uploads/ - User uploaded files
    - /workspace/intermediate/ - Code execution outputs and temp files
    - /workspace/skills/ - Skill resource files (excluding SKILL.md)

    Args:
        sandbox: DockerSandbox instance to scan.

    Returns:
        List of file paths in the container (absolute paths starting with /workspace/).

    Example:
        ```python
        sandbox = DockerSandbox(user_id=1, conversation_id=123)
        files = discover_container_files(sandbox)
        # Returns: ['/workspace/uploads/data.csv', '/workspace/intermediate/output.txt', ...]
        ```
    """
    paths = []

    # 1. Scan uploads directory
    result = sandbox.execute("find /workspace/uploads -type f 2>/dev/null || true")
    if result.exit_code == 0 and result.output.strip():
        for line in result.output.strip().split("\n"):
            if line:
                paths.append(line)

    # 2. Scan intermediate directory
    result = sandbox.execute("find /workspace/intermediate -type f 2>/dev/null || true")
    if result.exit_code == 0 and result.output.strip():
        for line in result.output.strip().split("\n"):
            if line:
                paths.append(line)

    # 3. Scan skills directory (exclude SKILL.md to avoid clutter)
    result = sandbox.execute(
        "find /workspace/skills -type f ! -name 'SKILL.md' 2>/dev/null || true"
    )
    if result.exit_code == 0 and result.output.strip():
        for line in result.output.strip().split("\n"):
            if line:
                paths.append(line)

    return [p for p in paths if p]  # Filter empty strings


def list_container_directories(sandbox: DockerSandbox) -> dict[str, list[str]]:
    """List files grouped by directory.

    Returns a dictionary with directory names as keys and file lists as values.

    Args:
        sandbox: DockerSandbox instance to scan.

    Returns:
        Dict with keys: 'uploads', 'intermediate', 'skills'.

    Example:
        ```python
        dirs = list_container_directories(sandbox)
        # {'uploads': ['data.csv', 'report.pdf'], 'intermediate': ['output.txt'], ...}
        ```
    """
    result = {}

    # Uploads
    uploads = sandbox.execute("ls -1 /workspace/uploads 2>/dev/null || true")
    result["uploads"] = (
        [f for f in uploads.output.strip().split("\n") if f] if uploads.exit_code == 0 else []
    )

    # Intermediate
    intermediate = sandbox.execute("ls -1 /workspace/intermediate 2>/dev/null || true")
    result["intermediate"] = (
        [f for f in intermediate.output.strip().split("\n") if f]
        if intermediate.exit_code == 0
        else []
    )

    # Skills (list skill folders, not individual files)
    skills = sandbox.execute("ls -1 /workspace/skills 2>/dev/null || true")
    result["skills"] = (
        [f for f in skills.output.strip().split("\n") if f] if skills.exit_code == 0 else []
    )

    return result


def get_file_info(sandbox: DockerSandbox, file_path: str) -> dict[str, str | int] | None:
    """Get detailed information about a file in the container.

    Args:
        sandbox: DockerSandbox instance.
        file_path: Absolute path to file in container.

    Returns:
        Dict with keys: 'path', 'size', 'permissions', 'modified' or None if file doesn't exist.

    Example:
        ```python
        info = get_file_info(sandbox, '/workspace/uploads/data.csv')
        # {'path': '...', 'size': 1024, 'permissions': '-rw-r--r--', 'modified': '2024-01-15'}
        ```
    """
    result = sandbox.execute(f"stat -c '%s|%A|%y' {file_path} 2>/dev/null || true")

    if result.exit_code != 0 or not result.output.strip():
        return None

    parts = result.output.strip().split("|")
    if len(parts) < 3:
        return None

    return {
        "path": file_path,
        "size": int(parts[0]),
        "permissions": parts[1],
        "modified": parts[2].split(".")[0],  # Remove microseconds
    }
