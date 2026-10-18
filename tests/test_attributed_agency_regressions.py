"""Temporal player choices retain the existing action-family rules."""

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    _action_authorizations,
    _action_signatures,
    _validate_declared_player_actions,
    _validate_implicit_player_contact,
    validate_scene_continuation,
)


OPENING_NARRATIVE = (
    "Você se encontra em um beco estreito, iluminado por néons trêmulos que "
    "lançam sombras sobre paredes grafitadas com símbolos arcanos. O ar cheira "
    "a fumaça de cigarro e a umidade de esgoto. Um som distante de sirenes ecoa, "
    "enquanto um gato preto cruza o caminho, desaparecendo na escuridão."
)
OBSERVED_SEARCH = (
    "Ao vasculhar o galpão, você encontra um velho mapa rasgado preso sob o "
    "rádio chiando, marcando rotas clandestinas e um ponto sinalizado no "
    "mezanino com o mesmo símbolo do cadeado."
)


def _proposal(**updates):
    payload = {
        "n": OPENING_NARRATIVE, "o": "unresolved", "l": "Beco estreito",
        "s": "Néons iluminam as paredes grafitadas de um beco.", "p": [],
        "f": [{"k": "observation", "s": "Sirenes ecoam ao longe."}],
        "t": [], "r": [], "q": "O que você faz agora?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def _check(proposal, declared="Onde estou?", *, player_aliases=()):
    authorizations = _action_authorizations(declared)
    _validate_declared_player_actions(
        proposal, authorized_actions=authorizations, npc_aliases=proposal.npcs_present,
        player_aliases=player_aliases,
    )
    _validate_implicit_player_contact(
        proposal, authorized_actions=authorizations, player_input=declared,
    )


def test_observed_opening_cannot_presuppose_exploration():
    proposal = _proposal(q="Qual será seu próximo passo ao explorar o beco?")
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal, facts=(), current_scene=None, player_input="Onde estou?",
        )
    assert caught.value.evidence == {
        "field": "player_prompt", "rule": "presupposed_player_action",
        "unauthorized_concepts": ["inspect"],
    }


def test_observed_temporal_search_is_not_general_investigation():
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=OBSERVED_SEARCH), "Investigo o galpão abandonado.")
    assert caught.value.evidence == {
        "field": "narrative", "rule": "undeclared_player_temporal_search",
        "unauthorized_concepts": ["inspect"],
    }


@pytest.mark.parametrize("question", [
    "Qual será seu próximo passo ao explorar o beco?",
    "O que você faz depois de explorar o beco?",
    "Como você reage após explorar o beco?",
])
@pytest.mark.parametrize("declared", ["Onde estou?", "Observo o beco.", "Investigo o beco."])
def test_temporal_exploration_requires_its_own_declared_family(question, declared):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(q=question), declared)
    assert caught.value.evidence["rule"] == "presupposed_player_action"


@pytest.mark.parametrize("declared", ["Exploro o beco.", "Eu exploro o beco.", "Vou explorar o beco.", "Explorar o beco."])
def test_temporal_question_can_refer_to_declared_exploration(declared):
    _check(_proposal(q="Qual será seu próximo passo ao explorar o beco?"), declared)


@pytest.mark.parametrize("question", [
    "Qual será seu próximo passo para explorar o beco?",
    "O que você faz se decidir explorar o beco?",
    "Como pretende explorar o beco?",
    "O que você faz antes de explorar o beco?",
    "O que você faz depois de Mara explorar o beco?",
    "O que você faz ao ver Mara explorar o beco?",
])
def test_future_conditional_npc_and_perception_questions_are_not_player_execution(question):
    _check(_proposal(q=question, p=["Mara"]))


@pytest.mark.parametrize("narrative", [
    "Mara explora o beco enquanto uma sirene ecoa.",
    "Você vê Mara explorar o beco enquanto a sirene ecoa.",
    "Você encontra uma exploração antiga descrita num mapa.",
    "Você encontra um explorador sentado no beco.",
])
def test_exploration_vocabulary_does_not_assign_npc_actions_or_nouns(narrative):
    _check(_proposal(n=narrative, p=["Mara"]))


@pytest.mark.parametrize("form", ["explorar", "exploro", "explora", "explorou", "explorando"])
def test_explicit_exploration_uses_its_own_family(form):
    assert ("inspect", "explore") in _action_signatures(form)


@pytest.mark.parametrize("field", ["n", "s", "f", "t", "r"])
def test_temporal_search_cannot_enter_visible_assertions_without_authorization(field):
    claim = "Ao vasculhar o galpão, você encontra um mapa."
    value = [{"k": "observation", "s": claim}] if field == "f" else [claim] if field in {"t", "r"} else claim
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(**{field: value}), "Investigo o galpão.")
    assert caught.value.evidence["rule"] == "undeclared_player_temporal_search"


@pytest.mark.parametrize("subject", ["você", "seu personagem", "sua personagem", "o personagem", "a personagem"])
def test_explicit_player_subject_owns_search_despite_preceding_npc(subject):
    text = f"Mara examina a parede. Ao vasculhar o galpão, {subject} encontra um mapa."
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=text, p=["Mara"]), "Investigo o galpão.")
    assert caught.value.evidence["rule"] == "undeclared_player_temporal_search"


@pytest.mark.parametrize("declared", ["Vasculho o galpão.", "Vou vasculhar o galpão.", "Vasculho o galpão abandonado."])
def test_matching_temporal_search_remains_authorized(declared):
    _check(_proposal(n=OBSERVED_SEARCH), declared)


@pytest.mark.parametrize("declared", ["Examino o galpão.", "Observo o galpão."])
def test_temporal_search_preserves_family_boundaries(declared):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=OBSERVED_SEARCH), declared)
    assert caught.value.evidence["rule"] == "undeclared_player_temporal_search"


@pytest.mark.parametrize("text", [
    "Ao vasculhar o galpão, Mara encontra um mapa.",
    "Mara se aproxima. Ao vasculhar o galpão, ela encontra um mapa.",
    "Se vasculhar o galpão, você poderá encontrar outro mapa.",
    "Caso decida vasculhar o galpão, você poderá encontrar outro mapa.",
    "Você vê Mara vasculhar o galpão enquanto o rádio chia.",
])
def test_npc_and_conditional_searches_remain_outside_temporal_player_assertion(text):
    _check(_proposal(n=text, p=["Mara"]), "Investigo o galpão.")


@pytest.mark.parametrize("field", ["n", "s", "f", "t", "r"])
@pytest.mark.parametrize("condition", ["Se você explorar", "Caso você explore"])
def test_conditional_exploration_remains_hypothetical_in_visible_fields(field, condition):
    claim = f"{condition} o beco, uma pista poderá aparecer."
    value = [{"k": "observation", "s": claim}] if field == "f" else [claim] if field in {"t", "r"} else claim
    _check(_proposal(**{field: value}))


@pytest.mark.parametrize("subject", ["seu personagem", "sua personagem", "Neófito"])
@pytest.mark.parametrize("condition,verb", [("Se", "explorar"), ("Caso", "explore")])
def test_direct_conditional_exploration_respects_player_aliases(subject, condition, verb):
    claim = f"{condition} {subject} {verb} o beco, uma pista poderá aparecer."
    _check(_proposal(n=claim), player_aliases=("Neófito",))


@pytest.mark.parametrize("claim", [
    "Se você não explorar o beco, nenhuma pista nova poderá aparecer.",
    "Caso você não explore o beco, nenhuma pista nova poderá aparecer.",
    "Se Mara explorar o beco, uma pista poderá aparecer.",
    "Caso Mara explore o beco, uma pista poderá aparecer.",
])
def test_negative_or_npc_condition_is_not_performed_player_exploration(claim):
    _check(_proposal(n=claim, p=["Mara"]))


@pytest.mark.parametrize("claim", [
    "Você explora o beco enquanto uma sirene ecoa ao longe.",
    "Se o rádio chiar, você explora o beco em busca da pista.",
    "Se Mara explorar o beco, você explora a rua em busca da pista.",
    "Se você explorar o beco, você explora a rua em busca da pista.",
    "Se você explorar o beco, uma pista poderá aparecer. Você explora a rua.",
    "Se você explorar o beco, uma pista poderá aparecer; você explora a rua.",
    "Se você explorar o beco, uma pista poderá aparecer e você explora a rua.",
    "Se você explorar o beco, uma pista poderá aparecer. Neófito explora a rua.",
    "Se você explorar o beco, você abre a porta lateral.",
])
def test_condition_never_authorizes_an_independent_player_action(claim):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n=claim, p=["Mara"]), player_aliases=("Neófito",))
    assert caught.value.code == "scene_player_agency_violation"


@pytest.mark.parametrize("declared", [
    "Se eu explorar o beco, uma pista poderá aparecer.",
    "Caso eu explore o beco, uma pista poderá aparecer.",
    "Não exploro o beco.",
    "Mara explora o beco.",
    "O que acontece se eu explorar o beco?",
    "Exploro o beco?",
    "Exploro o beco se Mara concordar.",
    "Exploro o beco ou observo a rua.",
    '"Exploro o beco", diz Mara.',
    "Mara diz: Exploro o beco.",
])
def test_exploration_mentions_do_not_authorize_player_execution(declared):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(n="Você explora o beco enquanto uma sirene ecoa ao longe."), declared)
    assert caught.value.evidence["rule"] == "undeclared_player_action"



def test_positive_coordinated_exploration_is_a_player_declaration():
    _check(
        _proposal(q="Qual será seu próximo passo ao explorar o beco?"),
        "Observo as paredes e exploro o beco.",
    )


@pytest.mark.parametrize("declared", [
    "Observo as paredes e eu exploro o beco.",
    "Observo as paredes e vou explorar o beco.",
    "Observo as paredes, mas exploro o beco.",
])
def test_coordinated_first_person_exploration_remains_authorized(declared):
    _check(_proposal(q="Qual será seu próximo passo ao explorar o beco?"), declared)


@pytest.mark.parametrize("declared", [
    "Observo as paredes e Mara explora o beco.",
    "Observo as paredes e não exploro o beco.",
    "Observo as paredes e explorar o beco.",
    "Se observo as paredes e exploro o beco, encontrarei algo?",
    "Caso eu observe as paredes e explore o beco, uma pista poderá aparecer.",
    "Observo as paredes e exploro o beco se Mara concordar.",
    'Mara diz: observo as paredes e exploro o beco.',
    '"Observo as paredes e exploro o beco", diz Mara.',
])
def test_coordinated_mentions_do_not_grant_exploration_authority(declared):
    with pytest.raises(SceneProposalError) as caught:
        _check(_proposal(q="Qual será seu próximo passo ao explorar o beco?"), declared)
    assert caught.value.evidence["rule"] == "presupposed_player_action"
