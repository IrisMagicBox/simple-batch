from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class RequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class ErrorType(str, Enum):
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_ERROR = "ConfigurationError"
    PERFORMANCE_CALCULATION_ERROR = "PerformanceCalculationError"
