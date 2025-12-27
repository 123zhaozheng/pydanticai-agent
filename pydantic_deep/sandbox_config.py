"""Default Docker image configurations for sandbox.

This module provides pre-defined ImageConfig instances describing
the capabilities of Docker images used by DockerSandbox.
"""

from __future__ import annotations

from pydantic_deep.types import ImageConfig

# Default data analysis sandbox image
DEFAULT_SANDBOX_CONFIG = ImageConfig(
    name="data-analysis",
    image="pydantic-deep-sandbox",
    description="数据分析执行环境,支持 Excel/CSV 处理、统计分析、数据可视化和 Python 脚本执行",
    work_dir="/workspace",
    pre_installed_packages=[
        # 数据处理
        "pandas",
        "numpy",
        # Excel 处理
        "openpyxl",
        "xlrd",
        "xlsxwriter",
        "python-docx",
        # 可视化
        "matplotlib",
        "seaborn",
        "plotly",
        # 统计分析
        "scipy",
        "statsmodels",
        # 网络请求
        "requests",
        "httpx",
        # 工具库
        "tqdm",
        "tabulate",
        "chardet",
        "orjson",
    ],
    capabilities=[
        "excel",
        "csv",
        "data-analysis",
        "visualization",
        "statistics",
        "python",
    ],
)


def get_default_sandbox_config() -> ImageConfig:
    """Get the default sandbox image configuration.
    
    Returns:
        ImageConfig for the default data analysis sandbox.
    """
    return DEFAULT_SANDBOX_CONFIG
