"""Retained L4 object-state false positive and explicit-subject counterproofs."""
from datetime import timedelta

import pytest

from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_input_service import prepare_campaign_source_player_action
from api.campaign_source_profile import (
    CampaignSourceProfileError, _PolicyView, _realizes_rule,
    validate_campaign_source_proposal,
)
from api.campaign_source_storage import create_campaign_source_session
from api.llm.contract import CancellationToken, utc_now
from api.persistence import SQLitePersistence
from api.scene_director_service import (
    SceneProposalError, expected_narrative_outcome, validate_scene_continuation,
)
from scripts.run_campaign_source_offline_trial import CONFIG, _initial_state

OBSERVED_L4_RESCUE = (
    'Você retira o registro da bancada baixa no Arquivo e o leva até a superfície seca na '
    'Galeria. Ele permanece intacto e protegido da umidade. Mara acompanha o deslocamento '
    'com atenção, sem interferir; ao vê-lo seguro, relaxa os ombros. “Assim está melhor. '
    'O registro foi preservado.” Com a ameaça afastada e o objetivo concluído, o silêncio '
    'retorna ao Arquivo.'
)


async def rescue_preparation(tmp_path):
    store = SQLitePersistence(tmp_path / 'record-state.sqlite3')
    await create_campaign_source_session(store, 'record-state', initial_state=_initial_state())
    claim = await prepare_campaign_source_player_action(
        store=store, session_id='record-state', operation_id='rescue',
        player_input='Retiro o registro', config=CONFIG,
        deadline=utc_now() + timedelta(seconds=30), cancellation=CancellationToken())
    capsule = claim.capsule
    assert capsule is not None
    packet = build_campaign_narrator_packet(capsule.campaign_request, capsule.campaign_effect)
    assert packet.beat.selected_option_id.startswith('R-05.')
    return capsule, packet


@pytest.mark.asyncio
async def test_l4_pronoun_failure_is_not_length_or_effect_failure(tmp_path):
    c, packet = await rescue_preparation(tmp_path)
    assert len(OBSERVED_L4_RESCUE.split()) == 59
    assert _realizes_rule(OBSERVED_L4_RESCUE, packet)
    view = _PolicyView(narrative=OBSERVED_L4_RESCUE, player_prompt='',
        outcome=expected_narrative_outcome(c.draft.facts),
        location=c.snapshot.canonical_scene.location,
        npcs_present=c.snapshot.canonical_scene.npcs_present)
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(view, facts=c.draft.facts,
            current_scene=c.snapshot.canonical_scene, player_input=packet.player_input,
            npc_aliases=c.snapshot.canonical_scene.npcs_present,
            require_player_prompt=False)
    assert caught.value.evidence == {
        'field': 'narrative', 'rule': 'undeclared_player_action',
        'subject': 'ambiguous_pronoun', 'clause_index': 1,
        'unauthorized_concepts': ['wait'],
    }


@pytest.mark.asyncio
async def test_explicit_record_subject_passes_without_changing_policy(tmp_path):
    c, packet = await rescue_preparation(tmp_path)
    text = OBSERVED_L4_RESCUE.replace('Ele permanece', 'O registro permanece')
    admitted = validate_campaign_source_proposal(
        {'n': text, 'q': '', 'realized_effects': packet.required_effects},
        packet=packet, facts=c.draft.facts, snapshot=c.snapshot)
    assert admitted.narrative == text
    assert packet.state_after.record_location == 'dry_surface'


@pytest.mark.asyncio
@pytest.mark.parametrize('replacement', [
    'Você permanece intacto e protegido da umidade.',
    'Seu personagem permanece intacto e protegido da umidade.',
    'Ele permanece parado.',
    'O registro permanece intacto e protegido da umidade. Você abre a porta.',
])
async def test_object_mention_does_not_authorize_player_or_unbound_action(tmp_path, replacement):
    c, packet = await rescue_preparation(tmp_path)
    text = OBSERVED_L4_RESCUE.replace('Ele permanece intacto e protegido da umidade.', replacement)
    with pytest.raises(CampaignSourceProfileError):
        validate_campaign_source_proposal(
            {'n': text, 'q': '', 'realized_effects': packet.required_effects},
            packet=packet, facts=c.draft.facts, snapshot=c.snapshot)
