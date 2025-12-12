"""Base adapter interface for data source normalization."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    """
    Base adapter all data source adapters must inherit.
    
    Each adapter defines a unique `source_type` and implements `parse(data)`
    which converts raw source payloads into the standardized Party schema
    (and optionally related transactions/relationships payloads for ingestion).
    """
    source_type: str = "unknown"

    @abstractmethod
    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw source payload into standardized dict structure.
        
        Returns a dict with keys like 'party', 'transactions', 'relationships'.
        Minimal requirement: must include a 'party' key.
        """
        raise NotImplementedError
