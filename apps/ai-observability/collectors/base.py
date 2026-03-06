"""Base collector interface for observability data collection."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseCollector(ABC):
    """Abstract base class for all collectors."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Collect data and return as a dictionary."""
        pass
