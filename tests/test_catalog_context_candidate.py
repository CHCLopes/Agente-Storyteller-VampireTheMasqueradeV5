from pydantic import ValidationError
import pytest

from api.catalog_models import (
    CatalogContextCandidate,
    CatalogDomain,
    CatalogRelevanceSignals,
)
from api.turn_models import RecordReference, Visibility


def test_catalog_candidate_is_strict_frozen_and_source_attributed() -> None:
    candidate = CatalogContextCandidate(
        domain=CatalogDomain.NPC_ARCHETYPE,
        entry_id="prince",
        minimal_text="Príncipe: ameaça 5; sobrenatural.",
        visibility=Visibility.PLAYER,
        required=True,
        signals=CatalogRelevanceSignals(
            explicitly_mentioned=True,
            active_in_scene=True,
        ),
        importance=0.9,
        source_refs=(
            RecordReference(
                record_id="catalog:npc_archetype/prince",
                record_type="catalog_entry",
                relation="derived_from",
            ),
        ),
    )

    assert candidate.domain is CatalogDomain.NPC_ARCHETYPE
    assert candidate.signals.explicitly_mentioned is True
    assert candidate.source_refs[0].record_id == "catalog:npc_archetype/prince"
    with pytest.raises(ValidationError, match="frozen"):
        candidate.importance = 0.1


@pytest.mark.parametrize(
    "update",
    (
        {"entry_id": "Prince"},
        {"minimal_text": " texto com espaço "},
        {"importance": 1.1},
        {"unexpected": True},
    ),
)
def test_catalog_candidate_rejects_ambiguous_or_unbounded_values(update) -> None:
    payload = {
        "domain": "clan",
        "entry_id": "brujah",
        "minimal_text": "Brujah: compulsão mecânica quando ativa.",
        **update,
    }
    with pytest.raises(ValidationError):
        CatalogContextCandidate(**payload)
