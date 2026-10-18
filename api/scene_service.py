"""Deterministic scene state and player-safe scene queries."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SCENE_SOURCE = _PROJECT_ROOT / "data" / "schema_save.json"


class SceneState(BaseModel):
    """Current scene projection rebuilt from immutable turn events.

    The projection is mutable across turns; its source events are not.  Keeping
    a compact summary and a few open threads gives the scene director enough
    continuity without turning the campaign snapshot into an unbounded prompt.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    location: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=600)
    npcs_present: tuple[str, ...] = Field(default=(), max_length=8)
    details: tuple[str, ...] = Field(default=(), max_length=4)
    open_threads: tuple[str, ...] = Field(default=(), max_length=12)
    last_turn: int = Field(default=0, ge=0)

    @field_validator("location")
    @classmethod
    def _location_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("scene location cannot be blank")
        return normalized

    @field_validator("npcs_present")
    @classmethod
    def _normalize_npcs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_labels(values, max_chars=80)

    @field_validator("summary")
    @classmethod
    def _normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("details", "open_threads")
    @classmethod
    def _normalize_scene_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_labels(values, max_chars=240)


@lru_cache(maxsize=1)
def load_scene_seed() -> SceneState:
    """Load the tracked scene used only by explicit campaign creation."""

    with _DEFAULT_SCENE_SOURCE.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    context = payload.get("context") if isinstance(payload, dict) else None
    if not isinstance(context, dict):
        raise ValueError("data/schema_save.json does not contain a context object")
    return SceneState.model_validate(
        {
            "location": context.get("location"),
            "npcs_present": context.get("npcs_present") or (),
        }
    )


def scene_from_context(context: Mapping[str, Any]) -> SceneState | None:
    """Read a scene projection without filling or normalizing campaign state."""

    raw_scene = context.get("scene")
    if raw_scene is not None:
        return SceneState.model_validate(raw_scene)

    legacy_location = context.get("location")
    if isinstance(legacy_location, str) and legacy_location.strip():
        return SceneState.model_validate(
            {
                "location": legacy_location,
                "npcs_present": context.get("npcs_present") or (),
            }
        )
    return None


def ensure_scene_context(context: Mapping[str, Any]) -> SceneState | None:
    """Compatibility read for existing callers; it deliberately does not mutate."""

    return scene_from_context(context)


def seed_scene_context(context: MutableMapping[str, Any]) -> SceneState:
    """Add the tracked seed during an explicit campaign-creation flow."""

    scene = scene_from_context(context)
    if scene is None:
        scene = load_scene_seed()
        context["scene"] = scene.model_dump(mode="json")
    return scene


def scene_fact_text(scene: SceneState | None) -> str:
    if scene is None:
        return "A localização atual ainda não foi estabelecida."

    parts = [f"Local atual: {scene.location}."]
    if scene.npcs_present:
        parts.append(f"Presenças registradas: {_join_portuguese(scene.npcs_present)}.")
    if scene.summary:
        parts.append(f"Situação atual: {scene.summary}")
    if scene.details:
        parts.append(f"Detalhes estabelecidos: {'; '.join(scene.details)}.")
    if scene.open_threads:
        parts.append(f"Pendências em jogo: {'; '.join(scene.open_threads)}.")
    return " ".join(parts)


def scene_opening_response(scene: SceneState | None) -> str:
    """Present only the seeded place and cast before the player's first action."""

    if scene is None:
        return "A cena ainda não tem um local definido. O que você faz?"
    opening = f"A crônica começa em {scene.location}."
    if scene.npcs_present:
        opening += f" Presenças na cena: {_join_portuguese(scene.npcs_present)}."
    return (
        opening
        + "\n\nVocê pode observar o lugar, iniciar uma conversa ou declarar outra ação. "
        "O que você faz?"
    )


def scene_query_response(scene: SceneState | None) -> str:
    if scene is None:
        return "A localização atual ainda não foi estabelecida."

    if not scene.summary and not scene.details:
        if scene.npcs_present:
            return (
                f"Você está em {scene.location}, com {_join_portuguese(scene.npcs_present)} "
                "presentes; outros detalhes observáveis da cena ainda não foram estabelecidos."
            )
        return (
            f"Você está em {scene.location}; outros detalhes observáveis da cena ainda "
            "não foram estabelecidos."
        )

    parts = [f"Você está em {scene.location}"]
    if scene.npcs_present:
        parts[0] += f", com {_join_portuguese(scene.npcs_present)} presentes"
    parts[0] += "."
    if scene.summary:
        parts.append(scene.summary)
    if scene.details:
        parts.append("Você percebe " + "; ".join(scene.details) + ".")
    if len(parts) == 1:
        parts.append("Outros detalhes observáveis ainda não foram estabelecidos.")
    return " ".join(parts)


def is_scene_query(user_input: str) -> bool:
    normalized = _normalized_text(user_input).rstrip(" ?!.")
    patterns = (
        r"onde (?:eu )?estou",
        r"me mostre (?:o )?(?:lugar|local|ambiente|arredores)",
        r"(?:descreva|mostre) (?:o )?(?:lugar|local|ambiente|arredores)",
        r"o que (?:ha|tem) (?:aqui|ao redor)",
        r"olh(?:o|ar) ao redor",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char))
        .replace("_", " ")
        .split()
    )


def _join_portuguese(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} e {values[1]}"
    return f"{', '.join(values[:-1])} e {values[-1]}"


def _normalize_labels(values: tuple[str, ...], *, max_chars: int) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = " ".join(value.split())
        key = label.casefold()
        if not label or key in seen:
            continue
        if len(label) > max_chars:
            raise ValueError(f"scene item exceeds {max_chars} characters")
        seen.add(key)
        normalized.append(label)
    return tuple(normalized)
