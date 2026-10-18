"""Opening summaries must not invent a player's history behind valid prose."""

import pytest

from api.orchestrator_service import STORYTELLER_SYSTEM_PROMPT
from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    validate_scene_continuation,
)
from scripts.evaluate_narrator_models import load_storyteller_prompt


def _opening(summary: str) -> SceneContinuationProposal:
    # Synthetic Groq opening from the operational probe on 2026-09-05.
    # Do not depend on ignored eval-results files or repair recorded answers.
    return SceneContinuationProposal.model_validate({
        "n": (
            "O ar é pesado, cheirando a mofo e metal oxidado. Luzes fluorescentes "
            "tremeluzem acima, lançando sombras erráticas nas paredes de concreto "
            "cru. Não há portas visíveis, apenas uma grade enferrujada ao fundo. "
            "O silêncio é ensurdecedor, quebrado apenas pelo gotejar rítmico de "
            "uma torneira quebrada no canto escuro."
        ),
        "o": "unresolved",
        "l": "Subsolo desconhecido",
        "s": summary,
        "p": [], "f": [],
        "t": ["Estabelecer localização exata", "Identificar saída"],
        "r": [],
        "q": "O que você faz neste local sombrio?",
    })


def test_opening_prompt_grounds_summary_without_scripted_scene_or_new_history():
    prompt = load_storyteller_prompt()
    assert prompt == STORYTELLER_SYSTEM_PROMPT
    assert len(prompt.split()) <= 400
    summary_instruction = next(line for line in prompt.splitlines() if line.startswith("- `s`:"))
    assert "resumo da cena" in summary_instruction
    assert "sintetize `n`" in summary_instruction
    assert "sem acrescentar ações, passado ou estado mental" in summary_instruction
    assert "sem inventar chegada, despertar, amnésia ou passado" in prompt


def test_valid_json_can_still_invent_waking_only_in_the_summary():
    proposal = _opening("Personagem desperta em subsolo industrial, sem contexto claro.")
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(), current_scene=None, player_input="Onde estou?",
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "scene_summary"
    assert caught.value.evidence["unauthorized_concepts"] == ["wake"]


def test_environment_only_summary_does_not_need_player_history_or_weaker_guard():
    proposal = _opening(
        "O subsolo tem paredes de concreto, luzes fluorescentes, uma grade "
        "enferrujada e uma torneira gotejando."
    )
    assert validate_scene_continuation(
        proposal, facts=(), current_scene=None, player_input="Onde estou?",
    ) is proposal
