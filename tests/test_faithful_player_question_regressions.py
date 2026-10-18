"""An open continuation question does not authorize narrated player actions."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _validate_player_prompt,
    _action_authorizations,
    _validate_implicit_player_contact,
    validate_mechanical_narrative,
    validate_scene_continuation,
)
from api.scene_service import SceneState


OBSERVED_QUESTION = "Como deseja prosseguir diante do cadeado travado e da presença misteriosa?"
NARRATIVE = (
    "A névoa se adensa entre os contêineres enquanto a corrente bate contra "
    "o concreto. Um brilho metálico aparece na água escura e desaparece "
    "quando uma onda passa, deixando apenas o reflexo irregular das luzes "
    "distantes sobre o cais."
)


def _proposal(question=OBSERVED_QUESTION, **updates):
    payload = {
        "n": NARRATIVE, "o": "unresolved", "l": "Cais municipal",
        "s": "Um brilho aparece na água do cais.", "p": [],
        "f": [{"k": "observation", "s": "Um brilho aparece na água."}],
        "t": [], "r": [], "q": question,
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _admit(proposal):
    return validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Cais municipal"),
        player_input="Observo o cais.",
    )


def test_observed_question_closes_an_otherwise_valid_proposal():
    assert _admit(_proposal("O que você faz agora?")).outcome == "unresolved"
    assert _admit(_proposal()).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    OBSERVED_QUESTION,
    "Como deseja prosseguir?",
    "Como você deseja prosseguir?",
    "Como deseja prosseguir diante de Mara?",
    "Como deseja prosseguir em relação a Mara?",
    "Como você deseja prosseguir diante da hesitação de Mara?",
])
@pytest.mark.parametrize("registered", [False, True])
def test_direct_continuation_invites_player_action(question, registered):
    _validate_player_prompt(question, npc_aliases=("Mara",) if registered else ())


@pytest.mark.parametrize("subject", ["seu personagem", "sua personagem", "Neófito", "Ana Luz"])
def test_continuation_uses_existing_player_subject_aliases(subject):
    _validate_player_prompt(
        f"Como {subject} deseja prosseguir diante de Mara?",
        player_aliases=("Neófito", "Ana Luz"), npc_aliases=("Mara",),
    )


@pytest.mark.parametrize("question", [
    "Como Mara deseja prosseguir?",
    "Como a informante deseja prosseguir?",
    "Como deseja prosseguir Mara?",
    "Como deseja prosseguir a informante?",
    "Como deseja prosseguir, Mara?",
    "Como deseja prosseguir, Mara, diante do cadeado?",
    "Como deseja prosseguir diante do cadeado, Mara?",
    "Como Mara deseja prosseguir enquanto você espera?",
    "Como a sombra do seu personagem deseja prosseguir?",
    "Como o personagem de Mara deseja prosseguir?",
    "Como deseja prosseguir com a história?",
    "Como deseja prosseguir com a narrativa?",
    "Como deseja prosseguir para avançar a história?",
    "Como deseja que a história prossiga?",
    "Como deve prosseguir a narrativa?",
    "Você deseja prosseguir diante do cadeado?",
    "Como deseja prosseguir diante do cadeado",
    "Como deseja prosseguir diante do cadeado: qual é a origem do vulto?",
])
@pytest.mark.parametrize("registered", [False, True])
def test_continuation_does_not_delegate_npc_story_or_closed_choices(question, registered):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(
            question, npc_aliases=("Mara", "informante") if registered else (),
        )


def test_continuation_keeps_the_existing_question_length_limit():
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(
            "Como deseja prosseguir diante do cadeado travado e da presença misteriosa "
            "que observa o galpão abandonado silenciosamente?"
        )
    assert caught.value.code == "scene_player_prompt_too_long"


def test_continuation_does_not_waive_secret_separation():
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(s="O Xerife armou uma emboscada no cais."),
            facts=(), current_scene=SceneState(location="Cais municipal"),
            player_input="Observo o cais.",
            protected_secrets=("O Xerife armou uma emboscada no cais.",),
        )
    assert caught.value.code == "scene_secret_disclosed"


def test_continuation_cannot_presuppose_an_undeclared_opening():
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal("Como deseja prosseguir diante do cadeado após abrir a porta?"))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "presupposed_player_action"


def test_observed_failed_injection_remains_rejected_for_narrated_player_agency():
    proposal = _proposal(
        n=(
            "Ao examinar o cadeado, o personagem percebe que o mecanismo está "
            "corroído e travado; a tentativa de abrir falha, deixando o metal "
            "rangendo sem ceder. Um leve eco reverbera no galpão, enquanto a "
            "sombra de um vulto distante se move silenciosamente, aumentando "
            "a tensão e lembrando que o tempo para descobrir o arquivo está se esgotando."
        ),
        o="failure", l="Galpão abandonado",
        s=("O cadeado está corroído e não abre, falhando ao ser investigado, "
           "e a tensão aumenta com um vulto ao fundo."),
        f=[
            {"k": "observation", "s": "O cadeado está corroído e não abre ao ser investigado.",
             "v": "public", "i": 0.9, "p": True},
            {"k": "complication", "s": "Um vulto silencioso se move nas sombras, sugerindo que alguém ou algo observa.",
             "v": "public", "i": 0.7, "p": True},
        ],
        t=["Descobrir o conteúdo do arquivo"],
    )
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=({"fact_type": "mechanics.resolution", "value": {"is_success": False}},),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_player_agency_violation"



def test_future_discovery_deadline_is_not_a_granted_failure_goal():
    validate_mechanical_narrative(
        "A investigação falha; o tempo para descobrir o arquivo está se esgotando.",
        outcome="failure", player_input="Investigo o cadeado.",
    )


def test_player_bound_nominal_opening_attempt_requires_opening_authority():
    proposal = _proposal(n=(
        "Ao examinar o cadeado, o personagem percebe que o mecanismo está "
        "corroído e travado; a tentativa de abrir falha, deixando o metal rangendo sem ceder."
    ))
    with pytest.raises(SceneProposalError) as caught:
        _validate_implicit_player_contact(
            proposal, authorized_actions=_action_authorizations("Investigo o cadeado."),
            player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("grant", [
    "Você descobre o arquivo.",
    "Você encontra uma prova conclusiva.",
    "O cadeado abre.",
    "Você recebe o arquivo.",
    "Uma luz revela o arquivo.",
])
def test_discovery_deadline_does_not_waive_an_independent_grant(grant):
    with pytest.raises(SceneProposalError) as caught:
        validate_mechanical_narrative(
            "A investigação falha; o tempo para descobrir o arquivo está se esgotando. " + grant,
            outcome="failure", player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_failure_granted_goal"


def test_discovery_deadline_alone_cannot_satisfy_a_successful_action():
    with pytest.raises(SceneProposalError) as caught:
        validate_mechanical_narrative(
            "O tempo para descobrir o arquivo está se esgotando.", outcome="success",
        )
    assert caught.value.code == "scene_success_not_honored"


def test_real_discovery_still_satisfies_the_existing_success_marker():
    validate_mechanical_narrative("Você descobre o arquivo.", outcome="success")


def test_time_pressure_without_physical_attempt_can_be_admitted_after_failure():
    proposal = _proposal(
        n=("A investigação do cadeado falha e o mecanismo permanece travado. "
           "Um leve eco reverbera no galpão, enquanto uma sombra distante se move "
           "entre as vigas. O tempo para descobrir o arquivo está se esgotando, "
           "aumentando a pressão no local."),
        o="failure", l="Galpão abandonado",
        s="A investigação falha e o mecanismo permanece travado.",
        f=[{"k": "observation", "s": "O mecanismo permanece travado.", "p": True}],
    )
    assert validate_scene_continuation(
        proposal,
        facts=({"fact_type": "mechanics.resolution", "value": {"is_success": False}},),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Investigo o cadeado.",
    ).outcome == "failure"


def _nominal_attempt(*, subject="o personagem", target="", predicate="falha"):
    return (
        f"Ao examinar o cadeado, {subject} percebe que o mecanismo está corroído e travado; "
        f"a tentativa de abrir{target} {predicate}, deixando o metal rangendo sem ceder."
    )


def _check_nominal_attempt(proposal, declared="Investigo o cadeado."):
    _validate_implicit_player_contact(
        proposal, authorized_actions=_action_authorizations(declared), player_input=declared,
    )


@pytest.mark.parametrize("subject", ["você", "seu personagem", "sua personagem", "o personagem", "a personagem"])
@pytest.mark.parametrize("field", ["n", "s", "f", "t", "r"])
def test_explicit_player_inspection_binds_its_nominal_attempt_in_visible_fields(subject, field):
    claim = _nominal_attempt(subject=subject)
    value = [{"k": "observation", "s": claim}] if field == "f" else [claim] if field in {"t", "r"} else claim
    with pytest.raises(SceneProposalError) as caught:
        _check_nominal_attempt(_proposal(**{field: value}))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_nominal_open_attempt"


@pytest.mark.parametrize("declared", [
    "Abro o cadeado.", "Vou abrir o cadeado.", "Observo o cadeado e abro o cadeado.",
])
@pytest.mark.parametrize("target", ["", " o cadeado"])
def test_nominal_opening_attempt_keeps_existing_positive_open_authorization(declared, target):
    _check_nominal_attempt(_proposal(n=_nominal_attempt(target=target)), declared)


@pytest.mark.parametrize("declared", [
    "Observo o cadeado.",
    "Abro a porta.",
    "Não abro o cadeado.",
    "Mara abre o cadeado.",
    "Se eu abrir o cadeado, descobrirei algo?",
    "Abro o cadeado se Mara concordar.",
])
def test_nominal_attempt_preserves_actor_negation_hypothesis_and_target_boundaries(declared):
    with pytest.raises(SceneProposalError) as caught:
        _check_nominal_attempt(_proposal(n=_nominal_attempt()), declared)
    assert caught.value.evidence["rule"] == "undeclared_player_nominal_open_attempt"


def test_explicit_nominal_target_cannot_be_replaced_by_the_inspected_barrier():
    with pytest.raises(SceneProposalError) as caught:
        _check_nominal_attempt(_proposal(n=_nominal_attempt(target=" a porta")), "Abro o cadeado.")
    assert caught.value.evidence["rule"] == "undeclared_player_nominal_open_attempt"


@pytest.mark.parametrize("claim", [
    _nominal_attempt(subject="Mara"),
    _nominal_attempt(subject="ela"),
    ("Ao examinar o cadeado, o personagem percebe que Mara tenta abrir a porta; "
     "a tentativa de abrir falha."),
    ("Ao examinar o cadeado, o personagem percebe que o mecanismo está corroído e travado; "
     "se a tentativa de abrir falhar, o metal continuará no lugar."),
    ("Ao examinar o cadeado, o personagem percebe que o mecanismo está corroído e travado; "
     "a tentativa de Mara de abrir falha."),
])
def test_npc_or_conditional_nominal_attempt_is_not_a_performed_player_action(claim):
    _check_nominal_attempt(_proposal(n=claim, p=["Mara"]))


@pytest.mark.parametrize("grant", ["O cadeado abre.", "Você descobre o arquivo."])
def test_failed_nominal_attempt_never_waives_a_later_mechanical_grant(grant):
    with pytest.raises(SceneProposalError) as caught:
        validate_mechanical_narrative(
            _nominal_attempt() + " " + grant, outcome="failure", player_input="Abro o cadeado.",
        )
    assert caught.value.code == "scene_failure_granted_goal"


@pytest.mark.parametrize("question", [
    "Como deseja prosseguir em relação à escrita da história?",
    "Como deseja prosseguir em relação à narrativa?",
    "Como deseja prosseguir diante da escrita da história?",
    "Como deseja prosseguir diante da narrativa?",
])
def test_scene_context_tail_does_not_delegate_narrative_authorship(question):
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question)
    assert caught.value.code == "scene_player_prompt_not_actionable"


@pytest.mark.parametrize("tail", [
    " se Mara não entregar a chave.",
    " nas mãos de Mara.",
    ", se Mara não entregar a chave.",
    ", nas mãos de Mara.",
])
def test_nominal_failure_suffix_does_not_override_its_condition_or_npc_owner(tail):
    prefix = _nominal_attempt().split(", deixando", 1)[0]
    _check_nominal_attempt(_proposal(n=prefix + tail, p=["Mara"]))


@pytest.mark.parametrize("question", [
    "Como deseja prosseguir diante da escrita na parede?",
    "Como deseja prosseguir em relação ao bilhete?",
    "Como deseja prosseguir diante da reação de Mara?",
])
def test_scene_context_remains_concrete_without_banning_written_clues(question):
    _validate_player_prompt(question, npc_aliases=("Mara",))


@pytest.mark.parametrize("tail", [
    " se Mara não entregar a chave.", " nas mãos de Mara.",
])
def test_conditional_or_npc_attempt_cannot_waive_a_later_player_opening(tail):
    prefix = _nominal_attempt().split(", deixando", 1)[0]
    proposal = _proposal(n=prefix + tail + " Você abre a porta lateral.")
    with pytest.raises(SceneProposalError) as caught:
        _admit(proposal)
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"


@pytest.mark.parametrize("tail", [
    " se Mara não entregar a chave.", " nas mãos de Mara.",
])
def test_conditional_or_npc_attempt_cannot_waive_a_later_mechanical_grant(tail):
    prefix = _nominal_attempt().split(", deixando", 1)[0]
    with pytest.raises(SceneProposalError) as caught:
        validate_mechanical_narrative(
            prefix + tail + " Você descobre o arquivo.",
            outcome="failure", player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_failure_granted_goal"


@pytest.mark.parametrize("predicate", ["falha", "falhou"])
def test_unqualified_nominal_failure_keeps_its_explicit_player_context(predicate):
    claim = _nominal_attempt(predicate=predicate).split(", deixando", 1)[0] + "."
    with pytest.raises(SceneProposalError) as caught:
        _check_nominal_attempt(_proposal(n=claim))
    assert caught.value.evidence["rule"] == "undeclared_player_nominal_open_attempt"
