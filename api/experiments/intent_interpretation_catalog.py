"""Explicit, reviewable paraphrase catalog for the C offline experiment.

This catalog is deliberately exact. It does not normalize, infer, substring
match, create a new intent, execute a beat, or mutate a session.
"""
from __future__ import annotations

from api.campaign_progression_catalog import CampaignIntentKind

VERSION = "intent-paraphrase-catalog.v1"

APPROVED_PARAPHRASES: dict[str, CampaignIntentKind] = {
    "Quero saber qual é a tarefa.": CampaignIntentKind.TASK,
    "Mara, o que eu posso fazer para ajudar?": CampaignIntentKind.TASK,
    "Fico esperando.": CampaignIntentKind.WAIT,
    "Vou retirar o registro da bancada.": CampaignIntentKind.RESCUE,
    "Analiso o registro.": CampaignIntentKind.INSPECT,
    "Não participarei do resgate.": CampaignIntentKind.WITHDRAW,
}


def approved_intent(player_input: str) -> CampaignIntentKind | None:
    """Return an explicitly reviewed mapping; all other strings are unknown."""
    if type(player_input) is not str:
        return None
    return APPROVED_PARAPHRASES.get(player_input)
