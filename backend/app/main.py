"""
Enterprise RAG Knowledge Assistant — FastAPI Application

Entry point for the backend API server.
Run with: uvicorn backend.app.main:app --reload
"""

import os

# Disable Chroma telemetry before import
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.schemas.requests import HealthResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logger.info("Enterprise RAG Knowledge Assistant starting up...")
    logger.info("ChromaDB directory: %s", settings.chroma_dir)
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Enterprise RAG Knowledge Assistant",
    description="A document-based AI assistant that answers questions grounded in retrieved content.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check that the API is running."""
    return HealthResponse(status="ok", version="0.1.0")


# Include all business routes
from backend.app.api.routes import router as api_router
app.include_router(api_router, tags=["RAG Assistant"])

# ---------------------------------------------------------------------------
# Stitch AI Modern Frontend Mount
# ---------------------------------------------------------------------------
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

frontend_static_dir = settings.project_root / "frontend" / "static"
if frontend_static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_static_dir)), name="static")

    @app.get("/", response_class=FileResponse, tags=["Frontend"])
    async def serve_frontend():
        """Serve the Stitch AI-designed modern web UI."""
        return FileResponse(frontend_static_dir / "index.html")

