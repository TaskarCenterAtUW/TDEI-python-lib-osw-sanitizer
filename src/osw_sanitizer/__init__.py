from .config import (
    DEFAULT_ALLOW_ZERO_LENGTH_LINES,
    DEFAULT_COORDINATE_PRECISION,
    DEFAULT_MAX_GEOMETRY_VERTICES,
    SanitizationConfig,
)
from .result import SanitizationResult
from .sanitizer import DatasetValidationError, OSWSanitization, SanitizationProcessor
from .version import __version__

__all__ = [
    "DEFAULT_ALLOW_ZERO_LENGTH_LINES",
    "DEFAULT_COORDINATE_PRECISION",
    "DEFAULT_MAX_GEOMETRY_VERTICES",
    "DatasetValidationError",
    "OSWSanitization",
    "SanitizationConfig",
    "SanitizationProcessor",
    "SanitizationResult",
    "__version__",
]
