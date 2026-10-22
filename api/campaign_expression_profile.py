"""A1 structural admission plus inherited, deliberately incomplete prose guards."""
from __future__ import annotations

import hashlib
import json

from .campaign_expression_context import CampaignExpressionSnapshot, SOURCE_POLICY
from .campaign_expression_rendering import (
    CampaignExpressionProposal, CampaignExpressionPresentation, ComposedSource,
    ComposedProjection, compose_expression, verify_realization_plan,
)
from .campaign_source_profile import _PolicyView, _realizes_rule
from .campaign_progression_service import CampaignNarratorPacket
from .scene_director_service import validate_scene_continuation, expected_narrative_outcome


class CampaignExpressionProfileError(ValueError):
    def __init__(self, code='campaign_expression_proposal_invalid'):
        self.code = code
        super().__init__(code)


def validate_campaign_expression_proposal(value, *, plan, packet, facts, snapshot,
                                         player_aliases=(), npc_aliases=(), invocation_id=None):
    try:
        checked = CampaignNarratorPacket.model_validate(packet)
        source = CampaignExpressionSnapshot.model_validate(snapshot)
        if (checked.session_id != source.origin.scene_origin.session_id
                or checked.base_revision != source.current_turn
                or checked.state_before != source.progression):
            raise ValueError('campaign_expression_context_mismatch')
        plan = verify_realization_plan(plan, checked, tuple(f.fact_id for f in facts))
        result = compose_expression(value, plan=plan, invocation_id=invocation_id)
        view = _PolicyView(narrative=result.narrative, player_prompt=result.player_prompt,
                           outcome=expected_narrative_outcome(facts),
                           location=source.canonical_scene.location,
                           npcs_present=source.canonical_scene.npcs_present)
        validate_scene_continuation(view, facts=facts, current_scene=source.canonical_scene,
                                    player_input=checked.player_input, protected_secrets=(),
                                    player_aliases=player_aliases,
                                    npc_aliases=(*source.canonical_scene.npcs_present, *npc_aliases),
                                    require_player_prompt=checked.state_after.outcome is None)
        # Exact plan verification proves inclusion; inherited lexical checks are
        # only additional counterexample guards, never semantic certification.
        if not _realizes_rule(result.narrative, checked):
            raise ValueError('campaign_expression_counterexample')
        return result
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise CampaignExpressionProfileError() from None


def create_campaign_expression_projection(presentation, *, plan, packet, facts, snapshot,
                                          invocation_id, source_id, player_aliases=(), npc_aliases=()):
    checked = validate_campaign_expression_proposal(
        presentation.expression, plan=plan, packet=packet, facts=facts, snapshot=snapshot,
        invocation_id=invocation_id, player_aliases=player_aliases, npc_aliases=npc_aliases)
    if presentation != checked:
        raise CampaignExpressionProfileError('campaign_expression_presentation_mismatch')
    source = ComposedSource(source_id=source_id, session_id=packet.session_id,
                            turn_id=packet.turn_id, invocation_id=invocation_id,
                            text=checked.narrative, sha256=hashlib.sha256(checked.narrative.encode()).hexdigest())
    return ComposedProjection(source=source, text=checked.narrative, segments=checked.segments)


def build_campaign_expression_context(snapshot, packet, *, plan):
    source = CampaignExpressionSnapshot.model_validate(snapshot)
    if packet.session_id != source.origin.scene_origin.session_id or packet.state_before != source.progression:
        raise CampaignExpressionProfileError('campaign_expression_context_mismatch')
    # Keep source attribution without duplicating complete hashes/derivation
    # envelopes in the model request. Stored evidence remains lossless.
    history = [{'turn_id': item.source.turn_id, 'text': item.text,
                'segments': [{'start': s.start, 'end': s.end, 'origin': s.origin,
                              'speaker': s.speaker} for s in item.segments],
                'canonical_authority': 'prepared_events_only'} for item in source.sources]
    result = {'protocol': 'campaign-expression-context-v2', 'profile': SOURCE_POLICY,
              'canonical_scene': {'location': source.canonical_scene.location,
                                  'npcs_present': list(source.canonical_scene.npcs_present)},
              'causal_packet': packet.model_dump(mode='json'),
              'realization_plan': plan.model_dump(mode='json'),
              'attributed_sources': history, 'semantic_truth_assessed': False}
    if len(json.dumps(result, ensure_ascii=False, separators=(',', ':'))) > 12000:
        raise CampaignExpressionProfileError('campaign_expression_context_size_exceeded')
    return result
