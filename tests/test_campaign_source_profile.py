"""Offline campaign profile admission and counterexamples."""
import pytest

from api.campaign_progression_service import build_campaign_narrator_packet
from api.campaign_source_profile import (
    CampaignSourceProfileError, CampaignSourceProposal,
    build_campaign_source_context, validate_campaign_source_proposal,
)
from test_campaign_source_capsule import capsule


def inputs(narrative=None, *, effects=None):
    retained = capsule()
    packet = build_campaign_narrator_packet(retained.campaign_request, retained.campaign_effect)
    text = narrative or (
        "A água pinga da infiltração acima da bancada e se aproxima do registro. "
        "Mara avisa que o risco aumentou, apontando a superfície seca na Galeria. "
        "O registro permanece seco por enquanto; nenhuma folha foi movida. "
        "O som das gotas torna claro que a escolha seguinte ainda pertence a você."
    )
    proposal = CampaignSourceProposal(n=text, q="O que você faz agora?",
                                      realized_effects=effects or packet.required_effects)
    return retained, packet, proposal


def test_nonterminal_effect_is_presented_and_context_is_attributed():
    retained, packet, proposal = inputs()
    assert validate_campaign_source_proposal(
        proposal, packet=packet, facts=retained.draft.facts,
        snapshot=retained.snapshot,
    ) == proposal
    context = build_campaign_source_context(retained.snapshot, packet)
    assert context["causal_packet"]["preparation_sha256"] == retained.campaign_effect.effect_sha256
    assert context["attributed_sources"] == []


def test_effect_ids_do_not_substitute_for_narrative_realization():
    retained, packet, proposal = inputs(
        "A luz muda de tom nas paredes do Arquivo. Mara olha para a bancada "
        "sem dizer nada sobre a tarefa. O ar parece imóvel e o lugar continua "
        "como antes. Nenhuma consequência da espera é descrita neste texto. "
        "Ainda assim, a cena oferece espaço para outra decisão."
    )
    with pytest.raises(CampaignSourceProfileError, match="campaign_source_effect_not_realized"):
        validate_campaign_source_proposal(
            proposal, packet=packet, facts=retained.draft.facts,
            snapshot=retained.snapshot,
        )


def test_wrong_effect_ids_are_rejected():
    retained, packet, proposal = inputs(effects=("campaign.record.preserved",))
    with pytest.raises(CampaignSourceProfileError, match="campaign_source_effect_mismatch"):
        validate_campaign_source_proposal(
            proposal, packet=packet, facts=retained.draft.facts,
            snapshot=retained.snapshot,
        )


@pytest.mark.parametrize("insertion", [
    "Mara não avisa sobre a infiltração. ",
    "Mara levou o registro para fora do Arquivo. ",
    "A fundadora é Helena, segundo Mara. ",
])
def test_declared_ids_cannot_override_material_counterexamples(insertion):
    retained, packet, proposal = inputs()
    changed = proposal.model_copy(update={"narrative": insertion + proposal.narrative})
    with pytest.raises(CampaignSourceProfileError):
        validate_campaign_source_proposal(
            changed, packet=packet, facts=retained.draft.facts,
            snapshot=retained.snapshot,
        )
