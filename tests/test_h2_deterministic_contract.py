from pathlib import Path


def test_h2_document_is_deterministic_and_does_not_prescribe_legacy_writes() -> None:
    document = Path("skills/H2_vtm_relational.md").read_text(encoding="utf-8")

    assert "descontinuado como skill cognitiva" in document
    assert "api/relationship_service.py" in document
    assert "commit transacional" in document
    assert "não recebem novas escritas" in document
    assert "data/saves/{session_id}_relationships.json" not in document
