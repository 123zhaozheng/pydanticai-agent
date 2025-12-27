"""Type definitions for pydantic-deep."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict, TypeVar

from pydantic import BaseModel
from pydantic_ai.output import OutputSpec
from typing_extensions import NotRequired

# Re-export OutputSpec from pydantic-ai for structured output support
# This allows users to specify the response format for agents
ResponseFormat = OutputSpec[object]

# Type variable for output types
OutputT = TypeVar("OutputT")


class FileData(TypedDict):
    """Data structure for storing file content."""

    content: list[str]  # Lines of the file
    created_at: str  # ISO 8601 timestamp
    modified_at: str  # ISO 8601 timestamp


class FileInfo(TypedDict):
    """Information about a file or directory."""

    name: str
    path: str
    is_dir: bool
    size: int | None


@dataclass
class WriteResult:
    """Result of a write operation."""

    path: str | None = None
    error: str | None = None


@dataclass
class EditResult:
    """Result of an edit operation."""

    path: str | None = None
    error: str | None = None
    occurrences: int | None = None


@dataclass
class ExecuteResponse:
    """Response from command execution."""

    output: str
    exit_code: int | None = None
    truncated: bool = False


class GrepMatch(TypedDict):
    """A single grep match result."""

    path: str
    line_number: int
    line: str


class Todo(BaseModel):
    """A todo item for task tracking."""

    content: str
    status: Literal["pending", "in_progress", "completed"]
    active_form: str  # Present continuous form (e.g., "Implementing feature X")


class SubAgentConfig(TypedDict):
    """Configuration for a subagent."""

    name: str
    description: str
    instructions: str
    tools: NotRequired[list[object]]
    model: NotRequired[str]


class CompiledSubAgent(TypedDict):
    """A pre-compiled subagent ready for use."""

    name: str
    description: str
    agent: NotRequired[object]  # Agent instance - typed as object to avoid circular imports


class SkillFrontmatter(TypedDict):
    """YAML frontmatter from a SKILL.md file."""

    name: str
    description: str
    tags: NotRequired[list[str]]
    version: NotRequired[str]
    author: NotRequired[str]


class Skill(TypedDict):
    """A loaded skill with its metadata and content."""

    name: str
    description: str
    path: str  # Path to the skill directory
    tags: list[str]
    version: str
    author: str
    frontmatter_loaded: bool  # Whether only frontmatter is loaded
    instructions: NotRequired[str]  # Full instructions (loaded on demand)
    resources: NotRequired[list[str]]  # List of additional files in the skill directory


class SkillDirectory(TypedDict):
    """Configuration for a skill directory."""

    path: str  # Path to the skills directory
    recursive: NotRequired[bool]  # Whether to search recursively


class UploadedFile(TypedDict):
    """Metadata for an uploaded file.

    Uploaded files are stored in the backend and can be accessed by the agent
    through file tools (read_file, grep, glob, execute).
    """

    name: str  # Original filename
    path: str  # Path in backend (e.g., /uploads/sales.csv)
    size: int  # Size in bytes
    line_count: int | None  # Number of lines (for text files)


class ImageConfig(BaseModel):
    """Docker 镜像配置 (描述已有镜像的能力,不动态构建).

    用于向模型描述执行环境的能力,让模型知道可以使用哪些工具和库。

    Example:
        ```python
        from pydantic_deep import ImageConfig, DockerSandbox

        # 定义数据分析镜像配置
        config = ImageConfig(
            name="data-analysis",
            image="pydantic-deep-sandbox",
            description="数据分析环境,支持 Excel 处理、统计分析和可视化",
            pre_installed_packages=["pandas", "openpyxl", "matplotlib"],
            capabilities=["excel", "data-analysis", "visualization"],
        )

        sandbox = DockerSandbox(image_config=config)
        ```
    """

    name: str
    """配置名称 (如 "data-analysis", "web-dev")."""

    image: str
    """Docker 镜像名 (如 "pydantic-deep-sandbox")."""

    description: str = ""
    """镜像能力描述,会注入到模型的系统提示中."""

    work_dir: str = "/workspace"
    """容器内的工作目录."""

    pre_installed_packages: list[str] = []
    """预装的包列表,告知模型无需 pip install."""

    capabilities: list[str] = []
    """能力标签 (如 ["excel", "charts", "pandas"]),可用于过滤和展示."""


# 保留 RuntimeConfig 别名以兼容测试
RuntimeConfig = ImageConfig
