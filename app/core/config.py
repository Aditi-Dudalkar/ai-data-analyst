"""Application configuration settings."""

from pathlib import Path
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Core settings for data storage, profiling, and LLM integration."""

    # --- Dataset storage ---
    UPLOAD_DIR: Path = Field(
        default_factory=lambda: Path(os.getenv("UPLOAD_DIR", "data/uploads")).resolve()
    )
    MAX_FILE_SIZE_BYTES: int = Field(
        default_factory=lambda: int(
            os.getenv("MAX_FILE_SIZE_BYTES", str(50 * 1024 * 1024))
        )  # 50 MB
    )
    SAMPLE_VALUES_COUNT: int = Field(
        default_factory=lambda: int(os.getenv("SAMPLE_VALUES_COUNT", "5"))
    )
    TOP_CATEGORICAL_LIMIT: int = Field(
        default_factory=lambda: int(os.getenv("TOP_CATEGORICAL_LIMIT", "5"))
    )

    # --- LLM configuration ---
    LLM_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "mock")
    )
    LLM_MODEL: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "mock-model")
    )
    LLM_API_KEY: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "")
    )
    LLM_TEMPERATURE: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.0"))
    )
    MAX_PLAN_RETRIES: int = Field(
        default_factory=lambda: int(os.getenv("MAX_PLAN_RETRIES", "2"))
    )


settings = Settings()
