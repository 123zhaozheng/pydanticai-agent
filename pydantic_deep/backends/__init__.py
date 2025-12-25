from pydantic_deep.backends.protocol import BackendProtocol, SandboxProtocol
from pydantic_deep.backends.sandbox import BaseSandbox, DockerSandbox
from pydantic_deep.backends.state import StateBackend

# Deprecated backends (still importable but not recommended)
from pydantic_deep.backends.composite import CompositeBackend  # noqa: F401
from pydantic_deep.backends.filesystem import FilesystemBackend  # noqa: F401

__all__ = [
    # Core protocols
    "BackendProtocol",
    "SandboxProtocol",
    # Recommended backends
    "StateBackend",  # In-memory, for development/testing
    "BaseSandbox",  # Abstract base for sandboxes
    "DockerSandbox",  # Recommended: Isolated execution environment
    # Deprecated (kept for backwards compatibility, will be removed in future)
    # "FilesystemBackend",  # Use DockerSandbox with volumes instead
    # "CompositeBackend",   # Use DockerSandbox with multiple volumes instead
]
