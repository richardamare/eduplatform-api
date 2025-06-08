from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.api import chat, workspace, files, flashcard, exam
from app.database import close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="A streaming chat API with PostgreSQL and vector search",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(flashcard.router, prefix="/api/v1")
app.include_router(exam.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"title": settings.api_title, "version": settings.api_version}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred"}
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
