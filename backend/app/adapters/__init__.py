"""Adapters package: defines BaseAdapter and auto-discovery registry."""
from .base import BaseAdapter
from .registry import AdapterRegistry, get_adapter_registry

__all__ = ["BaseAdapter", "AdapterRegistry", "get_adapter_registry"]
