"""Single validated, local-only registry for the seven V5 catalogs."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from pydantic import ValidationError

from .catalog_models import (
    CatalogDomain,
    CatalogEntryIdentity,
    CatalogLoreFact,
    CatalogLoreLookupResult,
    CatalogManifest,
    CatalogRecord,
    CatalogSupportEntry,
    CatalogSupportMatrix,
    DisciplinePowerMetadata,
)
from .turn_models import RecordReference


CATALOG_FILES: dict[CatalogDomain, str] = {
    CatalogDomain.BLOOD_POTENCY: "blood_potency.json",
    CatalogDomain.CLAN: "clans.json",
    CatalogDomain.DISCIPLINE_POWER: "disciplines.json",
    CatalogDomain.NPC_ARCHETYPE: "npc_hierarchy.json",
    CatalogDomain.PREDATOR_TYPE: "predator_types.json",
    CatalogDomain.PROGRESSION_CATEGORY: "progression_costs.json",
    CatalogDomain.WEAPON: "weapons.json",
}

EXPLICIT_ALIASES: dict[tuple[CatalogDomain, str], tuple[str, ...]] = {
    (CatalogDomain.NPC_ARCHETYPE, "prince"): ("principe",),
    (CatalogDomain.NPC_ARCHETYPE, "sheriff"): ("xerife",),
    (CatalogDomain.DISCIPLINE_POWER, "soaring_leap"): ("salto_ascendente",),
    (CatalogDomain.DISCIPLINE_POWER, "fleshcrafting"): ("moldar_carne",),
    (CatalogDomain.DISCIPLINE_POWER, "shadow_cast"): ("lancar_sombra",),
}


class CatalogRegistryError(RuntimeError):
    pass


def normalize_catalog_id(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")


class CatalogRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[1] / "data" / "catalogs"
        try:
            self.support_matrix = CatalogSupportMatrix.model_validate_json(
                (self.root / "v5_support_matrix.json").read_text(encoding="utf-8")
            )
            self.manifest = CatalogManifest.model_validate_json(
                (self.root / "catalog_manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, ValueError) as exc:
            raise CatalogRegistryError("catalog metadata is invalid") from exc

        support = {
            (entry.identity.domain, entry.identity.entry_id): entry
            for entry in self.support_matrix.entries
        }
        provenance = {item.domain: item for item in self.manifest.files}
        self._records: dict[tuple[CatalogDomain, str], CatalogRecord] = {}
        self._aliases: dict[tuple[CatalogDomain, str], str] = {}

        for domain, filename in CATALOG_FILES.items():
            path = self.root / filename
            item = provenance.get(domain)
            if item is None or item.path != f"data/catalogs/{filename}":
                raise CatalogRegistryError(f"missing provenance for {domain.value}")
            if sha256(path.read_bytes()).hexdigest() != item.sha256:
                raise CatalogRegistryError(f"catalog hash mismatch for {domain.value}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise CatalogRegistryError(f"catalog root must be an object: {filename}")
            for raw_id, payload in raw.items():
                entry_id = normalize_catalog_id(raw_id)
                if entry_id != raw_id or not isinstance(payload, dict):
                    raise CatalogRegistryError(f"invalid catalog entry: {domain.value}/{raw_id}")
                supported = support.get((domain, entry_id))
                if supported is None:
                    raise CatalogRegistryError(f"missing support row: {domain.value}/{entry_id}")
                aliases = EXPLICIT_ALIASES.get((domain, entry_id), ())
                if domain is CatalogDomain.DISCIPLINE_POWER:
                    metadata = DisciplinePowerMetadata.model_validate(
                        payload.get("catalog_metadata")
                    )
                    if metadata.power_id != entry_id:
                        raise CatalogRegistryError(
                            f"discipline power identity mismatch: {entry_id}"
                        )
                    aliases = tuple(dict.fromkeys((*aliases, *metadata.aliases)))
                identity = CatalogEntryIdentity(
                    domain=domain,
                    entry_id=entry_id,
                    aliases=aliases,
                    references=supported.identity.references,
                )
                key = (domain, entry_id)
                self._records[key] = CatalogRecord(
                    identity=identity,
                    support=supported.support,
                    mvp_scope=supported.mvp_scope,
                    payload=deepcopy(payload),
                )
                for alias in (entry_id, *aliases):
                    alias_key = (domain, normalize_catalog_id(alias))
                    previous = self._aliases.get(alias_key)
                    if previous is not None and previous != entry_id:
                        raise CatalogRegistryError(f"ambiguous alias: {domain.value}/{alias}")
                    self._aliases[alias_key] = entry_id

        if len(self._records) != len(self.support_matrix.entries):
            raise CatalogRegistryError("support matrix contains unknown entries")
        self._validate_references()

    def _validate_references(self) -> None:
        for record in self._records.values():
            for reference in record.identity.references:
                if (reference.domain, reference.entry_id) not in self._records:
                    raise CatalogRegistryError(
                        f"unknown reference: {reference.domain.value}/{reference.entry_id}"
                    )

    def get(self, domain: CatalogDomain, entry_id_or_alias: str) -> CatalogRecord | None:
        normalized = normalize_catalog_id(entry_id_or_alias)
        entry_id = self._aliases.get((domain, normalized))
        if entry_id is None:
            return None
        return self._records[(domain, entry_id)].model_copy(deep=True)

    def require(self, domain: CatalogDomain, entry_id_or_alias: str) -> CatalogRecord:
        record = self.get(domain, entry_id_or_alias)
        if record is None:
            raise CatalogRegistryError(
                f"unknown catalog entry: {domain.value}/{normalize_catalog_id(entry_id_or_alias)}"
            )
        return record

    def entries(self, domain: CatalogDomain) -> tuple[CatalogRecord, ...]:
        return tuple(
            self._records[key].model_copy(deep=True)
            for key in sorted(self._records, key=lambda item: item[1])
            if key[0] is domain
        )

    def discipline_family_ids(self) -> frozenset[str]:
        """Return known family IDs without creating a second editorial catalog."""
        families: set[str] = set()
        for record in self.entries(CatalogDomain.DISCIPLINE_POWER):
            metadata = DisciplinePowerMetadata.model_validate(
                record.payload["catalog_metadata"]
            )
            families.add(metadata.discipline_family_id)
            families.update(
                requirement.discipline_family_id
                for requirement in metadata.amalgam_requirements
            )
        for record in self.entries(CatalogDomain.CLAN):
            families.update(record.payload["engine_data"]["favored_disciplines"])
        return frozenset(families)


_REGISTRY: CatalogRegistry | None = None


def get_catalog_registry() -> CatalogRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = CatalogRegistry()
    return _REGISTRY


_LORE_FIELD_ROOTS: dict[CatalogDomain, tuple[tuple[str, ...], ...]] = {
    CatalogDomain.BLOOD_POTENCY: (("engine_data",),),
    CatalogDomain.CLAN: (("narrative_data",),),
    CatalogDomain.DISCIPLINE_POWER: (
        ("narrative_data",),
        ("catalog_metadata", "discipline_family_id"),
        ("catalog_metadata", "level"),
        ("catalog_metadata", "rules_origin"),
    ),
    CatalogDomain.NPC_ARCHETYPE: (("narrative_data",),),
    CatalogDomain.PREDATOR_TYPE: (("narrative_data",),),
    CatalogDomain.PROGRESSION_CATEGORY: (
        ("description",),
        ("cost_multiplier",),
        ("base_cost",),
    ),
    CatalogDomain.WEAPON: (("narrative_data",),),
}


def _query_mentions(query_id: str, record: CatalogRecord) -> bool:
    padded_query = f"_{query_id}_"
    for label in (record.identity.entry_id, *record.identity.aliases):
        normalized = normalize_catalog_id(label)
        if normalized and f"_{normalized}_" in padded_query:
            return True
    return False


def _value_at(payload: dict, path: tuple[str, ...]):
    value = payload
    for part in path:
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _flatten_lore_values(value, path: tuple[str, ...]):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _flatten_lore_values(value[key], (*path, str(key)))
    elif isinstance(value, (str, int, float, bool)) and str(value).strip():
        yield path, str(value)


def lookup_catalog_lore(
    query: str,
    *,
    registry: CatalogRegistry | None = None,
) -> CatalogLoreLookupResult:
    """Return typed catalog facts explicitly named by a lore question."""

    normalized_query = normalize_catalog_id(query) or "empty_query"
    catalog = registry or get_catalog_registry()
    matched = tuple(
        record
        for domain in CatalogDomain
        for record in catalog.entries(domain)
        if _query_mentions(normalized_query, record)
    )
    facts: list[CatalogLoreFact] = []
    sources: list[RecordReference] = []
    coverage = []
    limitations: list[str] = []
    for record in matched:
        source = RecordReference(
            record_id=f"catalog:{record.identity.domain.value}/{record.identity.entry_id}",
            record_type="catalog_entry",
            relation="derived_from",
        )
        sources.append(source)
        coverage.append(record.support.narrative)
        limitations.extend(record.support.limitations)
        for root in _LORE_FIELD_ROOTS[record.identity.domain]:
            value = _value_at(record.payload, root)
            for field_path, rendered in _flatten_lore_values(value, root):
                facts.append(
                    CatalogLoreFact(
                        domain=record.identity.domain,
                        entry_id=record.identity.entry_id,
                        field_path=field_path,
                        value=rendered,
                        source_refs=(source,),
                    )
                )

    if not facts:
        return CatalogLoreLookupResult(
            status="not_covered",
            normalized_query=normalized_query,
            limitations=("Nenhuma entrada de catálogo reconhecida cobre a consulta.",),
        )
    return CatalogLoreLookupResult(
        status="covered",
        normalized_query=normalized_query,
        facts=tuple(facts),
        source_refs=tuple(dict.fromkeys(sources)),
        coverage=tuple(coverage),
        limitations=tuple(dict.fromkeys(limitations)),
    )
