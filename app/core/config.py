"""Application configuration settings."""

from pathlib import Path
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Core settings for data storage and profiling."""

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


settings = Settings()
