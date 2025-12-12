"""Adapter registry with auto-discovery of BaseAdapter subclasses."""
import importlib
import pkgutil
from typing import Dict, Type
from .base import BaseAdapter


class AdapterRegistry:
    """Registry maintaining mapping from source_type -> adapter instance."""

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}

    def register(self, adapter_cls: Type[BaseAdapter]) -> None:
        instance = adapter_cls()
        if not instance.source_type or instance.source_type == "unknown":
            raise ValueError(f"Adapter {adapter_cls.__name__} must define a source_type")
        self._adapters[instance.source_type] = instance

    def get(self, source_type: str) -> BaseAdapter:
        if source_type not in self._adapters:
            raise KeyError(f"No adapter registered for source_type '{source_type}'")
        return self._adapters[source_type]

    def all(self) -> Dict[str, BaseAdapter]:
        return dict(self._adapters)

    def discover(self) -> int:
        """
        Discover and register all adapters under app.adapters package.
        Returns count of adapters registered.
        """
        # Iterate modules in this package
        import app.adapters as adapters_pkg
        count = 0
        for finder, name, ispkg in pkgutil.iter_modules(adapters_pkg.__path__, adapters_pkg.__name__ + "."):
            # import module to load classes
            importlib.import_module(name)
        # Register subclasses
        for adapter_cls in BaseAdapter.__subclasses__():
            # Avoid registering base class itself or duplicates
            if adapter_cls is BaseAdapter:
                continue
            # Don't double-register
            instance = adapter_cls()
            if instance.source_type not in self._adapters:
                self._adapters[instance.source_type] = instance
                count += 1
        return count


_registry_singleton: AdapterRegistry | None = None


def get_adapter_registry() -> AdapterRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = AdapterRegistry()
        _registry_singleton.discover()
    return _registry_singleton
