"""Sandbox configuration utilities for simplified workspace mounting.

This module provides functions to build Docker volume configurations
for mounting the current working directory into the sandbox.
"""

from __future__ import annotations

import os


def build_sandbox_volumes(
    work_dir: str | None = None,
) -> dict[str, dict[str, str]]:
    """Build Docker volume configuration for workspace sandbox.

    Mounts the current working directory (or specified directory) directly
    into the container at /workspace, ensuring the model sees the same
    absolute paths as the host system.

    Args:
        work_dir: Directory to mount (defaults to current working directory)

    Returns:
        Docker volumes dict: {host_path: {'bind': container_path, 'mode': 'rw'}}

    Example:
        ```python
        # Mount current directory to /workspace
        volumes = build_sandbox_volumes()
        sandbox = DockerSandbox(volumes=volumes)

        # Mount specific directory
        volumes = build_sandbox_volumes("/path/to/project")
        sandbox = DockerSandbox(volumes=volumes)
        ```
    """
    if work_dir is None:
        work_dir = os.getcwd()

    volumes = {
        os.path.abspath(work_dir): {
            'bind': '/workspace',
            'mode': 'rw'
        }
    }

    return volumes
