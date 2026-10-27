"""Domain exceptions for dataset management, profiling, and analysis planning."""


class DatasetError(Exception):
    """Base exception for all dataset-related operations."""

    def __init__(self, message: str, code: str = "DATASET_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class DatasetNotFoundError(DatasetError):
    """Raised when a requested dataset does not exist."""

    def __init__(self, dataset_id: str) -> None:
        super().__init__(
            f"Dataset with ID '{dataset_id}' was not found.",
            code="DATASET_NOT_FOUND",
        )
        self.dataset_id = dataset_id


class DatasetValidationError(DatasetError):
    """Base exception for dataset validation failures."""

    def __init__(self, message: str, code: str = "DATASET_VALIDATION_ERROR") -> None:
        super().__init__(message, code=code)


class InvalidFileFormatError(DatasetValidationError):
    """Raised when an uploaded file is not a supported format (e.g., not CSV)."""

    def __init__(self, filename: str, supported_formats: list[str] | None = None) -> None:
        formats = supported_formats or [".csv"]
        super().__init__(
            f"Unsupported file format for '{filename}'. Supported formats: {', '.join(formats)}.",
            code="INVALID_FILE_FORMAT",
        )
        self.filename = filename


class DatasetSizeLimitExceededError(DatasetValidationError):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, file_size: int, max_size: int) -> None:
        super().__init__(
            f"File size ({file_size} bytes) exceeds the maximum allowed limit of {max_size} bytes.",
            code="FILE_SIZE_LIMIT_EXCEEDED",
        )
        self.file_size = file_size
        self.max_size = max_size


class EmptyDatasetError(DatasetValidationError):
    """Raised when a dataset has no rows or data."""

    def __init__(self, message: str = "The uploaded dataset is empty.") -> None:
        super().__init__(message, code="EMPTY_DATASET")


class MissingHeadersError(DatasetValidationError):
    """Raised when a dataset does not contain valid column headers."""

    def __init__(self, message: str = "The dataset does not have valid column headers.") -> None:
        super().__init__(message, code="MISSING_HEADERS")


class CorruptDatasetError(DatasetValidationError):
    """Raised when a CSV file cannot be parsed due to corrupt formatting or encoding."""

    def __init__(self, message: str = "Failed to parse CSV dataset. The file may be corrupted.") -> None:
        super().__init__(message, code="CORRUPT_DATASET")


class PlanError(Exception):
    """Base exception for analysis planning operations."""

    def __init__(self, message: str, code: str = "PLAN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class UnknownQuestionError(PlanError):
    """Raised when the manual planner receives an unrecognized question."""

    def __init__(self, question: str) -> None:
        super().__init__(
            f"Unable to manually generate an analysis plan for unrecognized question: '{question}'.",
            code="UNKNOWN_QUESTION",
        )
        self.question = question


class PlanGenerationError(PlanError):
    """Raised when the agent fails to generate a valid AnalysisPlan after all retries."""

    def __init__(self, attempts: int, last_error: str = "") -> None:
        msg = f"Failed to generate a valid analysis plan after {attempts} attempt(s)."
        if last_error:
            msg += f" Last error: {last_error}"
        super().__init__(msg, code="PLAN_GENERATION_FAILED")
        self.attempts = attempts
        self.last_error = last_error
