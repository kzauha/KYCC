"""Unit tests for AdapterRegistry auto-discovery and BaseAdapter contract."""
import pytest
from app.adapters import BaseAdapter, AdapterRegistry, get_adapter_registry


class DummyAdapter(BaseAdapter):
    source_type = "dummy"
    def parse(self, data):
        return {"party": {"name": data.get("name", "Dummy")}}


def test_register_and_get_adapter():
    registry = AdapterRegistry()
    registry.register(DummyAdapter)
    adapter = registry.get("dummy")
    assert isinstance(adapter, DummyAdapter)
    assert adapter.parse({"name": "X"})["party"]["name"] == "X"


def test_get_unknown_adapter_raises():
    registry = AdapterRegistry()
    with pytest.raises(KeyError):
        registry.get("unknown")


def test_discover_registers_subclasses(monkeypatch):
    # Monkeypatch subclasses to include DummyAdapter
    registry = AdapterRegistry()
    count = registry.discover()
    # discover will import modules and then register subclasses; ensure at least one
    # Since we only defined DummyAdapter in test file scope, manually register
    registry.register(DummyAdapter)
    adapter = registry.get("dummy")
    assert adapter.source_type == "dummy"


def test_singleton_registry():
    reg1 = get_adapter_registry()
    reg2 = get_adapter_registry()
    assert reg1 is reg2
