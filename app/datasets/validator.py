"""Validation functions for uploaded datasets and CSV files."""

from pathlib import Path
import io
import pandas as pd

from app.core.config import settings
from app.core.exceptions import (
    CorruptDatasetError,
    DatasetSizeLimitExceededError,
    EmptyDatasetError,
    InvalidFileFormatError,
    MissingHeadersError,
)


class DatasetValidator:
    """Validates raw files and loaded datasets against format, size, and structure rules."""

    @staticmethod
    def validate_filename(filename: str) -> None:
        """Validate that the file has a supported extension (.csv)."""
        if not filename or not filename.strip():
            raise InvalidFileFormatError("unknown", supported_formats=[".csv"])

        suffix = Path(filename).suffix.lower()
        if suffix != ".csv":
            raise InvalidFileFormatError(filename, supported_formats=[".csv"])

    @staticmethod
    def validate_file_size(size_bytes: int, max_size_bytes: int | None = None) -> None:
        """Validate that the file size is non-zero and within the maximum threshold."""
        max_limit = max_size_bytes or settings.MAX_FILE_SIZE_BYTES

        if size_bytes <= 0:
            raise EmptyDatasetError("The uploaded file is empty (0 bytes).")

        if size_bytes > max_limit:
            raise DatasetSizeLimitExceededError(size_bytes, max_limit)

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> None:
        """Validate that a loaded DataFrame is non-empty and has valid column headers."""
        if df.empty or len(df) == 0:
            raise EmptyDatasetError("The dataset contains 0 rows.")

        if len(df.columns) == 0:
            raise MissingHeadersError("The dataset contains no columns.")

        # Check for completely empty or nameless headers
        cleaned_cols = [str(c).strip() for c in df.columns]
        if all(not c or c.startswith("Unnamed:") for c in cleaned_cols):
            raise MissingHeadersError("The dataset does not contain valid column headers.")

    @classmethod
    def validate_and_parse_csv(
        cls,
        content: bytes | io.BytesIO | Path | str,
        filename: str = "dataset.csv",
    ) -> pd.DataFrame:
        """Validate file and parse CSV content into a validated DataFrame."""
        cls.validate_filename(filename)

        if isinstance(content, (bytes, bytearray)):
            cls.validate_file_size(len(content))
            source = io.BytesIO(content)
        elif isinstance(content, Path):
            if not content.exists():
                raise CorruptDatasetError(f"File at '{content}' does not exist.")
            cls.validate_file_size(content.stat().st_size)
            source = content
        elif isinstance(content, str):
            path_obj = Path(content)
            if path_obj.exists() and path_obj.is_file():
                cls.validate_file_size(path_obj.stat().st_size)
                source = path_obj
            else:
                encoded = content.encode("utf-8")
                cls.validate_file_size(len(encoded))
                source = io.StringIO(content)
        elif isinstance(content, io.BytesIO):
            buffer_val = content.getvalue()
            cls.validate_file_size(len(buffer_val))
            source = content
        else:
            source = content

        try:
            # Try reading with utf-8 first, fallback to latin-1 if decoding error occurs
            try:
                df = pd.read_csv(source)
            except UnicodeDecodeError:
                if hasattr(source, "seek"):
                    source.seek(0)
                df = pd.read_csv(source, encoding="latin-1")
            except pd.errors.EmptyDataError:
                raise EmptyDatasetError("The CSV file is empty.")
            except (pd.errors.ParserError, ValueError) as err:
                raise CorruptDatasetError(f"Failed to parse CSV file: {err}") from err
        except (EmptyDatasetError, CorruptDatasetError):
            raise
        except Exception as err:
            raise CorruptDatasetError(f"Unexpected error while parsing CSV: {err}") from err

        cls.validate_dataframe(df)
        return df
