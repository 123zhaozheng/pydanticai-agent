from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db
from src.routes import files

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    init_db()
    yield

app = FastAPI(
    title="Pydantic Deep API",
    description="Backend for Pydantic Deep Agent interactions",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(files.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Pydantic Deep API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
