"""Prospective regression from a closed synthetic batch; never re-score that batch.

The observed text is copied as a fixture. Every check uses local policy functions,
with no provider, artifact lookup, persistence, or change to the declared action.
"""
from datetime import datetime, timezone

import pytest

from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState
from api.turn_models import CanonicalFact


NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)
PLAYER_INPUT = 'Pergunto a Rui: "Quero conhecer este arquivo. Por onde posso começar, e por quê?"'
QUESTION = "O que você decide fazer a seguir?"
ORIGINAL_NARRATIVE = (
    'Rui inclina a cabeça, examinando o corredor de estantes que se estende ao fundo do arquivo. '
    '"Este lugar guarda registros de tudo que aconteceu aqui," ele diz, apontando para uma fileira '
    'de caixas marcadas com datas antigas. "Começar pelos documentos de 1998 costuma ser útil, '
    'porque muitos dos eventos que ainda repercutem hoje foram catalogados então. Mas se houver '
    'algo específico que você procura, talvez seja melhor seguir o índice na parede ao lado da '
    'porta principal, onde as categorias são listadas. Enquanto isso, o ar frio do ar-condicionado '
    'faz o papel das caixas ranger levemente, como se o próprio tempo estivesse se acomodando."'
)
DEPENDENT_INTEREST_NARRATIVE = (
    "Nina cruza os braços, observando o caos organizado da oficina. "
    '"Bom, tem muito aqui que chama a atenção sem precisar tocar. Primeiro, o cheiro de metal '
    "queimado que vem da bancada de solda, ainda quente, indica que alguém estava trabalhando "
    "há pouco. Depois, as luzes piscam de forma irregular, como se o gerador estivesse "
    "sobrecarregado. Também tem um som de gota d'água vindo do canto onde a pia está vazia, "
    "mas parece que algo está entupindo. Por fim, a parede ao fundo tem um painel de controle "
    "com alguns botões iluminados, mas sem explicação clara. Cada um desses detalhes pode ser "
    'importante, dependendo do que você procura."'
)
FRAME = (
    "Rui permanece junto às estantes do arquivo. A lâmpada ilumina as caixas e a mesa de madeira. "
    "O silêncio entre os corredores deixa cada palavra da conversa audível. "
)
ADVICE = "Mas se houver algo específico que você procura, talvez seja melhor seguir o índice"


def _check(
    narrative, *, player_aliases=(), protected_secrets=(), player_input=PLAYER_INPUT,
    location="Arquivo", npc_aliases=("Rui",),
):
    declaration = CanonicalFact(
        fact_id="hypothetical-interest-declaration", fact_type="action.declaration",
        predicate="declared_player_action", occurred_at=NOW,
        value={"player_input":player_input, "requires_roll":False,
               "summary":"A ação foi declarada sem teste mecânico."},
    )
    before = declaration.model_dump(mode="json")
    checked = validate_source_proposal(
        {"n":narrative, "q":QUESTION},
        current_scene=SceneState(location=location, npcs_present=npc_aliases),
        facts=(declaration,), player_input=player_input, player_aliases=player_aliases,
        npc_aliases=npc_aliases, protected_secrets=protected_secrets,
    )
    assert declaration.model_dump(mode="json") == before
    assert checked.narrative == " ".join(narrative.split())
    assert checked.player_prompt == QUESTION
    return checked


def _reject(narrative, *, concepts=None, **kwargs):
    with pytest.raises(SceneProposalError, match="scene_player_agency_violation") as rejected:
        _check(narrative, **kwargs)
    if concepts is not None:
        assert set(rejected.value.evidence["unauthorized_concepts"]) >= set(concepts)
    return rejected.value.evidence


def test_closed_batch_exact_proposal_is_not_a_performed_search_or_movement():
    _check(ORIGINAL_NARRATIVE)


def test_dialogue_comparison_dependent_interest_is_not_a_performed_search():
    _check(
        DEPENDENT_INTEREST_NARRATIVE,
        player_input=(
            'Pergunto a Nina: "Quero entender o que merece atenção nesta oficina sem tocar '
            'nos objetos. O que você pode me contar daqui?"'
        ),
        location="Oficina", npc_aliases=("Nina",),
    )


def test_live_dialogue_conditional_observation_is_not_a_performed_inspection():
    _check(
        FRAME + (
            'Nina diz: "Se você observar o trabalho em progresso, verá onde a próxima '
            'etapa se encaixa. Também há ferramentas ao lado para indicar o próximo ajuste."'
        ),
        player_input='Pergunto a Nina: "O que merece minha atenção agora?"',
        location="Oficina", npc_aliases=("Nina",),
    )


def test_live_dialogue_closed_npc_preference_question_does_not_assign_desire():
    _check(
        FRAME + 'Rui diz: "A etiqueta de 1998 é um começo possível. Você quer ver os vestígios?"',
    )


def test_closed_npc_preference_question_does_not_hide_prior_player_assertion():
    _reject(
        FRAME + 'Rui diz: "Você abriu a caixa. Você quer ver os vestígios?"',
        concepts={"interact"},
    )


def test_unclosed_npc_preference_question_remains_rejected():
    evidence = _reject(
        FRAME + 'Rui diz: "A etiqueta é um começo. Você quer ver os vestígios',
    )
    assert evidence["rule"] == "assigned_internal_state"


def test_conditional_observation_does_not_hide_later_performed_inspection():
    _reject(
        FRAME + (
            'Nina diz: "Se você observar o trabalho, verá o padrão." '
            "Você examina as ferramentas da bancada."
        ),
        concepts={"inspect"},
        player_input='Pergunto a Nina: "O que merece minha atenção agora?"',
        location="Oficina", npc_aliases=("Nina",),
    )


@pytest.mark.parametrize("replacement,concepts", [
    ("dependendo do que você procura nas bancadas.", {"inspect"}),
    ("dependendo do que você procura. Você abre o painel.", {"interact"}),
])
def test_dependent_interest_does_not_mask_performed_actions(replacement, concepts):
    narrative = DEPENDENT_INTEREST_NARRATIVE.replace(
        'dependendo do que você procura."', replacement + '"',
    )
    _reject(
        narrative, concepts=concepts,
        player_input='Pergunto a Nina: "O que merece atenção aqui?"',
        location="Oficina", npc_aliases=("Nina",),
    )


@pytest.mark.parametrize("subject,aliases", [
    ("você",()), ("seu personagem",()), ("sua personagem",()), ("o personagem",()),
    ("a personagem",()), ("Neófito",("Neófito",)), ("Ana Maria",("Ana Maria",)),
])
def test_hypothetical_interest_with_known_player_subject(subject, aliases):
    _check(FRAME + ADVICE.replace("você",subject) + ".", player_aliases=aliases)


@pytest.mark.parametrize("before,after", [
    ('Rui diz: "','."'), ('Rui diz: “','.”'), ('Rui diz, "','."'),
    ("Rui diz: '",".'"), ("Rui diz: «",".»"), ("", "."),
])
def test_sentence_and_speech_boundaries_keep_the_advice_attributed(before, after):
    _check(FRAME + before + ADVICE + after)


@pytest.mark.parametrize("advice", [
    "Se houver algo específico que você procura, talvez seja melhor seguir o índice",
    "Mas se houver algo que você procura, talvez seja melhor seguir o índice",
    "Se houver algo que você procura, talvez seja melhor seguir o índice",
])
def test_bounded_interest_forms_with_same_modal_recommendation(advice):
    _check(FRAME + advice + ".")


@pytest.mark.parametrize("following,concepts", [
    (", e você abre a porta",{"interact"}),
    (", e abre a porta",{"interact"}),
    (" e abre a porta",{"interact"}),
    (", mas você procura documentos nas caixas",{"inspect"}),
    (", e você segue Rui pelo corredor",{"move"}),
    (", você abre a caixa",{"interact"}),
    (" e pega uma caixa",{"take"}),
])
def test_same_clause_actions_after_suggestion_are_not_masked(following, concepts):
    evidence = _reject(FRAME + ADVICE + following + ".", concepts=concepts)
    assert evidence["clause_index"] == 0


@pytest.mark.parametrize("following,aliases,concepts", [
    ("Você abre uma caixa.",(),{"interact"}),
    ("Você procura documentos nas caixas.",(),{"inspect"}),
    ("Você segue Rui até a porta.",(),{"move"}),
    ("Neófito abre uma caixa.",("Neófito",),{"interact"}),
    ("Rui obriga você a abrir uma caixa.",(),{"interact"}),
])
def test_action_after_closing_quote_is_still_checked(following, aliases, concepts):
    _reject(FRAME + 'Rui diz: "' + ADVICE + '." ' + following,
            player_aliases=aliases, concepts=concepts)


@pytest.mark.parametrize("preceding,aliases,concepts", [
    ("Você abre uma caixa. ",(),{"interact"}),
    ("Você procura documentos nas caixas. ",(),{"inspect"}),
    ("Neófito segue Rui pelo corredor. ",("Neófito",),{"move"}),
    ("Rui faz você abrir uma caixa. ",(),{"interact"}),
])
def test_prior_executed_or_forced_action_is_not_erased(preceding, aliases, concepts):
    _reject(FRAME + preceding + ADVICE + ".", player_aliases=aliases, concepts=concepts)


@pytest.mark.parametrize("assertion,concepts", [
    ("Você procura documentos nas caixas, talvez seja melhor seguir o índice.",{"inspect","move"}),
    ("Há algo específico que você procura, talvez seja melhor seguir o índice.",{"inspect","move"}),
    ("Mas se houver algo específico que você procura, você segue o índice.",{"inspect","move"}),
    ("Mas se Rui confirmar que você procura, talvez seja melhor seguir o índice.",{"inspect","move"}),
    ("Mas se houver algo específico que você procurou, talvez seja melhor seguir o índice.",{"inspect","move"}),
    ("Mas se houver algo específico que você procura nas caixas, talvez seja melhor seguir o índice.",{"inspect","move"}),
    ("Mas se houver algo específico que você procura, será melhor seguir o índice.",{"inspect","move"}),
    ("Mas se houver algo específico que você procura, talvez seja melhor seguiria o índice.",{"inspect"}),
])
def test_non_equivalent_conditions_and_factual_search_are_not_exempt(assertion, concepts):
    _reject(FRAME + assertion, concepts=concepts)


def test_custom_alias_followed_by_action_keeps_its_subject():
    _reject(FRAME + ADVICE.replace("você","Neófito") + " e abre uma caixa.",
            player_aliases=("Neófito",), concepts={"interact"})


def test_known_npc_may_still_act_after_player_advice():
    _check(FRAME + ADVICE + ". Rui abre uma caixa e aponta o índice.")


def test_accepting_advice_does_not_grant_later_action_authorizations():
    _check(FRAME + ADVICE + ".")
    _reject(FRAME + "Você procura documentos nas caixas e segue Rui.",
            concepts={"inspect","move"})


def test_protected_information_inside_the_same_quote_is_still_rejected():
    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        _check(ORIGINAL_NARRATIVE, protected_secrets=("o índice na parede ao lado da porta principal",))


def test_internal_contract_text_inside_the_same_quote_is_still_rejected():
    with pytest.raises(SceneProposalError, match="scene_internal_content"):
        _check(FRAME + 'Rui diz: "' + ADVICE + '; o pool de dados aumentou."')


def test_player_internal_state_after_the_advice_is_not_masked():
    evidence = _reject(FRAME + ADVICE + ". Você deseja abandonar o arquivo.")
    assert evidence["rule"] == "assigned_internal_state"


def test_existing_word_ceiling_remains_150():
    with pytest.raises(SceneProposalError, match="scene_narrative_too_long"):
        _check(ORIGINAL_NARRATIVE + " A poeira cobre as caixas." * 15)
