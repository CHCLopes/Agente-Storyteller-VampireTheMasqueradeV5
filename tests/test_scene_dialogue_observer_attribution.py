"""Local observer attribution, without changing declared action authority."""
import pytest

from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError, _action_authorizations
from api.scene_service import SceneState
from api.turn_models import CanonicalFact

OBSERVED = {'n': 'Mara inclina a cabeça, o sorriso sumindo aos poucos, substituído por uma expressão mais séria. Ela levanta a mão, os dedos traçando um gesto invisível no ar, como se tentasse dar forma a um conceito abstrato. — “Intenção é o que resta quando a matéria falha”, diz ela, a voz baixa, quase um sussurro. “Cada obra traz a marca de quem a criou, mas também a ausência do que não pôde ser dito. É sobre o que ficou de fora, não só sobre o que está ali.” Ela para, observando você com atenção, esperando para ver se a explicação ressoa ou se permanece vaga.', 'q': 'Como você responde a Mara?'}
OBSERVED_FACTS = [{'fact_id': 'fact-f5a9c4baf24aa3d7f1178422b777881e006c073ff3c9a06084bc42fbc2b389f9', 'fact_type': 'action.declaration', 'importance': 0.5, 'occurred_at': '2026-09-12T20:36:23.098165Z', 'predicate': 'declared_player_action', 'schema_version': '1.0', 'source_refs': [{'record_id': 'narrative_source_preparation.prepare_source_turn_draft', 'record_type': 'deterministic_module', 'relation': 'produced_by', 'schema_version': '1.0'}], 'subject': None, 'tags': ['action', 'declaration'], 'value': {'player_input': 'Digo a Mara: "Mara, explique melhor sua resposta."', 'requires_roll': False, 'summary': 'A ação foi declarada sem teste mecânico.'}, 'visibility': 'player'}]
PLAYER_INPUT = 'Digo a Mara: "Mara, explique melhor sua resposta."'

FILLER = (' A chuva pesa contra a janela enquanto um rádio chia no balcão. '
    'Uma corrente bate na porta, rompendo o silêncio da sala e ecoando pelo corredor, onde a luz começa a falhar.')


def check(text, *, players=('Neófito',), npcs=('Mara', 'Ivo')):
    return validate_source_proposal({'n': text + FILLER, 'q': 'Qual será sua próxima atitude?'},
        current_scene=SceneState(location='Galeria', npcs_present=('Mara',)),
        facts=(), player_input=PLAYER_INPUT, player_aliases=players, npc_aliases=npcs)


def test_recorded_t2_is_admitted_without_rewriting_text_or_declaring_wait():
    assert not any(concept == 'wait' for concept, _ in _action_authorizations(PLAYER_INPUT))
    result = validate_source_proposal(OBSERVED,
        current_scene=SceneState(location='Galeria', npcs_present=('Mara',)),
        facts=tuple(CanonicalFact.model_validate(fact) for fact in OBSERVED_FACTS),
        player_input=PLAYER_INPUT, player_aliases=(), npc_aliases=('Mara',))
    assert result.model_dump(by_alias=True) == OBSERVED


@pytest.mark.parametrize('text', [
    'Mara observa você, esperando em silêncio.',
    'Mara inclina a cabeça. Ela para, observando você com atenção, esperando para ver se a resposta faz sentido ou se permanece confusa.',
    'Mara sorri. Ela observa você, aguardando em silêncio.',
    'Ivo inclina a cabeça. Ele para, observando Neófito com cuidado, esperando para ver se a informação ressoa ou se permanece incompleta.',
    'Mara inclina a cabeça. Ela para, observando você, esperando para ver se a ideia permanece ambígua.',
    'Mara sorri. “A resposta é incerta.” Ela para, observando você, aguardando em silêncio.',
])
def test_bounded_observer_and_informational_state_keep_their_subject(text):
    assert check(text).narrative.startswith(text)


@pytest.mark.parametrize('text', [
    'Ela para, observando você com atenção, esperando em silêncio.',
    '“Mara inclina a cabeça.” Ela para, observando você com atenção, esperando em silêncio.',
    'A voz menciona Mara. Ela para, observando você com atenção, esperando em silêncio.',
    'Mara sorri. O visitante inclina a cabeça. Ela para, observando você, esperando em silêncio.',
    'Mara sorri, Visitante inclina a cabeça. Ela para, observando você, esperando em silêncio.',
    'Mara sorri, a visitante caminha. Ela para, observando você, esperando em silêncio.',
    '— Mara sorri. Ela para, observando você, esperando em silêncio.',
    'Mara sorri. Neófito sorri. Ela para, observando você, esperando em silêncio.',
    'Mara observa você esperando em silêncio.',
    'Mara observa você, que espera pela explicação.',
    'Mara observa você, mas você permanece parado.',
    'Mara observa você, esperando em silêncio, enquanto Neófito abre a porta.',
    'Mara observa você, esperando para ver se sua mão permanece imóvel.',
    'Mara observa você, esperando para ver se a mão permanece imóvel.',
    'Mara observa você, esperando para ver se a sua resposta permanece vaga.',
    'Mara observa você, esperando para ver se Neófito permanece parado.',
    # The later implicit subject is ambiguous: preserve conservative refusal,
    # without claiming that this sentence necessarily assigns the player an act.
    'Mara observa você, esperando para ver se a resposta permanece vaga, e abre a porta.',
    'Mara observa você, esperando para ver se a explicação ressoa ou se você permanece parado.',
    'Mara observa você, esperando para ver se a explicação ressoa ou se a mão permanece imóvel.',
    'Mara observa você, força sua mão a tocar o cadeado.',
])
def test_attribution_does_not_cross_ambiguous_or_player_subjects(text):
    with pytest.raises(SceneProposalError) as caught:
        check(text)
    assert caught.value.code == 'scene_player_agency_violation'


def test_npc_expectation_keeps_existing_conservative_admission_without_asserting_action():
    # A wished/expected act is not thereby completed; this test preserves the
    # existing conservative gate, it does not claim a semantic agency violation.
    with pytest.raises(SceneProposalError):
        check('Mara observa você, esperando que você abra a porta.')


@pytest.mark.parametrize('players,npcs', [(('Mara',), ('Mara',)), (('Neófito',), ())])
def test_alias_collision_or_missing_npc_cannot_establish_observer(players, npcs):
    with pytest.raises(SceneProposalError):
        check('Mara sorri. Ela para, observando você, esperando em silêncio.', players=players, npcs=npcs)
