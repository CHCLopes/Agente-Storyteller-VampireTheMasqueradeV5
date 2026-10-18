from api.catalog_models import CatalogDomain
from api.catalog_service import lookup_catalog_lore


def test_lookup_returns_typed_facts_sources_coverage_and_limitations() -> None:
    result = lookup_catalog_lore("O que devo saber sobre os Brujah?")

    assert result.status == "covered"
    assert result.facts
    assert {fact.domain for fact in result.facts} == {CatalogDomain.CLAN}
    assert {fact.entry_id for fact in result.facts} == {"brujah"}
    assert result.source_refs[0].record_id == "catalog:clan/brujah"
    assert result.coverage
    assert all(fact.source_refs == result.source_refs for fact in result.facts)


def test_lookup_resolves_localized_alias_and_limits_facts_to_named_record() -> None:
    result = lookup_catalog_lore("Qual é a função do Príncipe?")

    assert result.status == "covered"
    assert {fact.entry_id for fact in result.facts} == {"prince"}
    assert all(fact.field_path[0] == "narrative_data" for fact in result.facts)
    assert result.source_refs[0].record_id == "catalog:npc_archetype/prince"


def test_unknown_lore_query_is_explicitly_not_covered() -> None:
    result = lookup_catalog_lore("Quem governa a cidade perdida de Atlântida?")

    assert result.status == "not_covered"
    assert result.facts == ()
    assert result.source_refs == ()
    assert result.coverage == ()
    assert result.limitations == (
        "Nenhuma entrada de catálogo reconhecida cobre a consulta.",
    )
