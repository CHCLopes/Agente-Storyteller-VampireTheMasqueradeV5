"""Inactive local B selection; no route, accept, bootstrap, producer or gateway.

The trusted server caller chooses destination, enabled flag, session, store,
expected setup, producer config and exact loopback Host/Origin. Received IDs and
headers only compare against that binding: they do not authenticate a person.
The checksum and Python store identity detect inconsistent copies, not hostile
local code capable of reconstructing a complete binding.

The factory performs no I/O. Database paths are absolute lexical paths, not
physical-file identities; no resolve(), symlink or listener inspection occurs.
Only a fully matched B request reads its bound store's B setup manifest. A
failed B selection never selects legacy, creates/migrates a session or retries.

This helper is not mounted. Ordering before the real accept/lifespan, a genuinely
isolated synthetic store, listener binding and product acceptance still belong
to later integration. All handles/results are internal, not public DTOs or
serializable execution permissions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from .narrative_source_input import SourceProducerConfig
from .narrative_source_setup import SourceSetupManifest, validate_source_setup_manifest
from .persistence import SQLitePersistence


class SourceLocalSelectionError(ValueError):
    def __init__(self):
        super().__init__("source_local_selection_invalid")


def _raw(value: object) -> object:
    if isinstance(value, BaseModel):
        values = dict(value.__dict__)
        values.update(value.__pydantic_extra__ or {})
        return {key: _raw(item) for key, item in values.items()}
    if type(value) is dict:
        return {key: _raw(item) for key, item in value.items()}
    if type(value) is list:
        return [_raw(item) for item in value]
    if type(value) is tuple:
        return tuple(_raw(item) for item in value)
    return value


def _identity(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or value != value.strip():
        raise SourceLocalSelectionError()
    value.encode("utf-8")
    return value


def _authority(value: object) -> str:
    match = re.fullmatch(r"127\.0\.0\.1:([0-9]{1,5})", value) if type(value) is str else None
    if match is None or not 1 <= int(match[1]) <= 65535 or str(int(match[1])) != match[1]:
        raise SourceLocalSelectionError()
    return value


def _origin(value: object) -> str:
    if type(value) is not str or not value.startswith("http://"):
        raise SourceLocalSelectionError()
    _authority(value[7:])
    return value


def _database_path(store: SQLitePersistence) -> str:
    path = store.db_path
    if not isinstance(path, Path) or not path.is_absolute() or ".." in path.parts:
        raise SourceLocalSelectionError()
    return str(path)


class _InternalModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
        arbitrary_types_allowed=True, revalidate_instances="always", hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def preserve_copies(cls, value: object) -> object:
        return _raw(value)


class SourceLocalTrialBinding(_InternalModel):
    protocol: Literal["source-local-trial-binding-v1"] = "source-local-trial-binding-v1"
    session_id: StrictStr = Field(exclude=True, repr=False)
    store: SQLitePersistence = Field(exclude=True, repr=False)
    store_identity: StrictInt = Field(exclude=True, repr=False)
    database_path: StrictStr = Field(exclude=True, repr=False)
    expected_manifest: SourceSetupManifest = Field(exclude=True, repr=False)
    producer_config: SourceProducerConfig = Field(exclude=True, repr=False)
    expected_host: StrictStr = Field(exclude=True, repr=False)
    expected_origin: StrictStr = Field(exclude=True, repr=False)
    fingerprint_sha256: StrictStr = Field(exclude=True, repr=False)

    @model_validator(mode="after")
    def consistent_binding(self) -> "SourceLocalTrialBinding":
        _identity(self.session_id)
        _authority(self.expected_host)
        _origin(self.expected_origin)
        if self.store_identity != id(self.store) or self.database_path != _database_path(self.store):
            raise SourceLocalSelectionError()
        validate_source_setup_manifest(self.expected_manifest, session_id=self.session_id)
        if self.fingerprint_sha256 != _fingerprint(_binding_payload(self)):
            raise SourceLocalSelectionError()
        return self


def _binding_payload(binding: SourceLocalTrialBinding) -> dict:
    return dict(session_id=binding.session_id, store_identity=binding.store_identity,
        database_path=binding.database_path, expected_host=binding.expected_host,
        expected_origin=binding.expected_origin,
        expected_manifest=binding.expected_manifest.model_dump(mode="json"),
        producer_config=binding.producer_config.model_dump(mode="json"))


def _fingerprint(payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_source_local_trial_binding(*, session_id: str, store: SQLitePersistence,
        expected_manifest: SourceSetupManifest, producer_config: SourceProducerConfig,
        expected_host: str, expected_origin: str) -> SourceLocalTrialBinding:
    """Capture an explicit trusted-server binding without reading a database."""
    try:
        if (not isinstance(store, SQLitePersistence) or type(expected_manifest) is not SourceSetupManifest
                or type(producer_config) is not SourceProducerConfig):
            raise ValueError
        manifest = validate_source_setup_manifest(_raw(expected_manifest), session_id=_identity(session_id))
        config = SourceProducerConfig.model_validate(_raw(producer_config))
        values = dict(session_id=session_id, store=store, store_identity=id(store),
            database_path=_database_path(store), expected_manifest=manifest, producer_config=config,
            expected_host=_authority(expected_host), expected_origin=_origin(expected_origin))
        payload = {key: value for key, value in values.items() if key != "store"}
        payload.update(expected_manifest=manifest.model_dump(mode="json"), producer_config=config.model_dump(mode="json"))
        return SourceLocalTrialBinding(**values, fingerprint_sha256=_fingerprint(payload))
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise SourceLocalSelectionError() from None


def _checked(binding: object) -> SourceLocalTrialBinding:
    if type(binding) is not SourceLocalTrialBinding:
        raise SourceLocalSelectionError()
    return SourceLocalTrialBinding.model_validate(_raw(binding))


class SourceLocalSelection(_InternalModel):
    """Internal observation only; excluded handles must never be sent to a client."""
    destination: Literal["legacy", "rejected", "source_local_trial"]
    reason: Literal["disabled", "binding_invalid", "request_mismatch", "setup_unavailable"] | None = None
    binding: SourceLocalTrialBinding | None = Field(default=None, exclude=True, repr=False)
    manifest: SourceSetupManifest | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def consistent_result(self) -> "SourceLocalSelection":
        if self.destination == "source_local_trial":
            if self.reason is not None or self.binding is None or self.manifest is None:
                raise SourceLocalSelectionError()
            if self.manifest != self.binding.expected_manifest:
                raise SourceLocalSelectionError()
        elif self.binding is not None or self.manifest is not None:
            raise SourceLocalSelectionError()
        elif (self.destination == "legacy") != (self.reason is None):
            raise SourceLocalSelectionError()
        return self


def _headers_match(raw_headers: object, binding: SourceLocalTrialBinding) -> bool:
    # Keep duplicate fields observable; a dict would discard that evidence.
    if type(raw_headers) not in (list, tuple):
        return False
    selected = {b"host": [], b"origin": []}
    for pair in raw_headers:
        if type(pair) not in (list, tuple) or len(pair) != 2 or any(type(value) is not bytes for value in pair):
            return False
        name, value = pair
        if name.lower() in selected:
            selected[name.lower()].append(value)
    return (selected[b"host"] == [binding.expected_host.encode("ascii")]
        and selected[b"origin"] == [binding.expected_origin.encode("ascii")])


async def select_source_local_entry(*, destination: str, enabled: bool, binding: object,
        received_session_id: object, raw_headers: object) -> SourceLocalSelection:
    """Select before a future caller accepts; never call that caller's handlers."""
    if type(destination) is not str or destination not in ("legacy", "source_local_trial") or type(enabled) is not bool:
        raise SourceLocalSelectionError()
    if destination == "legacy":
        return SourceLocalSelection(destination="legacy")
    if not enabled:
        return SourceLocalSelection(destination="rejected", reason="disabled")
    try:
        checked = _checked(binding)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        return SourceLocalSelection(destination="rejected", reason="binding_invalid")
    if type(received_session_id) is not str or received_session_id != checked.session_id or not _headers_match(raw_headers, checked):
        return SourceLocalSelection(destination="rejected", reason="request_mismatch")
    try:
        # The only I/O path. No initialize, campaign creation, migration or reserve.
        observed = await checked.store.read_source_setup_manifest(checked.session_id)
        manifest = validate_source_setup_manifest(observed, session_id=checked.session_id)
        after = _checked(checked)
        if manifest != after.expected_manifest:
            raise ValueError
        return SourceLocalSelection(destination="source_local_trial", binding=after, manifest=manifest)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError, OSError, sqlite3.Error):
        return SourceLocalSelection(destination="rejected", reason="setup_unavailable")
