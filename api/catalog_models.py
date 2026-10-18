"""Strict metadata contracts for the deterministic V5 catalog registry."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator

from .turn_models import RecordReference, Visibility


class StrictCatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CatalogDomain(str, Enum):
    BLOOD_POTENCY = "blood_potency"
    CLAN = "clan"
    DISCIPLINE_POWER = "discipline_power"
    NPC_ARCHETYPE = "npc_archetype"
    PREDATOR_TYPE = "predator_type"
    PROGRESSION_CATEGORY = "progression_category"
    WEAPON = "weapon"


class SupportLevel(str, Enum):
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    PARTIAL = "partial"
    SUPPORTED = "supported"
    NOT_APPLICABLE = "not_applicable"


class CatalogReference(StrictCatalogModel):
    domain: CatalogDomain
    entry_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    relation: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")


class CatalogEntryIdentity(StrictCatalogModel):
    domain: CatalogDomain
    entry_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    aliases: tuple[StrictStr, ...] = ()
    references: tuple[CatalogReference, ...] = ()

    @field_validator("aliases")
    @classmethod
    def aliases_are_normalized_and_unique(cls, aliases: tuple[str, ...]) -> tuple[str, ...]:
        if any(alias != alias.strip().casefold() or not alias for alias in aliases):
            raise ValueError("catalog aliases must be normalized non-empty strings")
        if len(set(aliases)) != len(aliases):
            raise ValueError("catalog aliases must be unique")
        return aliases


class DisciplineRequirement(StrictCatalogModel):
    discipline_family_id: StrictStr = Field(
        min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$"
    )
    level: int = Field(ge=1, le=5)


class DisciplinePowerMetadata(StrictCatalogModel):
    schema_version: Literal["1.0"]
    power_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    aliases: tuple[StrictStr, ...] = ()
    discipline_family_id: StrictStr = Field(
        min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$"
    )
    level: int | None = Field(default=None, ge=1, le=5)
    prerequisite_power_ids: tuple[StrictStr, ...] = ()
    amalgam_requirements: tuple[DisciplineRequirement, ...] = ()
    rules_origin: Literal["v5", "v5_with_legacy_adaptation", "partially_identified"]


class CatalogSupport(StrictCatalogModel):
    catalogued: StrictBool
    references_valid: SupportLevel
    mechanics: SupportLevel
    narrative: SupportLevel
    positive_tests: SupportLevel
    negative_tests: SupportLevel
    limitations: tuple[StrictStr, ...] = ()


class CatalogSupportEntry(StrictCatalogModel):
    identity: CatalogEntryIdentity
    mvp_scope: Literal["base_reachable", "candidate", "deferred"]
    support: CatalogSupport


class CatalogSupportMatrix(StrictCatalogModel):
    schema_version: Literal["1.0"]
    content_version: StrictStr = Field(min_length=1)
    entries: tuple[CatalogSupportEntry, ...]

    @field_validator("entries")
    @classmethod
    def entries_are_unique(cls, entries: tuple[CatalogSupportEntry, ...]) -> tuple[CatalogSupportEntry, ...]:
        keys = [(entry.identity.domain, entry.identity.entry_id) for entry in entries]
        if len(keys) != len(set(keys)):
            raise ValueError("support matrix entries must be unique")
        return entries


class CatalogFileProvenance(StrictCatalogModel):
    domain: CatalogDomain
    path: StrictStr = Field(min_length=1)
    sha256: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    content_version: StrictStr = Field(min_length=1)
    reviewed_at: date
    source_title: StrictStr | None = None
    source_locator: StrictStr | None = None
    edition: StrictStr | None = None
    page_or_section: StrictStr | None = None
    license_basis: StrictStr | None = None
    editorial_notes: StrictStr = Field(min_length=1)
    verification_status: Literal["verified", "unverified"]


class CatalogSourceInventoryItem(StrictCatalogModel):
    source_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    filename: StrictStr = Field(min_length=1)
    sha256: StrictStr = Field(pattern=r"^[0-9a-f]{64}$")
    pages: int = Field(ge=1)
    source_role: Literal[
        "project_summary",
        "engine_design",
        "v5_rules",
        "legacy_rules",
        "scenario",
    ]
    edition: StrictStr | None = None
    authority_scope: tuple[CatalogDomain, ...] = ()
    usage_notes: StrictStr = Field(min_length=1)
    license_basis: StrictStr = Field(min_length=1)


class CatalogManifest(StrictCatalogModel):
    schema_version: Literal["1.0"]
    files: tuple[CatalogFileProvenance, ...]
    source_inventory: tuple[CatalogSourceInventoryItem, ...] = ()

    @field_validator("files")
    @classmethod
    def domains_and_paths_are_unique(
        cls, files: tuple[CatalogFileProvenance, ...]
    ) -> tuple[CatalogFileProvenance, ...]:
        domains = [item.domain for item in files]
        paths = [item.path for item in files]
        if len(domains) != len(set(domains)) or len(paths) != len(set(paths)):
            raise ValueError("manifest domains and paths must be unique")
        return files

    @field_validator("source_inventory")
    @classmethod
    def source_ids_and_hashes_are_unique(
        cls, sources: tuple[CatalogSourceInventoryItem, ...]
    ) -> tuple[CatalogSourceInventoryItem, ...]:
        ids = [item.source_id for item in sources]
        hashes = [item.sha256 for item in sources]
        if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
            raise ValueError("source inventory IDs and hashes must be unique")
        return sources


class CatalogRecord(StrictCatalogModel):
    identity: CatalogEntryIdentity
    support: CatalogSupport
    mvp_scope: Literal["base_reachable", "candidate", "deferred"]
    payload: dict[str, Any]


class CatalogRelevanceSignals(StrictCatalogModel):
    explicitly_mentioned: StrictBool = False
    explicitly_selected: StrictBool = False
    rule_triggered: StrictBool = False
    active_in_scene: StrictBool = False
    text_relevant: StrictBool = False


class CatalogContextCandidate(StrictCatalogModel):
    domain: CatalogDomain
    entry_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    minimal_text: StrictStr = Field(min_length=1)
    visibility: Visibility = Visibility.PLAYER
    required: StrictBool = False
    signals: CatalogRelevanceSignals = Field(default_factory=CatalogRelevanceSignals)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source_refs: tuple[RecordReference, ...] = ()

    @field_validator("minimal_text")
    @classmethod
    def text_is_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("minimal_text must be trimmed")
        return value


class CatalogContextOmission(StrictCatalogModel):
    item_id: StrictStr = Field(min_length=1)
    reason: Literal["budget", "irrelevant_default_weapon"]
    estimated_tokens: int = Field(ge=1)
    priority_position: int = Field(ge=1)


class CatalogContextSelection(StrictCatalogModel):
    policy_version: Literal["catalog-context-selection.v1"]
    selected: tuple[CatalogContextCandidate, ...] = ()
    omissions: tuple[CatalogContextOmission, ...] = ()
    estimated_tokens: int = Field(default=0, ge=0)


class CatalogLoreFact(StrictCatalogModel):
    domain: CatalogDomain
    entry_id: StrictStr = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    field_path: tuple[StrictStr, ...]
    value: StrictStr = Field(min_length=1)
    source_refs: tuple[RecordReference, ...]


class CatalogLoreLookupResult(StrictCatalogModel):
    status: Literal["covered", "not_covered"]
    normalized_query: StrictStr = Field(min_length=1)
    facts: tuple[CatalogLoreFact, ...] = ()
    source_refs: tuple[RecordReference, ...] = ()
    coverage: tuple[SupportLevel, ...] = ()
    limitations: tuple[StrictStr, ...] = ()
