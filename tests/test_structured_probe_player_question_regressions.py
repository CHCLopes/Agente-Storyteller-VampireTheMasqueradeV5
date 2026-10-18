"""An elided player-intent question retains the existing admission boundaries."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _validate_player_prompt,
    validate_scene_continuation,
)
from api.scene_service import SceneState


OBSERVED_QUESTION = "O que deseja fazer agora?"
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


def _admit(proposal, *, player_input="Observo o cais."):
    return validate_scene_continuation(
        proposal, facts=(), current_scene=SceneState(location="Cais municipal"),
        player_input=player_input,
    )


def test_observed_elided_question_closes_an_otherwise_valid_proposal():
    assert _admit(_proposal("O que você faz agora?")).outcome == "unresolved"
    assert _admit(_proposal()).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que Mara deseja fazer agora?",
    "O que a informante deseja fazer agora?",
    "O que deseja fazer Mara agora?",
    "O que deseja fazer a informante agora?",
    "O que deseja fazer agora, Mara?",
    "O que deseja fazer, Mara, agora?",
    "O que Mara deseja fazer enquanto você espera?",
    "O que Mara sabe sobre o que deseja fazer agora?",
    "O que a sombra do seu personagem deseja fazer agora?",
    "O que o personagem de Mara deseja fazer agora?",
    "O que deseja fazer com a história agora?",
    "O que deseja fazer em relação à escrita da história?",
    "O que deseja fazer diante da narrativa?",
    "O que a história deseja fazer agora?",
    "O que deseja fazer: qual é a origem do vulto?",
    "O que significa fazer isso agora?",
    "Você deseja fazer algo agora?",
    "O que deseja fazer agora",
    "Deseja fazer algo agora.",
])
@pytest.mark.parametrize("registered", [False, True])
def test_elided_intent_does_not_address_npc_story_world_or_closed_choices(question, registered):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(
            question, npc_aliases=("Mara", "informante") if registered else (),
        )


@pytest.mark.parametrize("question", [
    "O que deseja fazer?", OBSERVED_QUESTION,
    "O que deseja fazer a seguir?", "O que deseja fazer em seguida?",
])
@pytest.mark.parametrize("registered", [False, True])
def test_elided_intent_with_an_optional_temporal_adjunct_invites_the_player(question, registered):
    _validate_player_prompt(question, npc_aliases=("Mara",) if registered else ())


@pytest.mark.parametrize("subject", [
    "você", "seu personagem", "sua personagem", "o personagem", "a personagem", "Neófito", "Ana Luz",
])
def test_explicit_subject_reuses_registered_player_aliases(subject):
    _validate_player_prompt(
        f"O que {subject} deseja fazer agora?",
        player_aliases=("Neófito", "Ana Luz"), npc_aliases=("Mara",),
    )


@pytest.mark.parametrize("question", [
    "O que desejo fazer agora?",
    "O que deseja fazer agora ou escolher para a história?",
    'Mara pergunta "O que deseja fazer agora?"',
])
def test_intent_cue_cannot_be_extracted_from_author_speech_or_another_clause(question):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(question, npc_aliases=("Mara",))


def test_intent_question_keeps_the_existing_word_limit():
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(
            "O que deseja fazer agora diante do cadeado travado e da presença misteriosa "
            "que observa o galpão?"
        )
    assert caught.value.code == "scene_player_prompt_too_long"


@pytest.mark.parametrize("question", [OBSERVED_QUESTION, "O que fazes?"])
def test_intent_question_does_not_authorize_a_narrated_physical_action(question):
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(question, n="Você abre a porta lateral. " + NARRATIVE))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"


@pytest.mark.parametrize("question", [OBSERVED_QUESTION, "O que fazes?"])
def test_intent_question_does_not_waive_a_protected_secret(question):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(question, s="O Xerife armou uma emboscada no cais."),
            facts=(), current_scene=SceneState(location="Cais municipal"),
            player_input="Observo o cais.",
            protected_secrets=("O Xerife armou uma emboscada no cais.",),
        )
    assert caught.value.code == "scene_secret_disclosed"


@pytest.mark.parametrize("question", [OBSERVED_QUESTION, "O que fazes?"])
def test_intent_question_does_not_waive_a_mechanical_contradiction(question):
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(
                question, n="A investigação falha. O cadeado abre. " + NARRATIVE,
                o="failure", f=[{"k": "observation", "s": "Um brilho aparece na água.", "p": True}],
            ),
            facts=({"fact_type": "mechanics.resolution", "value": {"is_success": False}},),
            current_scene=SceneState(location="Cais municipal"),
            player_input="Investigo o cadeado.",
        )
    assert caught.value.code == "scene_failure_granted_goal"



def test_undeclared_eye_opening_remains_a_player_action():
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(n="Você abre os olhos. " + NARRATIVE))
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


def test_explicitly_declared_eye_opening_remains_authorized():
    assert _admit(
        _proposal(n="Você abre os olhos. " + NARRATIVE), player_input="Abro os olhos.",
    ).outcome == "unresolved"


def test_declared_door_opening_does_not_authorize_eye_opening():
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(n="Você abre os olhos. " + NARRATIVE), player_input="Abro a porta.")
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"


def test_declared_eye_opening_does_not_authorize_a_following_door_opening():
    with pytest.raises(SceneProposalError) as caught:
        _admit(
            _proposal(n="Você abre os olhos. Você abre a porta lateral. " + NARRATIVE),
            player_input="Abro os olhos.",
        )
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"
    assert caught.value.evidence["clause_index"] == 1


def test_npc_eye_opening_is_not_attributed_to_the_player():
    assert validate_scene_continuation(
        _proposal(n="Mara abre os olhos. " + NARRATIVE, p=["Mara"]), facts=(),
        current_scene=SceneState(location="Cais municipal", npcs_present=("Mara",)),
        player_input="Observo o cais.", npc_aliases=("Mara",),
    ).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que quer fazer agora?",
    "O que você quer fazer agora?",
    "O que gostaria de fazer agora?",
    "Como gostaria de prosseguir?",
    "O que deseja fazer diante de Mara?",
    "O que deseja fazer em relação ao cadeado?",
])
def test_audited_modal_or_scene_context_question_invites_the_player(question):
    _validate_player_prompt(question, npc_aliases=("Mara", "informante"))
    assert _admit(_proposal(question)).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "Você abre a porta. O que deseja fazer agora?",
    "Você abre os olhos: O que deseja fazer agora?",
    "Escolha o passado de Mara: O que deseja fazer agora?",
    "O que deseja fazer agora? enquanto você abre a porta?",
    "O que você faz agora? Quem Mara obedece?",
])
def test_audited_cue_cannot_hide_an_assertion_or_a_second_question(question):
    with pytest.raises(SceneProposalError):
        _admit(_proposal(question))


@pytest.mark.parametrize("modal", ["deseja fazer", "quer fazer", "gostaria de fazer"])
@pytest.mark.parametrize("template", [
    "O que Mara {modal} agora?",
    "O que {modal} Mara agora?",
    "O que {modal} agora, Mara?",
    "O que {modal} diante da narrativa?",
    "O que {modal} em relação à escrita da história?",
    "O que {modal} diante do cadeado: quem Mara obedece?",
    "O que {modal} diante do cadeado. Você abre a porta?",
])
def test_modal_variants_preserve_npc_meta_and_sentence_boundaries(modal, template):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(template.format(modal=modal), npc_aliases=("Mara",))


@pytest.mark.parametrize("question", [
    "Como Mara gostaria de prosseguir?",
    "Como gostaria de prosseguir Mara?",
    "Como gostaria de prosseguir, Mara?",
    "Como gostaria de prosseguir em relação à narrativa?",
    "Como gostaria de prosseguir diante da escrita da história?",
    "Você abre a porta. Como gostaria de prosseguir?",
    "Escolha o passado de Mara: Como gostaria de prosseguir?",
    "Você abre os olhos: Como deseja prosseguir?",
])
def test_modal_continuation_remains_a_whole_player_question(question):
    with pytest.raises(SceneProposalError):
        _admit(_proposal(question))


@pytest.mark.parametrize("question", [
    "O que você gostaria de fazer a seguir?",
    "O que Neófito quer fazer diante de Mara?",
    "O que Ana Luz gostaria de fazer em relação ao cadeado?",
    "Como gostaria de prosseguir diante de Mara?",
    "Como Neófito gostaria de prosseguir em relação ao cadeado?",
])
def test_modals_reuse_player_aliases_without_assigning_context_npcs(question):
    _validate_player_prompt(
        question, player_aliases=("Neófito", "Ana Luz"), npc_aliases=("Mara",),
    )


@pytest.mark.parametrize("literal", [
    "'Quem vem?'", '"Quem vem?"', "“Quem vem?”", "«Quem vem?»", "'Quem vem? Quem fica?'",
])
def test_question_marks_inside_a_quoted_inscription_are_not_another_prompt(literal):
    assert _admit(_proposal(f"Como você reage ao bilhete {literal}?")).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que você faz agora? Quem Mara obedece?",
    "O que gostaria de fazer? O que significa a marca?",
    "O que você faz? 'Quem vem?' Quem Mara obedece?",
    "O que você faz? 'Quem Mara obedece?",
])
def test_only_balanced_literals_can_exempt_question_marks(question):
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question, npc_aliases=("Mara",))
    assert caught.value.evidence["reason"] == "multiple_questions"


@pytest.mark.parametrize("literal", ["‘Quem vem?’", "‘Quem vem? Quem fica?’"])
def test_typographic_single_quoted_inscription_preserves_its_literal_questions(literal):
    assert _admit(_proposal(f"Como você reage ao bilhete {literal}?")).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que você faz? ‘Quem Mara obedece?",
    "O que você faz? Quem Mara obedece’ ?",
    "O que você faz? ‘Quem vem?’ Quem Mara obedece?",
])
def test_unbalanced_typographic_single_quotes_cannot_hide_another_question(question):
    with pytest.raises(SceneProposalError) as caught:
        _validate_player_prompt(question, npc_aliases=("Mara",))
    assert caught.value.evidence["reason"] == "multiple_questions"


PRESUPPOSED_OPENINGS = (
    "O que deseja fazer diante do cadeado enquanto você abre a porta?",
    "O que você faz diante da porta que você acaba de abrir?",
)


@pytest.mark.parametrize("question", PRESUPPOSED_OPENINGS)
@pytest.mark.parametrize("player_input", [
    "Observo o cais.", "Não abro a porta.", "Nunca abro a porta.",
    "Se eu abrir a porta, observo o cais.", "Abro a porta se Mara permitir.",
    "Mara abre a porta.", "Mara diz que eu abro a porta.",
    '"Abro a porta."', "‘Abro a porta.’", "Digo: Abro a porta.",
    "Abro a grade.", "Abro o cadeado.",
    "‘Observo o cais. Abro a porta.’",
])
def test_presupposed_barrier_opening_requires_a_positive_player_declaration(question, player_input):
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(question), player_input=player_input)
    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "player_prompt"
    assert caught.value.evidence["rule"] == "presupposed_player_barrier_open"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


@pytest.mark.parametrize("question", PRESUPPOSED_OPENINGS)
@pytest.mark.parametrize("player_input", [
    "Abro a porta.", "Eu abro a porta.", "Vou abrir a porta.",
    "Observo o cais e abro a porta.",
])
def test_presupposed_barrier_opening_can_be_grounded_in_the_declared_action(question, player_input):
    assert _admit(_proposal(question), player_input=player_input).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que deseja fazer diante do cadeado enquanto Mara espera?",
    "O que deseja fazer diante do cadeado enquanto Mara abre a porta?",
    "O que deseja fazer diante do cadeado enquanto você espera?",
    "O que deseja fazer diante do cadeado enquanto você não abre a porta?",
    "O que deseja fazer diante do cadeado enquanto você pode abrir a porta?",
    "O que deseja fazer diante do cadeado se você abrir a porta?",
    "O que você faz diante da porta que Mara acaba de abrir?",
    "O que você faz diante da porta que você pode abrir?",
    "O que você faz diante da porta que você não abriu?",
    "O que você faz diante da porta que você abrirá?",
    "O que você faz enquanto você abre a porta se Mara permitir?",
    'Como você reage ao bilhete “enquanto você abre a porta”?',
    'Como você reage ao bilhete “porta que você acaba de abrir”?',
])
def test_npc_context_and_nonperformed_opening_questions_do_not_assign_player_actions(question):
    assert _admit(_proposal(question)).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que deseja fazer diante do cadeado enquanto você abre a porta lateral?",
    "O que você faz diante da porta lateral que você acaba de abrir?",
])
def test_presupposed_opening_keeps_the_barrier_target_specific(question):
    assert _admit(_proposal(question), player_input="Abro a porta lateral.").outcome == "unresolved"
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(question), player_input="Abro a porta traseira.")
    assert caught.value.evidence["rule"] == "presupposed_player_barrier_open"


@pytest.mark.parametrize("subject", ["seu personagem", "a personagem", "Neófito", "Ana Luz"])
@pytest.mark.parametrize("template", [
    "O que você faz enquanto {subject} abre a porta?",
    "O que faz diante da porta que {subject} acaba de abrir?",
])
def test_presupposed_opening_uses_explicit_registered_player_subjects(subject, template):
    question = template.format(subject=subject)
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(question), facts=(), current_scene=SceneState(location="Cais municipal"),
            player_input="Observo o cais.", player_aliases=("Neófito", "Ana Luz"),
            npc_aliases=("Mara",),
        )
    assert caught.value.evidence["rule"] == "presupposed_player_barrier_open"


@pytest.mark.parametrize("question", [
    "O que você faz enquanto você abre a porta, se Mara permitir?",
    "O que você faz enquanto você abre a porta, caso Mara permita?",
])
def test_a_comma_before_the_opening_condition_preserves_its_hypothetical_scope(question):
    assert _admit(_proposal(question)).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que você faz enquanto você abre a porta e Mara foge se puder?",
    "O que você faz enquanto você abre a porta, Mara foge se puder?",
    "O que faz da porta que você acaba de abrir enquanto Mara foge se puder?",
])
def test_an_npc_action_condition_does_not_waive_the_independent_player_opening(question):
    with pytest.raises(SceneProposalError) as caught:
        _admit(_proposal(question))
    assert caught.value.evidence["rule"] == "presupposed_player_barrier_open"
    assert _admit(_proposal(question), player_input="Abro a porta.").outcome == "unresolved"


def test_observed_fazes_question_closes_an_otherwise_valid_proposal():
    assert _admit(_proposal("O que você faz agora?")).outcome == "unresolved"
    assert _admit(_proposal("O que fazes?")).outcome == "unresolved"


@pytest.mark.parametrize("question", [
    "O que fazes agora?",
    "O que fazes a seguir?",
    "O que fazes em seguida?",
    "O que fazes diante de Mara?",
    "O que fazes agora diante de Mara?",
    "O que fazes em relação ao cadeado?",
])
def test_fazes_invites_player_action_with_bounded_temporal_or_scene_context(question):
    _validate_player_prompt(question, npc_aliases=("Mara",))
    assert validate_scene_continuation(
        _proposal(question), facts=(), current_scene=SceneState(location="Cais municipal"),
        player_input="Observo o cais.", npc_aliases=("Mara",),
    ).outcome == "unresolved"


@pytest.mark.parametrize("question,npc_aliases", [
    ("O que Mara fazes?", ("Mara",)),
    ("O que a informante fazes?", ()),
    ("O que fazes Mara agora?", ()),
    ("O que fazes, Mara?", ("Mara",)),
    ("O que fazes agora, Celina?", ()),
    ("O que fazes diante da narrativa?", ()),
    ("O que fazes em relação à escrita da história?", ()),
    ("O que fazes: qual é a origem do vulto?", ()),
    ("Mara pergunta: O que fazes?", ("Mara",)),
    ("Você abre a porta. O que fazes?", ()),
    ("O que fazes? Quem Mara obedece?", ("Mara",)),
    ("O que fazes!", ()),
    ("O que fazes agora??", ()),
    ("O que fazes, agora?", ()),
    ("O que fazes...?", ()),
    ("O que fazes se Mara permitir?", ("Mara",)),
    ("O que fazes enquanto Mara espera?", ("Mara",)),
    ("Se Mara permitir, o que fazes?", ("Mara",)),
    ("O que tu fazes?", ()),
])
def test_fazes_does_not_extract_a_cue_from_npc_meta_world_or_other_clauses(question, npc_aliases):
    with pytest.raises(SceneProposalError):
        _validate_player_prompt(question, npc_aliases=npc_aliases)


def test_fazes_admitted_by_source_profile_keeps_question_out_of_attributed_narrative():
    from scripts import narrator_source_profile as profile

    question = "O que fazes?"
    proposal = profile.NarrativeSourceProposal.model_validate({"n": NARRATIVE, "q": question})
    projection = profile.create_source_projection(
        proposal, source_id="synthetic-fazes-source", session_id="synthetic-session",
        turn_id="synthetic-turn", invocation_id="synthetic-invocation",
        current_scene=SceneState(location="Cais municipal"), facts=(),
        player_input="Observo o cais.",
    )
    assert proposal.player_text == NARRATIVE + "\n\n" + question
    assert projection.text == projection.source.text == NARRATIVE
    assert question not in projection.source.text
    assert projection.source.source_policy == profile.VERSION
    assert projection.assessment.decision.value == "source_only"
    assert projection.assessment.semantic_status.value == "not_assessed"
