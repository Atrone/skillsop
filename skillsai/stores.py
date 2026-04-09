"""In-memory stores that mirror the architecture container data stores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlatformStores:
    """In-memory backing stores for the Option 17 architecture."""

    cache: dict[str, Any] = field(default_factory=dict)
    graph: dict[str, Any] = field(default_factory=dict)
    audit: list[dict[str, Any]] = field(default_factory=list)
    time_series: list[dict[str, Any]] = field(default_factory=list)
    mart: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    warehouse: list[dict[str, Any]] = field(default_factory=list)
    item_bank: dict[str, Any] = field(default_factory=dict)
    attempts: dict[str, Any] = field(default_factory=dict)

    # Block comment:
    # This helper keeps write semantics consistent across dictionary stores.
    def put(self, store_name: str, key: str, value: Any) -> None:
        """Write one key/value into a named dictionary-backed store."""
        # Line comment: resolve the dictionary-backed store object by name.
        store = getattr(self, store_name)
        if not isinstance(store, dict):
            raise TypeError(f"Store '{store_name}' is not dictionary-backed.")
        # Line comment: apply an overwrite write for the requested key.
        store[key] = value

    # Block comment:
    # This helper centralizes lookup behavior for dictionary stores.
    def get(self, store_name: str, key: str, default: Any | None = None) -> Any:
        """Read one key from a named dictionary-backed store."""
        # Line comment: resolve the dictionary-backed store object by name.
        store = getattr(self, store_name)
        if not isinstance(store, dict):
            raise TypeError(f"Store '{store_name}' is not dictionary-backed.")
        # Line comment: return the fallback when the key is absent.
        return store.get(key, default)

    # Block comment:
    # This helper centralizes append behavior for list-backed stores.
    def append(self, store_name: str, value: dict[str, Any]) -> None:
        """Append one record to a named list-backed store."""
        # Line comment: resolve the list-backed store object by name.
        store = getattr(self, store_name)
        if not isinstance(store, list):
            raise TypeError(f"Store '{store_name}' is not list-backed.")
        # Line comment: append an event-like record in order.
        store.append(value)

    # Block comment:
    # This helper exposes simple read access to list-backed stores.
    def list_records(self, store_name: str) -> list[dict[str, Any]]:
        """Return a shallow copy of records from a list-backed store."""
        # Line comment: resolve the list-backed store object by name.
        store = getattr(self, store_name)
        if not isinstance(store, list):
            raise TypeError(f"Store '{store_name}' is not list-backed.")
        # Line comment: copy so callers cannot mutate underlying storage directly.
        return list(store)
