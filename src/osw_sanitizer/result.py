from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SanitizationResult:
    success: bool
    message: str
    updated_dataset_zip: Optional[str] = None
    fixes_json: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
