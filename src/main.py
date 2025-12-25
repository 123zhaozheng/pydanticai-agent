import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logging.getLogger("pydantic_ai").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)  # 查看完整 API 请求/响应

# Configure Logfire for PydanticAI observability (官方推荐)
import logfire
logfire.configure(send_to_logfire=False)  # 本地控制台输出，不发送到云端
logfire.instrument_pydantic_ai()  # 监控所有 PydanticAI Agent 调用

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db

# Import API routers
from src.api.models import router as models_router
from src.api.conversations import router as conversations_router
from src.api.mcp_tools import router as mcp_tools_router
from src.api.todos import router as todos_router
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
