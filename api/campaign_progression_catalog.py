"""Closed, synthetic content for the opt-in record-rescue campaign.

The catalog describes consequences, not finished dialogue or hidden lore. Its
small recognizer refuses compound and unsupported actions instead of inventing
a mechanical outcome. No user text is interpreted as a rule or state delta.
"""
from __future__ import annotations

import re
import unicodedata
from enum import Enum

from .scene_resolution_service import (
    NpcBeatMove,
    SceneBeatKind,
    SceneConsequenceOption,
    SceneIntentOutcome,
    ScenePressure,
    SceneTurnKind,
)

CAMPAIGN_ID = "record-at-risk"
CONTENT_VERSION = "record-at-risk.v2"
SAFE_SURFACE = "safe_surface"
RECOVERED_CONTENT = "recovered_content"


class CampaignIntentKind(str, Enum):
    TASK = "task"
    HELP_REQUEST = "help_request"
    FOUNDER = "founder"
    WAIT = "wait"
    RESCUE = "rescue"
    INSPECT = "inspect"
    WITHDRAW = "withdraw"


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def classify_campaign_intent(raw_input: str) -> CampaignIntentKind | None:
    """Recognize whole, unambiguous inputs; quoted speech never executes actions."""
    if not isinstance(raw_input, str) or not raw_input.strip() or len(raw_input) > 2000:
        return None
    text = _plain(raw_input.strip())
    if re.fullmatch(r"(?:eu )?(?:aguardo|espero|permaneco em silencio e aguardo)[.!]?", text):
        return CampaignIntentKind.WAIT
    if re.fullmatch(r"(?:eu )?(?:retiro o registro|protejo o registro da agua|levo o registro ate a superficie seca)[.!]?", text):
        return CampaignIntentKind.RESCUE
    if re.fullmatch(r"(?:eu )?(?:examino|investigo|leio) o registro[.!]?", text):
        return CampaignIntentKind.INSPECT
    if re.fullmatch(r"(?:eu )?(?:desisto|abandono o registro|nao vou ajudar)[.!]?", text):
        return CampaignIntentKind.WITHDRAW

    # A spoken command is only a request to Mara, never an executed player action.
    speech = re.fullmatch(r'(?:eu )?(?:pergunto|digo) a mara:\s*["“«](.+)["”»][.!]?', text)
    if speech:
        text = speech.group(1).strip()
        if re.fullmatch(r"leve o registro[?!.]?", text):
            return CampaignIntentKind.HELP_REQUEST
    elif text.startswith(('pergunto ', 'digo ')):
        return None
    text = re.sub(r"^mara,?\s+", "", text)
    if re.fullmatch(r"(?:como posso ajudar|o que precisamos fazer|qual e a tarefa|como salvo o registro)[?!.]?", text):
        return CampaignIntentKind.TASK
    if re.fullmatch(r"leve o registro[?!.]?", text) and raw_input.strip().casefold().startswith("mara"):
        return CampaignIntentKind.HELP_REQUEST
    if re.fullmatch(r"(?:quem e a fundadora|quem foi a fundadora|qual e a identidade da fundadora)[?!.]?", text):
        return CampaignIntentKind.FOUNDER
    return None


def campaign_rule_id(intent: CampaignIntentKind, record: str, success: bool | None) -> str | None:
    if intent in {CampaignIntentKind.TASK, CampaignIntentKind.HELP_REQUEST}:
        return "R-01"
    if intent is CampaignIntentKind.FOUNDER:
        return "R-02"
    if intent is CampaignIntentKind.WAIT:
        return {"threatened": "R-03", "warned": "R-03B", "wet": "R-04"}.get(record)
    if intent is CampaignIntentKind.RESCUE:
        return {"threatened": "R-05", "warned": "R-05", "wet": "R-06"}.get(record)
    if intent is CampaignIntentKind.INSPECT:
        if success is None:
            return None
        return "R-07" if success else "R-08"
    if intent is CampaignIntentKind.WITHDRAW:
        return "R-09"
    return None


def campaign_options(rule_id: str, *, record: str, known_information: tuple[str, ...],
                     intent: CampaignIntentKind) -> tuple[SceneConsequenceOption, ...]:
    """Return the single authored candidate for a state; the resolver still selects it."""
    pressure = {
        "threatened": ScenePressure.CALM,
        "warned": ScenePressure.WATCHFUL,
        "wet": ScenePressure.TENSE,
    }
    if rule_id == "R-01":
        if intent is CampaignIntentKind.HELP_REQUEST:
            return (SceneConsequenceOption(
                option_id="R-01.help_request", priority=20, beat_kind=SceneBeatKind.RESPONSE,
                turn_kinds=(SceneTurnKind.DIALOGUE,), outcomes=(SceneIntentOutcome.UNRESOLVED,),
                required_npc_id="mara", required_capabilities=("protect_archive",),
                effect_keys=("mara.responds.to_rescue_request",),
                guidance_keys=("answer_specific_help_request", "do_not_rescue_without_authored_action"),
                observable_change="Mara responde ao pedido de levar o registro; nenhum resgate é presumido.",
                npc_move=NpcBeatMove(npc_id="mara", action="Mara responde ao pedido concreto de ajuda."),
                pressure_after=pressure[record],
            ),)
        already_known = SAFE_SURFACE in known_information
        return (SceneConsequenceOption(
            option_id="R-01.task_answer", priority=20, beat_kind=SceneBeatKind.RESPONSE,
            turn_kinds=(SceneTurnKind.DIALOGUE,), outcomes=(SceneIntentOutcome.UNRESOLVED,),
            required_npc_id="mara", required_capabilities=("answer_local_history",),
            effect_keys=("mara.replies.to_task",) if already_known else ("mara.replies.to_task", "campaign.knows.safe_surface"),
            guidance_keys=("acknowledge_prior_answer",) if already_known else ("explain_current_risk", "indicate_dry_surface"),
            observable_change="Mara responde sobre o risco atual e a superfície seca.",
            npc_move=NpcBeatMove(npc_id="mara", action="Mara responde à pergunta sobre a tarefa."),
            pressure_after=pressure[record],
        ),)
    if rule_id == "R-02":
        return (SceneConsequenceOption(
            option_id="R-02.protected_answer", priority=20, beat_kind=SceneBeatKind.RESPONSE,
            turn_kinds=(SceneTurnKind.DIALOGUE,), outcomes=(SceneIntentOutcome.UNRESOLVED,),
            required_npc_id="mara", required_capabilities=("answer_local_history",),
            effect_keys=("mara.refuses.founder_identity",),
            guidance_keys=("pertinent_refusal", "redirect_to_record"),
            observable_change="Mara recusa a identidade protegida e responde à intenção.",
            npc_move=NpcBeatMove(npc_id="mara", action="Mara recusa divulgar a identidade."),
            pressure_after=pressure[record],
        ),)
    rows = {
        "R-03": ("campaign.warning.visible", "A infiltração aumenta e Mara indica risco imediato; o registro continua seco.", SceneBeatKind.CHANGE, SceneTurnKind.WAIT, SceneIntentOutcome.UNRESOLVED, ScenePressure.WATCHFUL),
        "R-03B": ("campaign.record.wet", "A água atinge o registro; parte do conteúdo está em risco.", SceneBeatKind.CHANGE, SceneTurnKind.WAIT, SceneIntentOutcome.UNRESOLVED, ScenePressure.TENSE),
        "R-04": ("campaign.record.lost", "A água torna o texto irrecuperável; a aventura termina em perda.", SceneBeatKind.CONSEQUENCE, SceneTurnKind.WAIT, SceneIntentOutcome.UNRESOLVED, ScenePressure.IMMEDIATE),
        "R-05": ("campaign.record.preserved", "O registro é protegido intacto; a aventura se conclui.", SceneBeatKind.CONSEQUENCE, SceneTurnKind.FICTION_ACTION, SceneIntentOutcome.UNRESOLVED, pressure[record]),
        "R-06": ("campaign.record.partial", "O que ainda é legível é salvo; o dano anterior não é revertido.", SceneBeatKind.CONSEQUENCE, SceneTurnKind.FICTION_ACTION, SceneIntentOutcome.UNRESOLVED, ScenePressure.TENSE),
        "R-07": ("campaign.content.recovered", "A investigação recupera informação útil, sem restaurar o registro inteiro.", SceneBeatKind.CONSEQUENCE, SceneTurnKind.FICTION_ACTION, SceneIntentOutcome.SUCCESS, pressure[record]),
        "R-08": ("campaign.inspect.failed", "A investigação não recupera o conteúdo; o registro molha ou, se já molhado, se perde.", SceneBeatKind.COMPLICATION, SceneTurnKind.FICTION_ACTION, SceneIntentOutcome.FAILURE, ScenePressure.TENSE if record != "wet" else ScenePressure.IMMEDIATE),
        "R-09": ("campaign.withdrawn", "O jogador abandona a tentativa; a aventura termina sem deslocamento presumido.", SceneBeatKind.CONSEQUENCE, SceneTurnKind.FICTION_ACTION, SceneIntentOutcome.UNRESOLVED, pressure[record]),
    }
    effect, change, beat_kind, turn_kind, outcome, after_pressure = rows[rule_id]
    return (SceneConsequenceOption(
        option_id=f"{rule_id}.{effect}", priority=20, beat_kind=beat_kind,
        turn_kinds=(turn_kind,), outcomes=(outcome,), effect_keys=(effect,),
        observable_change=change, pressure_after=after_pressure,
    ),)
