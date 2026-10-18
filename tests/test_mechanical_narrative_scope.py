"""Mechanical achievement is not a keyword anywhere in a narrator response."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal, SceneProposalError, validate_scene_continuation,
)
from api.scene_service import SceneState
from api.turn_execution_service import validate_narrative_contract
from api.turn_execution_service import NarrativeContractError


def proposal(narrative, *, success=False, clue=None, summary=None):
    return SceneContinuationProposal.model_validate({
        "n": narrative, "o": "success" if success else "failure",
        "l": "Galpão abandonado",
        "s": summary or ("A investigação traz uma pista nova." if success else "O cadeado não cede."),
        "f": [{"k": "clue", "s": clue, "p": True}] if clue else [
            {"k": "complication", "s": "Passos se aproximam da grade.", "p": True}
        ],
        "q": "O que você faz agora?",
    })


FAILURE_START = "O cadeado não cede e o arquivo segue inacessível. "
WORLD_END = (
    " O rádio chia na bancada enquanto passos ecoam entre as vigas; "
    "o ar úmido atravessa a grade e aumenta a pressão no galpão."
)
CLUE = "Um rastro úmido de sangue segue até a escada do mezanino."
DISCOVERY = (
    "Um rastro úmido de sangue escorre até a escada do mezanino. "
    "O rádio chia sobre a bancada, enquanto a luz azulada oscila sobre as "
    "vigas e o vento frio atravessa as janelas quebradas."
)


def admit(item, *, player_input="Investigo o cadeado.", scene=None):
    facts = ({"fact_type": "mechanics.resolution", "value": {"is_success": item.outcome == "success"}},)
    current = scene or SceneState(location="Galpão abandonado")
    accepted = validate_scene_continuation(
        item, facts=facts, current_scene=current, player_input=player_input,
    )
    # Production's second validator must agree with structured admission.
    assert validate_narrative_contract(
        item.player_text, facts=facts, scene_proposal=item,
        player_input=player_input, current_scene=current,
    ) == item.player_text
    return accepted


@pytest.mark.parametrize("reaction", [
    "Uma lanterna corta a escuridão, revelando silhuetas que avançam com passos pesados.",
    "A luz revela sombras junto da grade.",
    "Os faróis revelam vultos junto da entrada.",
])
def test_failed_lock_goal_allows_unrelated_environmental_visibility(reaction):
    assert admit(proposal(FAILURE_START + reaction + WORLD_END)).outcome == "failure"


@pytest.mark.parametrize("reaction", [
    "A lanterna revela a combinação do cadeado.",
    "A luz revela a identidade da figura escondida.",
    "A luz revela a prova atrás da grade.",
    "A luz revela silhuetas e a combinação do cadeado.",
    "A luz revela silhuetas. A prova foi encontrada.",
    "A luz revela silhuetas com o registro definitivo nas mãos.",
    "A luz revela silhuetas e a grade abre.",
    "A luz revela a silhueta do assassino.",
    "A luz revela a figura de Mara.",
])
def test_environmental_subject_cannot_launder_mechanical_achievement(reaction):
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        admit(proposal(FAILURE_START + reaction + WORLD_END))


@pytest.mark.parametrize("player_input,threads", [
    ("Procuro as silhuetas.", ()),
    ("Investigo quem está escondido.", ()),
    ("Investigo o cadeado.", ("Identificar quem está escondido",)),
])
def test_visibility_is_not_unrelated_when_it_is_the_target(player_input, threads):
    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        admit(
            proposal(FAILURE_START + "A luz revela silhuetas junto da grade." + WORLD_END),
            player_input=player_input,
            scene=SceneState(location="Galpão abandonado", open_threads=threads),
        )


def test_successful_area_investigation_can_deliver_a_grounded_new_clue():
    assert admit(proposal(DISCOVERY, success=True, clue=CLUE), player_input="Investigo o galpão abandonado.")


@pytest.mark.parametrize("narrative,clue,details,player_input", [
    ("Não há um rastro úmido de sangue até a escada do mezanino." + WORLD_END, CLUE, (), "Investigo o galpão abandonado."),
    ("Talvez exista um rastro úmido de sangue até a escada do mezanino." + WORLD_END, CLUE, (), "Investigo o galpão abandonado."),
    ("O rádio chia sobre a bancada e a luz falha junto da grade." + WORLD_END, CLUE, (), "Investigo o galpão abandonado."),
    (DISCOVERY, CLUE, (CLUE,), "Investigo o galpão abandonado."),
    (DISCOVERY, CLUE, (), "Investigo o cadeado."),
    (DISCOVERY, CLUE, (), "Investigo o cadeado do galpão abandonado."),
    (DISCOVERY, CLUE, (), "Investigo o cadeado abandonado."),
    (DISCOVERY, CLUE, (), "Ataco o guarda."),
])
def test_clue_label_alone_does_not_prove_mechanical_success(narrative, clue, details, player_input):
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        admit(
            proposal(narrative, success=True, clue=clue), player_input=player_input,
            scene=SceneState(location="Galpão abandonado", details=details),
        )


def test_success_claim_only_in_question_or_summary_is_insufficient():
    item = proposal("A luz oscila sobre o chão escuro do galpão." + WORLD_END, success=True)
    item = item.model_copy(update={"player_prompt": "O que você faz depois do sucesso?", "scene_summary": "A investigação teve sucesso."})
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        admit(item, player_input="Investigo o galpão abandonado.")


def test_unchanged_outcome_does_not_allow_failure_in_the_actual_investigation():
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        admit(proposal("A investigação falha, mas o rádio revela um chiado." + WORLD_END,
                       success=True, clue=CLUE), player_input="Investigo o galpão abandonado.")


@pytest.mark.parametrize("clue,narrative", [
    ("Uma mancha larga úmida recente escura de sangue atravessa o piso.",
     "Uma mancha larga úmida recente escura de água atravessa o piso."),
    ("O crachá velho azul pertence ao vigia João no galpão.",
     "O crachá velho azul pertence ao vigia Pedro no galpão."),
    ("Uma pista nova importante interessante relevante surge no galpão.",
     "Uma pista nova importante interessante relevante surge no galpão."),
    ("3 marcas recentes de sangue atravessam o piso do galpão.",
     "2 marcas recentes de sangue atravessam o piso do galpão."),
    ("Um rastro úmido de sangue segue da escada até o mezanino.",
     "Um rastro úmido de sangue segue do mezanino até a escada."),
])
def test_overlap_cannot_substitute_material_identity_or_concrete_information(clue, narrative):
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        admit(proposal(narrative + WORLD_END, success=True, clue=clue),
              player_input="Investigo o galpão abandonado.")


def test_legacy_prose_contract_cannot_use_question_as_outcome_evidence():
    text = "O rádio chia na bancada e a luz oscila sobre as vigas." + WORLD_END + " O que você faz depois do sucesso?"
    with pytest.raises(NarrativeContractError, match="narrative_outcome_mismatch"):
        validate_narrative_contract(text, facts=({"fact_type": "mechanics.resolution", "value": {"is_success": True}},))


def test_structured_contract_cannot_validate_different_prose():
    item = proposal(DISCOVERY, success=True, clue=CLUE)
    with pytest.raises(NarrativeContractError, match="narrative_proposal_mismatch"):
        validate_narrative_contract(
            "A investigação teve sucesso e a porta cedeu." + WORLD_END,
            facts=({"fact_type": "mechanics.resolution", "value": {"is_success": True}},),
            scene_proposal=item,
        )


@pytest.mark.parametrize("narrative,clue", [
    ("A luz revela sombras junto da grade." + WORLD_END, None),
    ("O rádio chia sobre a bancada." + WORLD_END + " Quem encontrou a prova?", None),
    ("O rádio chia sobre a bancada." + WORLD_END + " Um rastro úmido de sangue segue até a escada do mezanino?", CLUE),
    ('Uma voz repete: "A investigação teve sucesso."' + WORLD_END, None),
    ('Uma voz repete: «A investigação teve sucesso.»' + WORLD_END, None),
])
def test_world_effect_question_or_dialogue_is_not_investigation_success(narrative, clue):
    with pytest.raises(SceneProposalError, match="scene_success_not_honored"):
        admit(proposal(narrative, success=True, clue=clue), player_input="Investigo o cadeado.")
