"""
Enterprise RAG Knowledge Assistant — Application Configuration

Loads settings from environment variables / .env file.
All secrets and tunables are centralized here.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # --- LLM Provider Selection ---
    llm_provider: str = Field(default="gemini", description="LLM provider: gemini | anthropic | openai | mock")

    # --- Google Gemini (Free tier on Google AI Studio) ---
    google_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model name")
    gemini_embedding_model: str = Field(default="models/text-embedding-004", description="Gemini embedding model")

    # --- Anthropic Claude ---
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    llm_model: str = Field(default="claude-sonnet-4-20250514", description="Anthropic model name")

    # --- OpenAI ---
    openai_api_key: str = Field(default="", description="OpenAI API key")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model")


    # --- ChromaDB ---
    chroma_persist_directory: str = Field(
        default="./storage/chroma",
        description="Directory for persistent ChromaDB storage",
    )

    # --- Retrieval ---
    top_k: int = Field(default=4, ge=1, le=20, description="Number of chunks to retrieve")
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Characters per chunk")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="Overlap between chunks")

    # --- Upload Limits ---
    max_upload_mb: int = Field(default=10, ge=1, le=100, description="Max upload size in MB")

    # --- Application ---
    backend_host: str = Field(default="0.0.0.0", description="API server host")
    backend_port: int = Field(default=8000, description="API server port")
    log_level: str = Field(default="info", description="Logging level")

    # --- Paths ---
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent,
        description="Root directory of the project",
    )

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024

    @property
    def storage_dir(self) -> Path:
        """Resolved storage directory."""
        path = self.project_root / "storage"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_dir(self) -> Path:
        """Resolved ChromaDB directory."""
        path = Path(self.chroma_persist_directory)
        if not path.is_absolute():
            path = self.project_root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton settings instance
settings = Settings()
