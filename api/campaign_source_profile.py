"""Campaign-only B narrative policy, with deterministic effect obligations.

This checks narrow counterexamples, not full semantic truth. Human assessment
still gates narrator admission. The model never supplies canonical state.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from .campaign_progression_service import CampaignNarratorPacket, CampaignProgressState
from .campaign_source_context import CampaignSourceSnapshot, SOURCE_POLICY
from .narrative_grounding import (
    DerivationDestination, NarrativeVisibility, SourceProjection,
    bind_narrative_derivation, create_narrative_source, materialize_source_projection,
)
from .narrative_source_profile import MAX_CONTEXT_CHARACTERS
from .scene_director_service import expected_narrative_outcome, validate_scene_continuation
from .turn_models import CanonicalFact

PROTOCOL = "campaign-source-proposal-v1"
CONTEXT_PROTOCOL = "campaign-source-application-context-v1"


class CampaignSourceProfileError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CampaignSourceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True,
                              revalidate_instances="always", hide_input_in_errors=True)
    protocol: Literal["campaign-source-proposal-v1"] = PROTOCOL
    narrative: Annotated[StrictStr, Field(min_length=40, max_length=1600)] = Field(alias="n")
    player_prompt: Annotated[StrictStr, Field(max_length=200)] = Field(alias="q")
    realized_effects: tuple[StrictStr, ...]

    @field_validator("narrative", "player_prompt", mode="before")
    @classmethod
    def normalize(cls, value: object) -> object:
        return " ".join(value.split()) if type(value) is str else value

    @model_validator(mode="after")
    def valid(self) -> "CampaignSourceProposal":
        if not self.narrative or len(set(self.realized_effects)) != len(self.realized_effects):
            raise ValueError("campaign proposal invalid")
        return self

    @property
    def player_text(self) -> str:
        return self.narrative + ("\n\n" + self.player_prompt if self.player_prompt else "")


@dataclass(frozen=True)
class _PolicyView:
    narrative: str
    player_prompt: str
    outcome: str
    location: str
    npcs_present: tuple[str, ...]
    scene_summary: Literal[""] = ""
    new_facts: tuple[()] = ()
    open_threads: tuple[()] = ()
    resolved_threads: tuple[()] = ()

    @property
    def player_text(self) -> str:
        return self.narrative + ("\n\n" + self.player_prompt if self.player_prompt else "")


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(char for char in value if not unicodedata.combining(char)).split())


_REQUIRED = {
    "R-01": (("mara",), ("registro", "agua", "infiltr", "ajud", "tarefa")),
    "R-02": (("mara",), ("fundadora",), ("nao", "recus", "segredo")),
    "R-03": (("mara",), ("agua", "infiltr"), ("avisa", "alerta", "risco", "aproxima"), ("seco", "seca", "intacto")),
    "R-03B": (("agua", "infiltr"), ("molh", "ating"), ("registro", "documento")),
    "R-04": (("agua", "infiltr"), ("registro", "texto", "documento"), ("perdid", "irrecuper", "ilegivel")),
    "R-05": (("registro", "documento"), ("salv", "proteg", "preserv"), ("intacto", "seco", "seca")),
    "R-06": (("registro", "documento"), ("parcial", "parte", "trecho"), ("salv", "legivel", "preserv")),
    "R-07": (("registro", "documento", "texto"), ("recuper", "descobr", "legivel"), ("parcial", "parte", "trecho")),
    "R-08": (("registro", "documento", "texto"), ("nao", "falh", "sem"), ("molh", "perdid", "agua", "irrecuper")),
    "R-09": (("mara",), ("desist", "aband", "recus", "nao vai ajud")),
}


def _realizes_rule(text: str, packet: CampaignNarratorPacket) -> bool:
    normalized = _plain(text)
    rule = packet.beat.selected_option_id.split(".", 1)[0]
    groups = _REQUIRED.get(rule)
    if groups is None or any(not any(fragment in normalized for fragment in group) for group in groups):
        return False
    if re.search(r"\bfundadora (?:e|era|se chama|chamava-se) [a-z]", normalized):
        return False
    if rule in {"R-01", "R-02", "R-03"} and re.search(
            r"\bmara (?:nao|nunca) (?:responde|explica|avisa|alerta|recusa)\b", normalized):
        return False
    if rule not in {"R-05", "R-06"} and re.search(
            r"\b(?:voce|o jogador|a jogadora) (?:ja |entao |agora )?"
            r"(?:retira|retirou|leva|levou|salva|salvou|protege|protegeu)\b",
            normalized):
        return False
    if rule in {"R-01", "R-03", "R-03B", "R-04", "R-05", "R-06", "R-07", "R-08"} and re.search(
            r"\bmara (?:levou|retirou|salvou|protegeu|recuperou) (?:o |a )?(?:registro|documento|texto)\b",
            normalized):
        return False
    before, after = packet.state_before, packet.state_after
    if (rule in {"R-05", "R-06"}
            and "superficie seca" in _plain(packet.player_input)
            and "superficie seca" not in normalized):
        # A declared destination is part of the player's authorized method.
        return False
    if rule == "R-01" and "campaign.knows.safe_surface" in packet.required_effects:
        if not any(word in normalized for word in ("seca", "seco", "galeria")):
            return False
    if rule == "R-01" and "mara.responds.to_rescue_request" in packet.required_effects:
        if not any(word in normalized for word in ("levar", "pegar", "ajudar", "consigo", "posso")):
            return False
    if after.record in {"threatened", "warned"}:
        # Explicit affirmative damage is a counterexample; mere mention of risk
        # or a negated verb is not itself a confirmation of damage.
        if re.search(r"\b(?:registro|documento) (?:ja |foi |ficou )?(?:molhado|perdido|destruido)\b", normalized):
            return False
    if after.record == "wet" and re.search(r"\b(?:registro|documento) (?:ainda |segue |permanece |esta )*(?:intacto|seco)\b", normalized):
        return False
    if after.record == "wet" and re.search(
            r"\b(?:registro|documento) (?:voltou a ficar|ficou|permaneceu) (?:intacto|seco)\b",
            normalized):
        return False
    if after.record in {"preserved", "partial"} and re.search(r"\b(?:registro|documento) (?:foi |esta )?(?:perdido|destruido)\b", normalized):
        return False
    if before.record == "wet" and after.record == "partial" and rule == "R-06":
        if not any(word in normalized for word in ("dano", "molh", "perd", "ainda")):
            return False
    if rule == "R-08" and re.search(r"\b(?:recuperou|encontrou|descobriu) (?:o |a )?(?:conteudo|informacao|trecho)\b", normalized):
        return False
    if after.outcome is not None and re.search(
            r"\b(?:precisa|deve|tem que) (?:voltar a )?(?:salvar|resgatar|recuperar) (?:o |a )?(?:registro|documento)\b",
            normalized):
        return False
    return True


def validate_campaign_source_proposal(
    value: CampaignSourceProposal | dict, *, packet: CampaignNarratorPacket,
    facts: tuple[CanonicalFact, ...], snapshot: CampaignSourceSnapshot,
    player_aliases: tuple[str, ...] = (), npc_aliases: tuple[str, ...] = (),
) -> CampaignSourceProposal:
    try:
        proposal = CampaignSourceProposal.model_validate(value)
        checked = CampaignNarratorPacket.model_validate(packet)
        source = CampaignSourceSnapshot.model_validate(snapshot)
        if (tuple(proposal.realized_effects) != checked.required_effects
                or checked.session_id != source.origin.scene_origin.session_id
                or checked.base_revision != source.current_turn
                or checked.state_before != source.progression
                or bool(proposal.player_prompt) == bool(checked.state_after.outcome is not None)):
            raise CampaignSourceProfileError("campaign_source_effect_mismatch")
        view = _PolicyView(
            narrative=proposal.narrative, player_prompt=proposal.player_prompt,
            outcome=expected_narrative_outcome(facts),
            location=source.canonical_scene.location,
            npcs_present=source.canonical_scene.npcs_present,
        )
        validate_scene_continuation(
            view, facts=facts, current_scene=source.canonical_scene,
            player_input=checked.player_input, protected_secrets=(),
            player_aliases=player_aliases,
            npc_aliases=(*source.canonical_scene.npcs_present, *npc_aliases),
            require_player_prompt=checked.state_after.outcome is None,
        )
        if not _realizes_rule(proposal.narrative, checked):
            raise CampaignSourceProfileError("campaign_source_effect_not_realized")
        return proposal
    except CampaignSourceProfileError:
        raise
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        raise CampaignSourceProfileError("campaign_source_proposal_invalid") from None


def create_campaign_source_projection(
    proposal: CampaignSourceProposal, *, packet: CampaignNarratorPacket,
    facts: tuple[CanonicalFact, ...], snapshot: CampaignSourceSnapshot,
    invocation_id: str, source_id: str,
    player_aliases: tuple[str, ...] = (), npc_aliases: tuple[str, ...] = (),
) -> SourceProjection:
    checked = validate_campaign_source_proposal(
        proposal, packet=packet, facts=facts, snapshot=snapshot,
        player_aliases=player_aliases, npc_aliases=npc_aliases,
    )
    source = create_narrative_source(
        source_id=source_id, session_id=packet.session_id,
        turn_id=packet.turn_id, invocation_id=invocation_id,
        text=checked.narrative, source_policy=SOURCE_POLICY,
        visibility=NarrativeVisibility.PLAYER,
    )
    binding = bind_narrative_derivation(
        source, checked.narrative, destination=DerivationDestination.NARRATIVE_SOURCE_VIEW,
    )
    return materialize_source_projection(source, binding, checked.narrative)


def build_campaign_source_context(snapshot: CampaignSourceSnapshot,
                                  packet: CampaignNarratorPacket) -> dict[str, object]:
    checked = CampaignSourceSnapshot.model_validate(snapshot)
    causal = CampaignNarratorPacket.model_validate(packet)
    if (causal.session_id != checked.origin.scene_origin.session_id
            or causal.base_revision != checked.current_turn
            or causal.state_before != checked.progression):
        raise CampaignSourceProfileError("campaign_source_context_mismatch")
    context = {
        "protocol": CONTEXT_PROTOCOL,
        "profile": SOURCE_POLICY,
        "canonical_scene": {"location": checked.canonical_scene.location,
                            "npcs_present": list(checked.canonical_scene.npcs_present)},
        "attributed_sources": [item.model_dump(mode="json") for item in checked.sources],
        "causal_packet": causal.model_dump(mode="json"),
        "semantic_truth_assessed": False,
    }
    if isinstance(causal.state_before, CampaignProgressState):
        context["record_position"] = {
            "before": causal.state_before.record_location,
            "after": causal.state_after.record_location,
            "locations": {"bench": "bancada baixa no Arquivo",
                          "dry_surface": "superfície seca na Galeria"},
            "authority": "deterministic_campaign_state",
        }
    if len(json.dumps(context, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))) > MAX_CONTEXT_CHARACTERS:
        raise CampaignSourceProfileError("campaign_source_context_size_exceeded")
    return context
