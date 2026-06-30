"""
EDF-L1 Phase 6 — Adapter Registry Verification Suite.

Verifies the public behaviour of :class:`AdapterRegistry` and
:func:`default_registry`:

    - registration
    - duplicate registration
    - removal
    - lookup
    - unknown board handling
    - factory creation (lazy instantiation)
    - enabled-boards resolution
    - disabled boards
    - missing config (Phase 5 backward compatibility)
    - lazy imports (no circular dependency)
    - iteration / membership / size protocol

Rules:
    - No production code is modified by this suite.
    - The registry is tested in isolation; no downloader/storage/manifest
      components are required.
"""

from __future__ import annotations

import inspect

import pytest

from src.edf.adapters.base import BaseAdapter
from src.edf.adapters.registry import AdapterRegistry, default_registry


# ---------------------------------------------------------------------------
# Test adapter doubles
# ---------------------------------------------------------------------------


class _StubAdapter(BaseAdapter):
    """Minimal concrete adapter for registry tests (isolated from real boards)."""

    def __init__(self, config=None, http_client=None):
        super().__init__(config or {}, http_client)
        self.received_config = config
        self.received_http = http_client

    @property
    def board_name(self) -> str:
        return "STUB"

    def pre_flight(self):
        return []

    def get_descriptors(self):
        return []

    def resolve_url(self, descriptor):
        return descriptor.url


class _OtherStub(BaseAdapter):
    @property
    def board_name(self) -> str:
        return "OTHER"

    def pre_flight(self):
        return []

    def get_descriptors(self):
        return []

    def resolve_url(self, descriptor):
        return descriptor.url


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_registry():
    return AdapterRegistry()


@pytest.fixture
def populated_registry():
    r = AdapterRegistry()
    r.register("GSEB", _StubAdapter)
    r.register("NCERT", _OtherStub)
    return r


# ---------------------------------------------------------------------------
# 1. Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_adds_board(self, empty_registry):
        empty_registry.register("GSEB", _StubAdapter)
        assert empty_registry.is_registered("GSEB")
        assert "GSEB" in empty_registry

    def test_list_adapters_returns_registered(self, populated_registry):
        assert populated_registry.list_adapters() == ["GSEB", "NCERT"]

    def test_list_adapters_is_sorted(self, empty_registry):
        empty_registry.register("Zeta", _StubAdapter)
        empty_registry.register("Alpha", _OtherStub)
        assert empty_registry.list_adapters() == ["Alpha", "Zeta"]

    def test_register_stores_class_not_instance(self, empty_registry):
        empty_registry.register("GSEB", _StubAdapter)
        cls = empty_registry.get("GSEB")
        assert cls is _StubAdapter
        # No instance created yet.
        assert isinstance(cls, type)

    def test_register_rejects_non_ba_subclass(self, empty_registry):
        class NotAnAdapter:
            pass

        with pytest.raises(TypeError):
            empty_registry.register("X", NotAnAdapter)  # type: ignore[arg-type]

    def test_register_rejects_empty_board_name(self, empty_registry):
        with pytest.raises(ValueError):
            empty_registry.register("", _StubAdapter)

    def test_register_rejects_non_string_board_name(self, empty_registry):
        with pytest.raises(ValueError):
            empty_registry.register(123, _StubAdapter)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Duplicate registration
# ---------------------------------------------------------------------------


class TestDuplicateRegistration:
    def test_duplicate_raises_valueerror(self, populated_registry):
        with pytest.raises(ValueError):
            populated_registry.register("GSEB", _OtherStub)

    def test_duplicate_message_names_board(self, empty_registry):
        empty_registry.register("GSEB", _StubAdapter)
        with pytest.raises(ValueError, match="GSEB"):
            empty_registry.register("GSEB", _OtherStub)

    def test_different_boards_allowed(self, empty_registry):
        empty_registry.register("GSEB", _StubAdapter)
        empty_registry.register("NCERT", _OtherStub)
        assert len(empty_registry) == 2


# ---------------------------------------------------------------------------
# 3. Removal / unregister
# ---------------------------------------------------------------------------


class TestUnregister:
    def test_unregister_removes_board(self, populated_registry):
        assert populated_registry.unregister("GSEB") is True
        assert not populated_registry.is_registered("GSEB")
        assert "GSEB" not in populated_registry

    def test_unregister_unknown_returns_false(self, empty_registry):
        assert empty_registry.unregister("NOPE") is False

    def test_unregister_then_reregister_allowed(self, populated_registry):
        populated_registry.unregister("GSEB")
        # Should not raise after removal.
        populated_registry.register("GSEB", _OtherStub)
        assert populated_registry.get("GSEB") is _OtherStub


# ---------------------------------------------------------------------------
# 4. Lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_get_returns_registered_class(self, populated_registry):
        assert populated_registry.get("GSEB") is _StubAdapter

    def test_get_unknown_raises_keyerror(self, empty_registry):
        with pytest.raises(KeyError):
            empty_registry.get("GSEB")

    def test_get_unknown_message_names_board(self, populated_registry):
        with pytest.raises(KeyError, match="UNKNOWN"):
            populated_registry.get("UNKNOWN")

    def test_is_registered_false_for_unknown(self, empty_registry):
        assert empty_registry.is_registered("GSEB") is False

    def test_is_registered_true_after_register(self, empty_registry):
        empty_registry.register("GSEB", _StubAdapter)
        assert empty_registry.is_registered("GSEB") is True


# ---------------------------------------------------------------------------
# 5. Factory creation (lazy instantiation)
# ---------------------------------------------------------------------------


class TestFactoryCreation:
    def test_create_returns_instance(self, populated_registry):
        adapter = populated_registry.create("GSEB", config={"gseb": {}})
        assert isinstance(adapter, _StubAdapter)
        assert isinstance(adapter, BaseAdapter)

    def test_create_passes_config(self, populated_registry):
        cfg = {"gseb": {"textbooks": []}, "marker": 1}
        adapter = populated_registry.create("GSEB", config=cfg)
        assert adapter.received_config is cfg

    def test_create_passes_http_client(self, populated_registry):
        http = object()
        adapter = populated_registry.create("GSEB", config={}, http_client=http)
        assert adapter.received_http is http

    def test_create_unknown_raises_keyerror(self, empty_registry):
        with pytest.raises(KeyError):
            empty_registry.create("NOPE", config={})

    def test_create_does_not_change_constructor_signature(self, populated_registry):
        # Adapter constructor must still accept (config, http_client).
        sig = inspect.signature(_StubAdapter.__init__)
        params = list(sig.parameters)
        assert "config" in params
        assert "http_client" in params

    def test_create_invokes_adapter_ctor_contract(self, populated_registry):
        # create() must call adapter_cls(config=config, http_client=http_client)
        adapter = populated_registry.create("NCERT", config={"ncert": {}})
        assert adapter.board_name == "OTHER"


# ---------------------------------------------------------------------------
# 6. enabled_boards — positive / default cases
# ---------------------------------------------------------------------------


class TestEnabledBoards:
    def test_no_boards_section_all_registered_enabled(self):
        cfg = {"gseb": {}, "ncert": {}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert result == ["GSEB", "NCERT"]

    def test_explicit_enabled_true(self):
        cfg = {"boards": {"gseb": {"enabled": True}, "ncert": {"enabled": True}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert result == ["GSEB", "NCERT"]

    def test_case_insensitive_board_keys(self):
        # boards keys are lowercase; registered names are uppercase.
        cfg = {"boards": {"gseb": {"enabled": True}, "ncert": {"enabled": True}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert "GSEB" in result and "NCERT" in result

    def test_entry_without_enabled_defaults_true(self):
        cfg = {"boards": {"gseb": {}}}  # present but no enabled key
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB"])
        assert result == ["GSEB"]

    def test_scalar_shorthand_true(self):
        cfg = {"boards": {"gseb": True}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB"])
        assert result == ["GSEB"]


# ---------------------------------------------------------------------------
# 7. Disabled boards
# ---------------------------------------------------------------------------


class TestDisabledBoards:
    def test_disabled_board_excluded(self):
        cfg = {"boards": {"gseb": {"enabled": False}, "ncert": {"enabled": True}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert result == ["NCERT"]

    def test_all_disabled_returns_empty(self):
        cfg = {"boards": {"gseb": {"enabled": False}, "ncert": {"enabled": False}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert result == []

    def test_scalar_shorthand_false(self):
        cfg = {"boards": {"gseb": False}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB"])
        assert result == []

    def test_board_absent_from_section_defaults_enabled(self):
        # ncert not listed under boards → defaults enabled.
        cfg = {"boards": {"gseb": {"enabled": True}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB", "NCERT"])
        assert result == ["GSEB", "NCERT"]


# ---------------------------------------------------------------------------
# 8. Missing config (backward compatibility)
# ---------------------------------------------------------------------------


class TestMissingConfig:
    def test_none_config_all_registered_enabled(self):
        result = AdapterRegistry.enabled_boards(None, registered=["GSEB"])
        assert result == ["GSEB"]

    def test_empty_config_all_registered_enabled(self):
        result = AdapterRegistry.enabled_boards({}, registered=["GSEB", "NCERT"])
        assert result == ["GSEB", "NCERT"]

    def test_no_registered_list_no_boards_section_returns_empty(self):
        result = AdapterRegistry.enabled_boards({}, registered=None)
        assert result == []

    def test_no_registered_list_with_boards_section_derives_uppercase(self):
        cfg = {"boards": {"gseb": {"enabled": True}, "ncert": {"enabled": False}}}
        result = AdapterRegistry.enabled_boards(cfg, registered=None)
        assert result == ["GSEB"]

    def test_phase5_flat_config_still_works(self):
        # Classic Phase 5 config: flat gseb/download, no boards section.
        cfg = {
            "gseb": {"textbooks": []},
            "download": {"timeout_seconds": 10},
            "validation": {"min_size_bytes": 1024},
        }
        result = AdapterRegistry.enabled_boards(cfg, registered=["GSEB"])
        assert result == ["GSEB"]


# ---------------------------------------------------------------------------
# 9. Iteration / membership / size
# ---------------------------------------------------------------------------


class TestDunderProtocol:
    def test_iter_yields_sorted_boards(self, populated_registry):
        assert list(iter(populated_registry)) == ["GSEB", "NCERT"]

    def test_len_matches_count(self, populated_registry):
        assert len(populated_registry) == 2

    def test_contains_registered(self, populated_registry):
        assert "GSEB" in populated_registry
        assert "NCERT" in populated_registry
        assert "CBSE" not in populated_registry

    def test_repr_is_string_and_lists_boards(self, populated_registry):
        r = repr(populated_registry)
        assert isinstance(r, str)
        assert "GSEB" in r and "NCERT" in r


# ---------------------------------------------------------------------------
# 10. default_registry() + lazy imports
# ---------------------------------------------------------------------------


class TestDefaultRegistry:
    def test_has_gseb_and_ncert(self):
        r = default_registry()
        assert "GSEB" in r
        assert "NCERT" in r

    def test_returns_adapter_registry_instance(self):
        assert isinstance(default_registry(), AdapterRegistry)

    def test_default_registry_creates_real_adapters(self):
        r = default_registry()
        gseb = r.create("GSEB", config={"gseb": {"textbooks": []}})
        ncert = r.create("NCERT", config={"ncert": {"textbooks": []}})
        assert gseb.board_name == "GSEB"
        assert ncert.board_name == "NCERT"

    def test_default_registry_is_fresh_each_call(self):
        r1 = default_registry()
        r1.unregister("GSEB")
        r2 = default_registry()
        # A new registry is returned each call — GSEB re-registered.
        assert "GSEB" in r2

    def test_registry_module_does_not_import_downloader(self):
        import src.edf.adapters.registry as reg_mod

        src = inspect.getsource(reg_mod)
        # The registry must not import pipeline/downloader/storage/manifest.
        assert "core.downloader" not in src
        assert "core.pipeline" not in src
        assert "storage.manager" not in src
        assert "manifests.manager" not in src

    def test_no_circular_import_on_module_import(self):
        # Re-importing must not raise (guards against circular deps).
        import importlib

        mod = importlib.import_module("src.edf.adapters.registry")
        assert hasattr(mod, "AdapterRegistry")
        assert hasattr(mod, "default_registry")
