from dataclasses import dataclass
from src.core.enums.status import ResultStatus

@dataclass
class StartResult:
    status: ResultStatus
    text: str