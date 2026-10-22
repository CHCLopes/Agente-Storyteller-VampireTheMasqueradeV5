"""Tests for the exact six-entry C catalog and its negative controls."""
import json

import pytest

from api.campaign_progression_catalog import CampaignIntentKind
from api.experiments.intent_interpretation_catalog import (
    APPROVED_PARAPHRASES, VERSION, approved_intent,
)
from scripts.evaluate_intent_paraphrase_admission_offline import CASES, evaluate


def test_catalog_is_exact_and_versioned():
    assert VERSION == "intent-paraphrase-catalog.v1"
    assert len(APPROVED_PARAPHRASES) == 6
    assert all(type(key) is str and key == key.strip() for key in APPROVED_PARAPHRASES)
    assert all(isinstance(value, CampaignIntentKind) for value in APPROVED_PARAPHRASES.values())


@pytest.mark.parametrize("player_input,intent", list(APPROVED_PARAPHRASES.items()))
def test_approved_exact_mappings(player_input, intent):
    assert approved_intent(player_input) is intent


@pytest.mark.parametrize("player_input", [
    "Quero saber qual é a tarefa",
    " quero saber qual é a tarefa.",
    "Fico esperando",
    "Não retiro o registro.",
    'Digo a Mara: "Leve o registro".',
    "Fico esperando e depois retiro o registro.",
    "Uso meu casaco para cobrir o registro.",
])
def test_unapproved_near_misses_are_not_inferred(player_input):
    assert approved_intent(player_input) is None


def test_evidence_counts_and_no_model_claim():
    result = evaluate()
    assert result["catalog_version"] == VERSION
    assert result["synthetic_only"] is True
    assert result["provider_calls"] == 0
    assert result["model_accuracy_measured"] is False
    assert result["counts"] == {
        "cases": 12,
        "approved_cases": 6,
        "approved_eligible": 6,
        "control_cases": 6,
        "control_false_accepts": [],
        "approved_baseline_false_blocks": ["C01", "C02", "C03", "C04", "C05", "C06"],
        "approved_baseline_agreements": 0,
    }


def test_result_is_repeatable_and_has_no_execution_surface(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("catalog study must not execute or roll")

    monkeypatch.setattr("api.rules_service.calculate_resolution", forbidden)
    first = evaluate()
    assert evaluate() == first
    assert all("action_eligible" in row for row in first["rows"])
