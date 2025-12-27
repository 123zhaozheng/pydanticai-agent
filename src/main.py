import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging (reduce noise from httpx since Logfire handles it)
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger("pydantic_ai").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce httpx noise, Logfire will capture details

# Configure Logfire for PydanticAI observability (官方推荐)
import logfire

logfire.configure(
    send_to_logfire=False,  # 本地控制台输出，不发送到云端
    console=logfire.ConsoleOptions(
        colors='auto',
        span_style='indented',   # 缩进显示,更清晰
        verbose=True,            # 详细输出
        include_timestamps=True, # 包含时间戳
    )
)

# 1️⃣ 监控 PydanticAI Agent 调用 (Agent run, 模型调用, 工具执行)
logfire.instrument_pydantic_ai()

# 2️⃣ 监控 HTTP 请求 (发送给 LLM 的完整请求和响应)
logfire.instrument_httpx(capture_all=True)

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db

# Import API routers
from src.api.models import router as models_router
from src.api.conversations import router as conversations_router
from src.api.mcp_tools import router as mcp_tools_router
from src.api.todos import router as todos_router
from src.api.uploads import router as uploads_router
from src.api.skills import router as skills_router
from pydantic_deep.toolsets.mcp import reload_mcp_toolset

# ========== 全局 MCP Toolset 单例 ==========
# Moved to pydantic_deep.toolsets.mcp

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    init_db()
    # Initialize global MCP toolset
    reload_mcp_toolset()
    yield

app = FastAPI(
    title="Pydantic Deep API",
    description="Backend for Pydantic Deep Agent interactions",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(models_router)
app.include_router(conversations_router)
app.include_router(mcp_tools_router)
app.include_router(todos_router)
app.include_router(uploads_router)
app.include_router(skills_router)


@app.get("/")
async def root():
    return {"message": "Welcome to Pydantic Deep API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src", "pydantic_deep"],  # Only watch these directories
    )
