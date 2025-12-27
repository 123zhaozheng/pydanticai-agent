"""Pydantic Deep API - FastAPI Application Entry Point."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure Logfire (MUST be done before any other imports that use logfire)
from src.logging_config import configure_logging, instrument_fastapi
configure_logging()

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
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

# Instrument FastAPI with Logfire
instrument_fastapi(app)

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
        reload_dirs=["src", "pydantic_deep"],
    )
