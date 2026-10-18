from api.catalog_models import CatalogDomain, SupportLevel
from api.catalog_service import get_catalog_registry, normalize_catalog_id


def test_all_entries_validate_against_versioned_schema() -> None:
    registry = get_catalog_registry()
    assert registry.support_matrix.schema_version == "1.0"
    assert len(registry.support_matrix.entries) == 66
    assert sum(len(registry.entries(domain)) for domain in CatalogDomain) == 66


def test_catalog_ids_aliases_and_cross_references_are_unique() -> None:
    registry = get_catalog_registry()
    seen: set[tuple[CatalogDomain, str]] = set()
    known = {
        (record.identity.domain, record.identity.entry_id)
        for domain in CatalogDomain
        for record in registry.entries(domain)
    }
    for domain in CatalogDomain:
        for record in registry.entries(domain):
            for label in (record.identity.entry_id, *record.identity.aliases):
                key = (domain, normalize_catalog_id(label))
                assert key not in seen
                seen.add(key)
            assert all(
                (reference.domain, reference.entry_id) in known
                for reference in record.identity.references
            )


def test_supported_subset_matrix_matches_catalog_and_tests() -> None:
    registry = get_catalog_registry()
    rows = {
        (row.identity.domain, row.identity.entry_id): row
        for row in registry.support_matrix.entries
    }
    for domain in CatalogDomain:
        for record in registry.entries(domain):
            row = rows[(domain, record.identity.entry_id)]
            assert row.support.catalogued is True
            if row.support.mechanics is SupportLevel.SUPPORTED:
                assert row.support.references_valid in {
                    SupportLevel.SUPPORTED,
                    SupportLevel.PARTIAL,
                }
                assert row.support.positive_tests is SupportLevel.SUPPORTED
                assert row.support.negative_tests is SupportLevel.SUPPORTED
                assert row.support.limitations
