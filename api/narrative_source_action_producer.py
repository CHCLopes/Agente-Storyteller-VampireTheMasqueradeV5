"""Bounded local action producer for source-local-ordinary-v1; no general parser.

Recognized whole inputs: waiting; speaking to a seed NPC, with quoted content
after a colon when supplied; investigating the current environment/seed location.
Unknown targets, compound commands and every unmatched input are refused. Speech
inside a matched quote is dialogue, never an engine command. 'Observo' and related
Awareness verbs are deliberately outside this first profile, not no-roll actions.
An ambiguous normalized NPC roster currently refuses the whole profile, including
waiting and investigation, rather than selecting one interpretation of a label.

The internal profile requires a valid, hunger-zero sheet. Investigation uses only
Wits (1..5) + Investigation (0..5), difficulty 3, unopposed, and one real engine call.
Known conditions are checked at player_sheet.status, character.status/fome and
context.current_state/blocking/pending_roll/environmental_flags, plus neutral
deterministic_mechanics. This is not detection of conditions in unknown extensions.

Only the service's direct newly acquired database claim may lead to this call.
Request validation does not authenticate that authorization. No state/cache or
relationship is changed; partial RNG failure never triggers a retry.
"""
from __future__ import annotations

import re
import unicodedata

from . import rules_service as rules
from .narrative_source_input import SourceInputFailure, SourceInputRequest
from .narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation


def _normalized(text: str) -> str:
    # Matching only: the original request text remains the receipt's literal intent.
    return " ".join("".join(char for char in unicodedata.normalize("NFKD", text.casefold())
                            if not unicodedata.combining(char)).split())


def _family(request: SourceInputRequest) -> str:
    text = _normalized(request.player_input)
    names = [_normalized(name) for name in request.snapshot.canonical_scene.npcs_present]
    if len(names) != len(set(names)):
        return "unsupported"
    npc = "(?:" + "|".join(re.escape(name) for name in names) + ")" if names else r"(?!)"
    prefix, stop = r"(?:eu )?", r"[.!?]?"
    wait = (
        r"(?:aguardo|espero)(?: (?:a reacao|a resposta|o proximo movimento)(?: de " + npc + r")?)?",
        r"permaneco(?: no lugar| aqui)?(?: em silencio)?(?: e aguardo)?",
    )
    if any(re.fullmatch(prefix + phrase + r"(?:,? sem tocar em nada)?" + stop, text) for phrase in wait):
        return "declared"
    if re.fullmatch(prefix + r"(?:falo|converso) com " + npc + stop, text):
        return "declared"
    quotation = r'(?:"[^"\x00]+"|«[^»\x00]+»|“[^”\x00]+”)'
    speech = re.fullmatch(prefix + r"(?:digo|pergunto) a " + npc + r":\s*(?P<quote>" + quotation + ")" + stop, text)
    if speech:
        return "declared" if speech.group("quote")[1:-1].strip() else "unsupported"
    location = re.escape(_normalized(request.snapshot.canonical_scene.location))
    target = r"(?:o ambiente|o local|a sala|(?:a |o )?" + location + r")"
    if re.fullmatch(prefix + r"(?:investigo|examino|analiso) " + target + r"(?: sem tocar (?:em nada|nos objetos))?" + stop, text):
        return "investigation"
    if re.fullmatch(prefix + r"(?:falo(?: com)?|converso(?: com)?|digo(?: a)?|pergunto(?: a)?|investigo|examino|analiso)" + stop, text):
        return "clarify"
    return "unsupported"


def _neutral_mechanics(value: object) -> bool:
    if type(value) is not dict:
        return False
    defaults = rules.DeterministicTurnInputs().model_dump(mode="json")
    for name, actual in value.items():
        if name not in defaults or name in {"attribute", "skill"}:
            return False
        expected = defaults[name]
        if name == "action_target" and actual == "UNOPPOSED":
            continue
        if type(actual) is not type(expected) or actual != expected:
            return False
    return True


def _eligible_sheet(state: dict, session_id: str) -> rules.PlayerSheetModel | None:
    raw = state.get("player_sheet")
    if type(raw) is not dict or set(raw) - set(rules.PlayerSheetModel.model_fields):
        return None
    status = raw.get("status")
    if type(status) is not dict or set(status) - set(rules.StatusModel.model_fields):
        return None
    for name in ("health_tracker", "willpower_tracker"):
        tracker = status.get(name)
        if type(tracker) is not dict or set(tracker) != set(rules.TrackerModel.model_fields):
            return None
    try:
        sheet = rules.PlayerSheetModel.model_validate(raw, strict=True)
    except (ValueError, TypeError):
        return None
    if sheet.status.current_hunger != 0:
        return None
    for tracker in (sheet.status.health_tracker, sheet.status.willpower_tracker):
        if (tracker.size <= 0 or tracker.superficial < 0 or tracker.aggravated < 0
                or tracker.superficial + tracker.aggravated >= tracker.size):
            return None
    if (sheet.status.blood_potency < 0 or not 1 <= sheet.status.humanity <= 10
            or sheet.status.stains != 0 or sheet.available_xp < 0 or sheet.spent_xp < 0):
        return None
    if "character" in state:
        character = state["character"]
        if (type(character) is not dict or character.get("status") != "ACTIVE"
                or type(character.get("fome")) is not int or character["fome"] != 0
                or ("id" in character and character["id"] != session_id)):
            return None
        if "trackers" in character:
            trackers = character["trackers"]
            if type(trackers) is not dict:
                return None
            for name, canonical in (("health", sheet.status.health_tracker), ("willpower", sheet.status.willpower_tracker)):
                if name in trackers:
                    expected = {"max": canonical.size, "superficial": canonical.superficial, "aggravated": canonical.aggravated}
                    actual = trackers[name]
                    if type(actual) is not dict or set(actual) != set(expected) or any(type(actual[key]) is not int or actual[key] != item for key, item in expected.items()):
                        return None
            for name, expected in (("humanity", sheet.status.humanity), ("stains", sheet.status.stains)):
                if name in trackers and (type(trackers[name]) is not int or trackers[name] != expected):
                    return None
    context = state.get("context", {})
    if type(context) is not dict:
        return None
    for name, neutral in (("current_state", "ACTIVE"), ("blocking", False), ("pending_roll", None)):
        if name in context and (type(context[name]) is not type(neutral) or context[name] != neutral):
            return None
    if "environmental_flags" in context:
        flags = context["environmental_flags"]
        if (type(flags) is not dict or set(flags) - {"fire_exposure", "blood_stimulus"}
                or any(value is not False for value in flags.values())):
            return None
    for node in (state, context):
        if "deterministic_mechanics" in node and not _neutral_mechanics(node["deterministic_mechanics"]):
            return None
    return sheet


def produce_source_player_action(
    request: SourceInputRequest,
) -> DeclaredActionPreparation | ResolvedActionPreparation | SourceInputFailure:
    """Produce at most one receipt; call only after the service acquires new P."""
    try:
        if type(request) is not SourceInputRequest:
            raise ValueError
        checked = SourceInputRequest.model_validate(request)
    except (ValueError, TypeError, AttributeError, RecursionError, OverflowError):
        return SourceInputFailure(code="source_input_production_failed", stage="preflight")
    family = _family(checked)
    if family in {"unsupported", "clarify"}:
        return SourceInputFailure(code=("source_input_clarification_required" if family == "clarify"
                                        else "source_input_out_of_scope"), stage="classification")
    sheet = _eligible_sheet(checked.state, checked.session_id)
    if sheet is None:
        return SourceInputFailure(code="source_input_out_of_scope", stage="preflight")
    if family == "declared":
        return DeclaredActionPreparation()
    # No fallback values for missing mechanics and no numbers inferred from text.
    wits, investigation = sheet.attributes.get("Wits"), sheet.skills.get("Investigation")
    if (type(wits) is not int or not 1 <= wits <= 5
            or type(investigation) is not int or not 0 <= investigation <= 5):
        return SourceInputFailure(code="source_input_out_of_scope", stage="preflight")
    action = rules.V5ActionPayload(intent=checked.player_input, attribute=rules.V5Attribute.Wits,
        skill=rules.V5Skill.INVESTIGATION, requires_roll=True, is_aggressive=False,
        inferred_difficulty=3, action_target=rules.V5ActionTarget.UNOPPOSED,
        weapon_category=rules.V5WeaponCategory.UNARMED)
    try:
        receipt = rules.calculate_resolution(action, current_hunger=0, dice_pool=wits + investigation)
        if type(receipt) is not rules.ResolutionResult:
            raise ValueError
        return ResolvedActionPreparation(action=action, resolution=receipt)
    except Exception:
        return SourceInputFailure(code="source_input_production_failed", stage="resolution")
