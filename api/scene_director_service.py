"""Typed admission policy for improvisational scene direction.

The model proposes fiction; this module decides what the product can admit.
Past canonical events remain immutable, while the current scene projection may
advance through newly validated facts committed with the same turn.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .scene_service import SceneState
from .scene_resolution_service import (
    SceneBeatResolution,
    SceneResolutionError,
    validate_scene_proposal_against_beat,
)
from .turn_models import CanonicalFact, Visibility


class SceneProposalError(ValueError):
    """A well-formed model proposal that the narrative policy cannot admit."""

    def __init__(
        self,
        code: str,
        *,
        evidence: Mapping[str, object] | None = None,
    ):
        super().__init__(code)
        self.code = code
        # Keep ``str(exc)`` and ``exc.code`` stable for existing callers while
        # exposing machine-readable, non-narrative diagnostics to evaluators.
        # Evidence must never contain generated prose or confidential context.
        self.evidence = dict(evidence or {})


class SceneFactKind(str, Enum):
    OBSERVATION = "observation"
    CLUE = "clue"
    NPC_ACTION = "npc_action"
    COMPLICATION = "complication"
    TRANSITION = "transition"
    HOOK = "hook"


class ProposedSceneFact(BaseModel):
    """One bounded fictional claim proposed for canonical admission."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    kind: SceneFactKind = Field(alias="k")
    summary: str = Field(alias="s", min_length=3, max_length=240)
    # Advertise the same authority enforced locally: SYSTEM is reserved for
    # internal records, never an option in an LLM's proposed fiction schema.
    visibility: Literal[
        Visibility.PUBLIC, Visibility.PLAYER, Visibility.STORYTELLER
    ] = Field(default=Visibility.PLAYER, alias="v")
    importance: float = Field(default=0.5, alias="i", ge=0.0, le=1.0)
    pending: bool = Field(default=False, alias="p")

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())


class SceneContinuationProposal(BaseModel):
    """Provider-neutral result of one improvisational narrator invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    narrative: str = Field(alias="n", min_length=40, max_length=1600)
    outcome: Literal["success", "failure", "unresolved"] = Field(alias="o")
    realized_effects: tuple[str, ...] = Field(default=(), alias="e", max_length=4)
    location: str = Field(alias="l", min_length=1, max_length=160)
    scene_summary: str = Field(alias="s", min_length=8, max_length=600)
    npcs_present: tuple[str, ...] = Field(default=(), alias="p", max_length=8)
    new_facts: tuple[ProposedSceneFact, ...] = Field(
        default=(), alias="f", max_length=4
    )
    open_threads: tuple[str, ...] = Field(default=(), alias="t", max_length=4)
    resolved_threads: tuple[str, ...] = Field(default=(), alias="r", max_length=4)
    player_prompt: str = Field(alias="q", min_length=3, max_length=200)

    @field_validator(
        "narrative", "location", "scene_summary", "player_prompt"
    )
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("realized_effects", "npcs_present", "open_threads", "resolved_threads")
    @classmethod
    def normalize_lists(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = " ".join(raw.split())
            key = value.casefold()
            if not value or key in seen:
                continue
            if len(value) > 240:
                raise ValueError("scene proposal list item is too long")
            seen.add(key)
            normalized.append(value)
        return tuple(normalized)

    @model_validator(mode="after")
    def require_forward_motion(self) -> "SceneContinuationProposal":
        if not self.new_facts and not self.open_threads and not self.resolved_threads:
            raise ValueError(
                "scene continuation must add a fact or change an open thread"
            )
        return self

    @property
    def player_text(self) -> str:
        return f"{self.narrative.rstrip()}\n\n{self.player_prompt.rstrip()}"


_FORBIDDEN_INTERNAL_FRAGMENTS = (
    "fatos canonicos",
    "narrativa autorizada",
    "system log",
    "normal_rolls",
    "hunger_rolls",
    "pool de dados",
    "schema_version",
)

_AGENCY_PATTERNS = (
    r"\bvoce\s+(?:pens\w*|acredit\w*|desej\w*|quer\w*|sente-se|arrepende-se)\b",
    r"\b(?:seu|o|a)\s+personagem\s+"
    r"(?:pens\w*|acredit\w*|desej\w*|quer\w*|sente-se|arrepende-se)\b",
    r"\b(?:voce|(?:(?:seu|o|a)\s+)?personagem)\b[^.!?;:]{0,120}"
    r"\b(?:sem\s+sab\w*|sem\s+memoria|nao\s+sab\w*|ignor\w*|"
    r"nao\s+se\s+lembr\w*)\b",
)


def _mask_quoted_player_preference_questions(value: str) -> str:
    """Ignore a complete NPC question about preference, not an assigned state.

    Only the final, closed question fragment is masked. Earlier assertions in
    the same quotation and unclosed provider text remain visible to every
    agency gate.
    """

    quoted = re.compile(r'(["“«])(?P<body>[^"”»]*)(["”»])')
    preference = re.compile(
        r'(?P<boundary>^|[.!?;:])(?P<question>\s*voce\s+'
        r'(?:quer\w*|desej\w*)\b[^.!?;:]*\?)'
    )

    def mask_quote(match: re.Match[str]) -> str:
        body = match.group("body")

        def mask_question(question: re.Match[str]) -> str:
            return question.group("boundary") + " " * len(question.group("question"))

        masked = preference.sub(mask_question, body)
        return match.group(1) + masked + match.group(3)

    return quoted.sub(mask_quote, value)

_PLAYER_SUBJECT_CLAUSE = re.compile(
    r"\b(?P<subject>voce|seu\s+personagem|o\s+personagem|a\s+personagem|"
    r"personagem)\b"
    r"(?P<clause>[^.!?;:]*)"
)

# Each action has both a broad policy concept and a lexical family. Admission
# compares families, not only concepts: declaring ``abrir`` never authorizes
# the narrator to ``fechar`` or ``acionar`` something on the player's behalf.
# Patterns group regular flexions of the same verb without merging synonyms.
_PLAYER_ACTION_PATTERNS = (
    (
        "move",
        "go",
        r"\b(?:ir|vou|vais|vai|vamos|vao|fui|foi|fomos|foram|indo|iria|iriam)\b",
    ),
    (
        "move",
        "enter",
        r"\bentr(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|aria|ariam)\b",
    ),
    (
        "move",
        "advance",
        r"\bavanc(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "cross",
        r"\batravess(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "cross_cruzar",
        r"\bcruz(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "follow",
        r"\b(?:sigo|segu(?:ir|e|es|imos|em|i|iu|iram|ia|iam|indo|ira|iriam))\b",
    ),
    (
        "move",
        "run",
        r"\bcorr(?:er|o|e|es|emos|em|i|eu|eram|ia|iam|endo|era|eriam)\b",
    ),
    (
        "move",
        "flee",
        r"\bfug(?:ir|o|e|es|imos|em|i|iu|iram|ia|iam|indo|ira|iriam)\b",
    ),
    (
        "move",
        "climb",
        r"\b(?:subir|subo|sobe(?:s)?|subimos|sobem|subi|subiu|subiram|"
        r"subia(?:m)?|subira(?:m)?|subiria(?:m)?|subindo)\b",
    ),
    (
        "move",
        "descend",
        r"\bdesc(?:er|o|e|es|emos|em|i|eu|eram|ia|iam|endo|era|eriam)\b",
    ),
    (
        "move",
        "approach",
        r"\baproxim(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "withdraw",
        r"\bafast(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "return",
        r"\bretorn(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "move",
        "arrive",
        r"\bcheg(?:ar|o|a|as|amos|am|uei|ou|aram|ava|avam|ando|ue|uem|aria|ariam)\b",
    ),
    (
        "move",
        "leave",
        r"\b(?:sair|saio|sai|saimos|saem|saiu|sairam|saia|saiam|"
        r"saindo|sairia|sairiam)\b",
    ),
    (
        "move",
        "depart",
        r"\bpart(?:ir|o|e|es|imos|em|i|iu|iram|ia|iam|indo|ira|iriam)\b",
    ),
    (
        "move",
        "drive",
        r"\bdirig(?:ir|o|e|es|imos|em|i|iu|iram|ia|iam|indo|ira|iriam)\b",
    ),
    (
        "move",
        "shift",
        r"\bdesloc(?:ar|o|a|as|amos|am|uei|ou|aram|ava|avam|ando|aria|ariam)\b",
    ),
    (
        "interact",
        "open",
        r"\babr(?:ir|o|e|es|imos|em|i|iu|iram|ia|iam|indo|ira|iriam|a|am)\b",
    ),
    (
        "interact",
        "close",
        r"\bfech(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "interact",
        "touch",
        r"\btoc(?:ar|o|a|as|amos|am|uei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    (
        "interact", "manipulate",
        r"\bmanipul(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    ("interact", "push", r"\bempurr\w*\b"),
    ("interact", "pull", r"\bpux\w*\b"),
    (
        "interact", "brush",
        # `roça` can name a place after accent normalization, not an action.
        r"\broc(?:ar|o|amos|am|ou|aram|ando)\b",
    ),
    (
        "interact", "force",
        # Avoid the ambiguous noun `força`; these verbal forms cover the
        # explicit attempt construction without matching possessive force.
        r"\bforc(?:ar|o|amos|am|ou|aram|ando)\b",
    ),
    (
        "interact", "move_object",
        r"\bmov(?:er|o|e|es|emos|em|i|eu|eram|ia|iam|endo|era|eriam)\b",
    ),
    (
        "interact", "tear_off",
        r"\barranc(?:ar|o|a|as|amos|am|ou|aram|ava|avam|ando|ara|ariam)\b",
    ),
    ("interact", "break", r"\bquebr\w*\b"),
    ("interact", "light", r"\bacend\w*\b"),
    ("interact", "extinguish", r"\bapag\w*\b"),
    (
        "interact",
        "use",
        r"\bus(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    ("interact", "activate", r"\bacion\w*\b"),
    ("take", "take", r"\bpeg\w*\b"),
    ("take", "keep", r"\bguard\w*\b"),
    ("take", "collect", r"\brecolh\w*\b"),
    ("take", "pick_up", r"\bapanh\w*\b"),
    ("take", "take_control", r"\btom\w*\b"),
    ("take", "deliver", r"\bentreg\w*\b"),
    ("take", "drop", r"\blarg\w*\b"),
    # These families intentionally express only narrow, safe paraphrases.
    # Looking at someone does not authorize searching their body, while a
    # general investigation may naturally be narrated as an examination.
    ("inspect", "inspect_general", r"\binvestig\w*\b"),
    ("inspect", "inspect_general", r"\bexamin\w*\b"),
    ("inspect", "inspect_general", r"\banalis\w*\b"),
    (
        "inspect", "verify",
        r"\bverifi(?:c(?:ar|o|a|as|amos|am|ou|aram|ava|avam|ando|ara|arao|aria|ariam)|"
        r"qu(?:ei|e|em))\b",
    ),
    (
        "inspect", "explore",
        r"\bexplor(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|aria|ariam)\b",
    ),
    ("inspect", "search_thoroughly", r"\bvasculh\w*\b"),
    ("inspect", "search_general", r"\bprocur\w*\b"),
    ("inspect", "search_general", r"\bbusc\w*\b"),
    ("inspect", "observe", r"\bobserv\w*\b"),
    ("inspect", "frisk", r"\brevist\w*\b"),
    ("combat", "attack", r"\batac\w*\b"),
    ("combat", "strike", r"\bgolpe\w*\b"),
    ("combat", "shoot", r"\bdispar\w*\b"),
    ("combat", "bite", r"\bmord\w*\b"),
    ("combat", "grab", r"\bagarr\w*\b"),
    ("combat", "threaten", r"\bameac\w*\b"),
    (
        "combat",
        "wound",
        r"\bfer(?:ir|e|em|iu|iram|ia|iam|indo|ido|ida|idos|idas|"
        r"ira|iriam|isse|issem)\b",
    ),
    ("combat", "kill", r"\bmat\w*\b"),
    (
        "social",
        "speak",
        r"\bfal(?:ar\w*|o|a|as|amos|am|ei|ou|ava|avam|ando|e|em|asse|assem)\b",
    ),
    ("social", "say", r"\bdiz\w*\b"),
    ("social", "ask", r"\bpergunt\w*\b"),
    ("social", "answer", r"\brespond\w*\b"),
    ("social", "converse", r"\bconvers\w*\b"),
    ("social", "promise", r"\bpromet\w*\b"),
    ("social", "confess", r"\bconfess\w*\b"),
    ("social", "convince", r"\bconvenc\w*\b"),
    ("social", "persuade", r"\bpersuad\w*\b"),
    (
        "social", "address",
        r"\babord(?:ar|o|a|as|amos|am|ei|ou|aram|ava|avam|ando|e|em|ara|arao|aria|ariam)\b",
    ),
    ("choice", "decide", r"\bdecid\w*\b"),
    ("choice", "choose", r"\bescolh\w*\b"),
    ("choice", "accept", r"\baceit\w*\b"),
    ("choice", "refuse", r"\brecus\w*\b"),
    ("choice", "resolve", r"\bresolv\w*\b"),
    ("conceal", "hide", r"\bescond\w*\b"),
    ("conceal", "conceal", r"\bocult\w*\b"),
    ("conceal", "disguise", r"\bdisfarc\w*\b"),
    ("conceal", "lie", r"\bment\w*\b"),
    ("consume", "drink", r"\bbeb\w*\b"),
    ("consume", "feed", r"\baliment\w*\b"),
    ("consume", "devour", r"\bdevor\w*\b"),
    ("consume", "consume", r"\bconsum\w*\b"),
    ("wait", "wait", r"\besper\w*\b"),
    ("wait", "await", r"\baguard\w*\b"),
    ("wait", "remain", r"\bpermanec\w*\b"),
    ("wake", "wake", r"\bacord\w*\b"),
    ("wake", "awaken", r"\bdespert\w*\b"),
)

_PERCEPTION_VERB = re.compile(
    r"\b(?:sent\w*|sinto|sinta|sintam|ouv\w*|escut\w*|vejo|ve|vemos|veem|viu|viram|"
    r"perceb\w*|not\w*|observ\w*)\b"
)

_PLAYER_CONTROL_CUE = re.compile(
    r"\b(?:para|antes|depois|decid\w*|tent\w*|resolv\w*|"
    r"pretend\w*|quer\w*|vontade|precis\w*|dev\w*|tem\s+que)\b"
)

_PORTUGUESE_LANGUAGE_MARKERS = frozenset(
    {
        "ao",
        "aos",
        "ate",
        "ainda",
        "antes",
        "aqui",
        "ali",
        "com",
        "como",
        "da",
        "das",
        "de",
        "depois",
        "do",
        "dos",
        "e",
        "ela",
        "ele",
        "elas",
        "eles",
        "em",
        "enquanto",
        "entre",
        "esse",
        "essa",
        "este",
        "esta",
        "ha",
        "isso",
        "isto",
        "mas",
        "na",
        "nas",
        "nao",
        "no",
        "nos",
        "o",
        "onde",
        "os",
        "ou",
        "para",
        "pela",
        "pelas",
        "pelo",
        "pelos",
        "por",
        "qual",
        "quando",
        "que",
        "quem",
        "sem",
        "se",
        "seu",
        "seus",
        "sim",
        "sob",
        "sobre",
        "sua",
        "suas",
        "um",
        "uma",
        "uns",
        "umas",
        "voce",
    }
)

# Content evidence supplements function words for short generated fields.  It
# is deliberately small and generic; the gate still defaults to rejecting
# non-name fragments for which it cannot find any Portuguese evidence.
_PORTUGUESE_CONTENT_MARKERS = frozenset(
    {
        "aproxima",
        "aproximam",
        "aparece",
        "ar",
        "bar",
        "beco",
        "cais",
        "chia",
        "entender",
        "entra",
        "encontrada",
        "encontrado",
        "fechado",
        "fechada",
        "galpao",
        "identificar",
        "industrial",
        "interrompida",
        "interrompidas",
        "marcas",
        "municipal",
        "nova",
        "novo",
        "passos",
        "perigo",
        "perto",
        "pista",
        "principe",
        "rua",
        "silhueta",
        "sombra",
        "telhado",
        "xerife",
    }
)

_ENGLISH_LANGUAGE_MARKERS = frozenset(
    {
        "after",
        "and",
        "are",
        "as",
        "at",
        "before",
        "but",
        "can",
        "could",
        "did",
        "do",
        "does",
        "from",
        "he",
        "her",
        "here",
        "his",
        "how",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "over",
        "she",
        "should",
        "still",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "under",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "without",
        "would",
        "you",
        "your",
    }
)

_ENGLISH_CONTENT_MARKERS = frozenset(
    {
        "alley",
        "appear",
        "appears",
        "blood",
        "clue",
        "corridor",
        "crackle",
        "crackles",
        "danger",
        "door",
        "enter",
        "enters",
        "fall",
        "falls",
        "footstep",
        "footsteps",
        "found",
        "guard",
        "night",
        "nearby",
        "new",
        "radio",
        "room",
        "shadow",
        "shadows",
        "signal",
        "silent",
        "siren",
        "street",
        "unknown",
        "watch",
        "watches",
        "warehouse",
    }
)

_SPANISH_LANGUAGE_MARKERS = frozenset(
    {
        "al",
        "aunque",
        "con",
        "desde",
        "donde",
        "el",
        "ella",
        "ellos",
        "hay",
        "hacia",
        "la",
        "las",
        "los",
        "luego",
        "mientras",
        "muy",
        "pero",
        "sin",
        "una",
        "unas",
        "uno",
        "unos",
        "usted",
        "ustedes",
        "y",
    }
)

_FRENCH_LANGUAGE_MARKERS = frozenset(
    {
        "avec",
        "avant",
        "comment",
        "dans",
        "des",
        "du",
        "elle",
        "est",
        "et",
        "ils",
        "la",
        "le",
        "les",
        "mais",
        "pour",
        "sans",
        "sont",
        "sur",
        "une",
        "vous",
        "votre",
    }
)

_PLAYER_PROMPT_POSSESSIVE_ACTION = (
    r"\b(?:sua|seu)\s+(?:proxima|proximo)?\s*"
    r"(?:acao|atitude|escolha|decisao|passo|movimento|tentativa)\b"
)

_PLAYER_PROMPT_ACTION_CUE = re.compile(
    r"\b(?:o\s+que\s+(?:voce\s+)?(?:faz|fara|observa|procura|tenta|"
    r"pretende)|"
    r"que\s+fazer|como\s+(?:voce\s+)?(?:age|agira|reage|reagira|"
    r"responde|respondera|procede|procedera|pretende|vai|lida|lidara)|"
    r"qual\s+(?:e|sera)\s+" + _PLAYER_PROMPT_POSSESSIVE_ACTION + r"|"
    r"(?:que|qual)\s+[^?]{0,50}\b(?:escolhe|escolhera|prefere|"
    r"decide|decidira|seguira))\b"
)

_PLAYER_PROMPT_WORLD_FACT = re.compile(
    r"\b(?:o\s+que\s+(?!voce\b)[^?]{0,80}\b(?:revel\w*|mostr\w*|"
    r"signific\w*|indic\w*|contem|caus\w*)|"
    r"qual\s+(?:e|sera)\s+(?:a|o)\s+(?:fonte|origem|verdade|resposta))\b"
)

_PLAYER_PROMPT_NAMED_ACTOR = re.compile(
    r"\b(?:faz|fará|age|agirá|reage|reagirá|responde|responderá|"
    r"procede|procederá|pretende|decide|decidirá|verifica|verificará|aborda|abordará)\s+"
    r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'-]*\b|"
    r"^(?:O\s+que|Como)\s+"
    r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'-]*\s+"
    r"(?:faz|fará|age|agirá|reage|reagirá|responde|responderá|"
    r"procede|procederá|pretende|decide|decidirá|verifica|verificará|aborda|abordará)\b|"
    r"^\s*(?:Que|Qual)\s+\S+\s+"
    r"[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][\wÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç'-]*\s+"
    r"(?:escolhe|escolherá|prefere|decide|decidirá)\b"
)

_PLAYER_PROMPT_COMMON_ACTOR = re.compile(
    r"^(?:O\s+que|Como)\s+(?:a|o|um|uma)\s+\w+"
    r"(?:\s+(?:da|do|de|das|dos)\s+\w+){0,2}\s+"
    r"(?:faz|fará|age|agirá|reage|reagirá|responde|responderá|"
    r"procede|procederá|pretende|decide|decidirá|verifica|verificará|aborda|abordará)\b|"
    r"\b(?:faz|fará|age|agirá|reage|reagirá|responde|responderá|"
    r"procede|procederá|pretende|decide|decidirá|verifica|verificará|aborda|abordará)\s+"
    r"(?:a(?!\s+seguir\b)|o|um|uma)\s+\w+"
    r"(?:\s+(?:da|do|de|das|dos)\s+\w+){0,2}\b|"
    r"^(?:Que|Qual)\s+\S+(?:\s+\S+){0,2}\s+"
    r"(?:a|o|um|uma)\s+\w+"
    r"(?:\s+(?:da|do|de|das|dos)\s+\w+){0,2}\s+"
    r"(?:escolhe|escolherá|prefere|decide|decidirá)\b"
)

_POLICY_STOPWORDS = frozenset(
    {
        "a",
        "ao",
        "aos",
        "as",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "ela",
        "ele",
        "em",
        "entre",
        "essa",
        "esse",
        "esta",
        "este",
        "foi",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "para",
        "pela",
        "pelo",
        "por",
        "que",
        "se",
        "sem",
        "seu",
        "sua",
        "um",
        "uma",
    }
)

_ACTION_TARGET_STOPWORDS = _POLICY_STOPWORDS | frozenset(
    {
        "agora",
        "cuidadosamente",
        "devagar",
        "imediatamente",
        "la",
        "lhe",
        "lentamente",
        "lo",
        "novamente",
        "personagem",
        "rapidamente",
        "voce",
    }
)

_ACTION_TARGET_BOUNDARY = re.compile(
    r"[,;:.!?]|\b(?:antes|depois|durante|e|enquanto|entao|mas|para|"
    r"porem|quando|sob)\b"
)

_TARGET_SENSITIVE_ACTION_CONCEPTS = frozenset(
    {"combat", "conceal", "consume", "interact", "move", "social", "take"}
)

# This small domain lexicon catches high-risk paraphrases without pretending to
# be a general semantic classifier. Token overlap remains the generic control
# for names, places and campaign-specific terms.
_SECRET_PARAPHRASE_CONCEPTS = (
    ("ambush", r"\b(?:emboscad\w*|armadilh\w*|cilad\w*|cerc\w*)\b"),
    (
        "authority",
        r"\b(?:xerife|sheriff|autoridad\w*|chefe\s+da\s+guarda|guarda)\b",
    ),
    ("planning", r"\b(?:arm\w*|prepar\w*|planej\w*|orden\w*|organiz\w*)\b"),
    ("port", r"\b(?:cais|porto|doca\w*|armazem\w*)\b"),
    ("betrayal", r"\b(?:trai\w*|traic\w*|traidor\w*)\b"),
    ("hidden", r"\b(?:secret\w*|ocult\w*|reservad\w*|escondid\w*)\b"),
    ("evidence", r"\b(?:prova\w*|evidencia\w*|pista\w*|registro\w*)\b"),
)

_FAILURE_MARKER = re.compile(
    r"\b(?:falh\w*|(?:nao|nada)\s+(?:se\s+)?(?:consegu\w*|cede(?:m|u|ram)?|abr(?:e|em|iu|iram))|"
    r"nada\s+conclusivo|complica\w*|"
    r"custo|pressao|imped\w*|bloque\w*|atras\w*|perd\w*|escap\w*|"
    r"resist\w*|incomplet\w*|parcial\w*|risco|ameac\w*)\b|"
    r"\binvestigacao\s+nao\s+recupera\s+conteudo\s+algum\b|"
    r"(?:^|[.])\s*(?:ao examinar o registro na bancada baixa do arquivo,\s*)?"
    r"voce\s+nao\s+recupera\s+(?:nenhum|seu)\s+conteudo\b|"
    r"(?:^|[.])\s*sua tentativa de examinar o registro nao recupera conteudo algum\b|"
    r"(?:^|[.,])\s*(?:mas )?a tentativa nao recupera conteudo\b"
)

_FAILURE_GOAL_GRANT = re.compile(
    r"\b(?:sucesso|bem[- ]sucedid\w*|consegu\w*|alcanc\w*|ating\w*|"
    r"obt\w*|encontr\w*|descobr\w*|ced\w*|abr\w*|revel\w*|"
    r"solucion\w*|resolv\w*|confirm\w*|identific\w*|localiz\w*)\b|"
    r"\b(?:prova|evidencia|pista|resposta|registro)\s+"
    r"(?:definitiv\w*|conclusiv\w*|complet\w*)\b|"
    r"\b(?:objetivo|missao|tarefa)\s+(?:cumprid\w*|concluid\w*)\b|"
    r"\brecuper(?:a|ou)\s+(?:informacao\s+util|informacoes\s+uteis|parte\s+da\s+informacao)\b|"
    r"(?:^|(?<=[.]))\s*o registro permanece na bancada, agora parcial, "
    r"com parte de seu conteudo recuperada\s*(?=[.!;]|$)"
)

_NEGATED_GOAL_PREFIX = re.compile(
    r"\b(?:falh\w*\s+(?:em|ao\s+tent\w*|a)?|"
    r"nao\s+(?:se\s+)?consegu\w*|sem\s+(?:se\s+)?consegu\w*|"
    r"nao\s+foi\s+possivel)\s*$"
)

_IMMEDIATE_NEGATION_PREFIX = re.compile(r"\b(?:nao(?:\s+se)?|sem)\s*$")
_LOCAL_NOTHING_SUBJECT_PREFIX = re.compile(r"(?:^|,)\s*nada(?:\s+se)?\s*$")

_PASSIVE_NEGATED_GOAL_PREFIX = re.compile(
    r"\b(?:nao|nada|nunca|jamais|nenhum\w*)\b"
    r"(?:\s+[a-z0-9]+){0,3}\s+(?:foi|foram|esta|estao|ficou|ficaram)\s*$"
)

_FAILURE_POSSESSION_GRANT = re.compile(
    r"\b(?:receb\w*|possu\w*|segur\w*|carreg\w*|apanh\w*|recolh\w*)\b|"
    r"\b(?:repous\w*|fic\w*|est\w*)\b[^.!?;:]{0,100}"
    r"\b(?:na\s+palma|nas?\s+maos?|em\s+(?:sua\s+)?posse|"
    r"com\s+voce|ao\s+seu\s+alcance)\b"
)

_THREAD_RESOLUTION_MARKER = re.compile(
    r"\b(?:descobr\w*|identific\w*|revel\w*|solucion\w*|resolv\w*|"
    r"confirm\w*|encerr\w*|desvend\w*|esclarec\w*)\b|"
    r"\b(?:fica|torna-se)\s+clar\w*\b"
)

_THREAD_UNRESOLVED_MARKER = re.compile(
    r"\b(?:desconhecid\w*|incert\w*|sem\s+resposta|nao\s+se\s+sabe|"
    r"ainda\s+nao|continua\s+(?:sem|ocult\w*|desconhecid\w*)|"
    r"permanece\s+(?:sem|ocult\w*|desconhecid\w*|incert\w*))\b"
)


def expected_narrative_outcome(facts: Iterable[CanonicalFact | Mapping]) -> str:
    for fact in facts:
        fact_type = (
            fact.get("fact_type")
            if isinstance(fact, Mapping)
            else fact.fact_type
        )
        if fact_type != "mechanics.resolution":
            continue
        value = fact.get("value") if isinstance(fact, Mapping) else fact.value
        if isinstance(value, Mapping) and isinstance(value.get("is_success"), bool):
            return "success" if value["is_success"] else "failure"
    return "unresolved"


def validate_scene_continuation(
    proposal: SceneContinuationProposal,
    *,
    facts: Iterable[CanonicalFact | Mapping],
    current_scene: SceneState | None,
    player_input: str = "",
    protected_secrets: Iterable[str] = (),
    player_aliases: Iterable[str] = (),
    npc_aliases: Iterable[str] = (),
    scene_beat: SceneBeatResolution | None = None,
    require_player_prompt: bool = True,
) -> SceneContinuationProposal:
    """Admit bounded fictional novelty without surrendering game authority."""

    fact_records = tuple(facts)
    player_alias_records = tuple(player_aliases)
    npc_alias_records = tuple(npc_aliases)
    expected_outcome = expected_narrative_outcome(fact_records)
    if proposal.outcome != expected_outcome:
        raise SceneProposalError("scene_outcome_mismatch")

    _validate_portuguese_scene_fields(proposal, current_scene=current_scene)
    if require_player_prompt:
        _validate_player_prompt(
            proposal.player_prompt,
            player_aliases=player_alias_records,
            npc_aliases=(*npc_alias_records, *proposal.npcs_present),
        )
    elif proposal.player_prompt != "":
        raise SceneProposalError("scene_terminal_prompt_forbidden")

    player_text = proposal.player_text
    visible_fields = _player_visible_scene_fields(proposal)
    normalized_visible = _normalize_for_policy("\n".join(visible_fields))
    if any(
        fragment in normalized_visible for fragment in _FORBIDDEN_INTERNAL_FRAGMENTS
    ):
        raise SceneProposalError("scene_internal_content")

    words = re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", player_text, flags=re.UNICODE)
    if len(words) < 30:
        raise SceneProposalError("scene_narrative_too_short")
    if len(words) > 150:
        raise SceneProposalError("scene_narrative_too_long")

    for field_name, field_value in (
        ("narrative", proposal.narrative),
        ("scene_summary", proposal.scene_summary),
        *(
            (f"open_threads[{index}]", value)
            for index, value in enumerate(proposal.open_threads)
        ),
        *(
            (f"resolved_threads[{index}]", value)
            for index, value in enumerate(proposal.resolved_threads)
        ),
        *(
            (f"new_facts[{index}].summary", fact.summary)
            for index, fact in enumerate(proposal.new_facts)
            if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        ),
    ):
        field_normalized = _mask_quoted_player_preference_questions(
            _normalize_for_policy(field_value)
        )
        for pattern in _AGENCY_PATTERNS:
            if re.search(pattern, field_normalized):
                raise SceneProposalError(
                    "scene_player_agency_violation",
                    evidence={
                        "field": field_name,
                        "rule": "assigned_internal_state",
                    },
                )

    _validate_secret_separation(
        proposal,
        visible_fields,
        protected_secrets=protected_secrets,
    )

    previous_threads = {
        scene_thread_key(value): value
        for value in (current_scene.open_threads if current_scene is not None else ())
    }
    resolved_keys = {scene_thread_key(value) for value in proposal.resolved_threads}
    open_keys = {scene_thread_key(value) for value in proposal.open_threads}
    if resolved_keys - previous_threads.keys():
        raise SceneProposalError("scene_unknown_thread_resolution")
    if resolved_keys & open_keys:
        raise SceneProposalError("scene_thread_reopened_while_resolved")
    resolution_evidence = "\n".join(
        (
            proposal.narrative,
            proposal.scene_summary,
            *(fact.summary for fact in proposal.new_facts),
        )
    )
    for thread in proposal.resolved_threads:
        if not _thread_resolution_is_grounded(thread, resolution_evidence):
            raise SceneProposalError("scene_thread_resolution_without_evidence")

    location_changed = (
        current_scene is not None
        and proposal.location.casefold() != current_scene.location.casefold()
    )
    input_action_authorizations = _action_authorizations(player_input)
    input_action_concepts = frozenset(
        concept for concept, _ in input_action_authorizations
    )
    _validate_declared_player_actions(
        proposal,
        authorized_actions=input_action_authorizations,
        player_aliases=player_alias_records,
        npc_aliases=npc_alias_records,
    )
    _validate_implicit_player_contact(
        proposal, authorized_actions=input_action_authorizations,
        player_input=player_input, player_aliases=player_alias_records,
    )
    if current_scene is None:
        _validate_implicit_opening_history(
            proposal.scene_summary, player_input,
            npc_aliases=(*npc_alias_records, *proposal.npcs_present),
        )

    transition = any(
        fact.kind is SceneFactKind.TRANSITION for fact in proposal.new_facts
    )
    if (
        location_changed
        and not transition
    ):
        raise SceneProposalError("scene_location_changed_without_transition")
    if location_changed and "move" not in input_action_concepts:
        raise SceneProposalError("scene_player_movement_not_authorized")

    previous_roster = {
        value.casefold()
        for value in (current_scene.npcs_present if current_scene is not None else ())
    }
    proposed_roster = {value.casefold() for value in proposal.npcs_present}
    npc_roster_changed = current_scene is not None and proposed_roster != previous_roster
    npc_change_is_explicit = any(
        fact.kind in {SceneFactKind.NPC_ACTION, SceneFactKind.TRANSITION}
        for fact in proposal.new_facts
    )
    if npc_roster_changed and not npc_change_is_explicit:
        raise SceneProposalError(
            "scene_npc_roster_changed_without_event",
            evidence={
                "previous_count": len(previous_roster),
                "proposed_count": len(proposed_roster),
                "added_count": len(proposed_roster - previous_roster),
                "removed_count": len(previous_roster - proposed_roster),
                "fact_kind_counts": {
                    kind.value: sum(fact.kind is kind for fact in proposal.new_facts)
                    for kind in SceneFactKind
                },
                "has_change_fact": npc_change_is_explicit,
            },
        )

    summaries: set[str] = set()
    for fact in proposal.new_facts:
        key = fact.summary.casefold()
        if key in summaries:
            raise SceneProposalError("scene_duplicate_fact")
        summaries.add(key)
    validate_mechanical_narrative(
        proposal.narrative, outcome=expected_outcome, proposal=proposal,
        player_input=player_input, current_scene=current_scene,
    )

    if scene_beat is not None:
        try:
            validate_scene_proposal_against_beat(proposal, scene_beat)
        except SceneResolutionError as exc:
            raise SceneProposalError(exc.code, evidence=exc.evidence) from None

    return proposal


def project_scene(
    proposal: SceneContinuationProposal,
    *,
    previous: SceneState | None,
    turn_number: int,
) -> SceneState:
    """Create the next compact scene projection from an admitted proposal."""

    visible_details = tuple(
        fact.summary
        for fact in proposal.new_facts
        if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        and fact.kind
        in {
            SceneFactKind.OBSERVATION,
            SceneFactKind.CLUE,
            SceneFactKind.NPC_ACTION,
            SceneFactKind.COMPLICATION,
            SceneFactKind.TRANSITION,
        }
    )
    details = _merge_recent(
        previous.details if previous is not None else (),
        visible_details,
        limit=4,
    )
    resolved = {scene_thread_key(value) for value in proposal.resolved_threads}
    retained_threads = tuple(
        value
        for value in (previous.open_threads if previous is not None else ())
        if scene_thread_key(value) not in resolved
    )
    threads = merge_scene_threads(retained_threads, proposal.open_threads)
    if len(threads) > 12:
        raise SceneProposalError("scene_open_thread_capacity_exceeded")
    return SceneState(
        location=proposal.location,
        summary=proposal.scene_summary,
        npcs_present=proposal.npcs_present,
        details=details,
        open_threads=threads,
        last_turn=turn_number,
    )


def _merge_recent(
    existing: tuple[str, ...], incoming: tuple[str, ...], *, limit: int
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in (*existing, *incoming):
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(value)
    return tuple(merged[-limit:])


def scene_thread_key(value: str) -> str:
    """Compare labels, not meanings; retain words and internal punctuation.

    A narrator may add a sentence terminator to a canonical label. This does
    not open a different thread. Do not apply the broader policy normalizer:
    accent, number, negation and internal punctuation differences can identify
    distinct objectives. The returned key never replaces stored source text.
    """

    normalized = " ".join(value.casefold().split())
    return normalized.rstrip(" .!?…") or normalized


def merge_scene_threads(
    existing: tuple[str, ...], incoming: tuple[str, ...]
) -> tuple[str, ...]:
    """Keep the first canonical label when only terminal punctuation varies."""

    merged: list[str] = []
    seen: set[str] = set()
    for value in (*existing, *incoming):
        key = scene_thread_key(value)
        if key in seen:
            continue
        seen.add(key)
        merged.append(value)
    return tuple(merged)


def _normalize_for_policy(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char))
        .split()
    )


def _generated_scene_text_fields(
    proposal: SceneContinuationProposal,
) -> tuple[tuple[str, str], ...]:
    """Return every piece of prose generated by the H6 wire contract."""

    return (
        ("narrative", proposal.narrative),
        ("location", proposal.location),
        ("scene_summary", proposal.scene_summary),
        *(
            (f"npcs_present[{index}]", value)
            for index, value in enumerate(proposal.npcs_present)
        ),
        *(
            (f"new_facts[{index}].summary", fact.summary)
            for index, fact in enumerate(proposal.new_facts)
        ),
        *(
            (f"open_threads[{index}]", value)
            for index, value in enumerate(proposal.open_threads)
        ),
        *(
            (f"resolved_threads[{index}]", value)
            for index, value in enumerate(proposal.resolved_threads)
        ),
        ("player_prompt", proposal.player_prompt),
    )


def _language_marker_counts(value: str) -> dict[str, int]:
    normalized = _normalize_for_policy(value)
    tokens = re.findall(r"[a-z]+", normalized)
    portuguese = sum(token in _PORTUGUESE_LANGUAGE_MARKERS for token in tokens)
    portuguese += sum(token in _PORTUGUESE_CONTENT_MARKERS for token in tokens)
    english = sum(token in _ENGLISH_LANGUAGE_MARKERS for token in tokens)
    english += sum(token in _ENGLISH_CONTENT_MARKERS for token in tokens)
    english += sum(
        token in _ENGLISH_CONTENT_MARKERS
        and (token.endswith("s") or token in {"found"})
        for token in tokens
    )
    spanish = sum(token in _SPANISH_LANGUAGE_MARKERS for token in tokens)
    french = sum(token in _FRENCH_LANGUAGE_MARKERS for token in tokens)

    # These suffixes only add corroborating evidence. A single loanword such as
    # "marketing" cannot make otherwise Portuguese prose fail the gate.
    english += sum(
        token.endswith(("ing", "ed", "ly")) and len(token) >= 5
        for token in tokens
    )
    portuguese += min(2, len(re.findall(r"[ãõçáéíóúâêôà]", value.casefold())))
    portuguese += min(
        2,
        sum("lh" in token or "nh" in token for token in tokens),
    )
    spanish += min(2, value.casefold().count("ñ"))

    return {
        "portuguese": portuguese,
        "english": english,
        "spanish": spanish,
        "french": french,
    }


def _clearly_foreign_language(value: str) -> tuple[str, dict[str, int]] | None:
    counts = _language_marker_counts(value)
    detected_language, foreign_count = max(
        (
            (language, count)
            for language, count in counts.items()
            if language != "portuguese"
        ),
        key=lambda item: item[1],
    )
    portuguese_count = counts["portuguese"]
    if foreign_count < 2 or foreign_count <= portuguese_count:
        return None
    return detected_language, counts


def _validate_portuguese_scene_fields(
    proposal: SceneContinuationProposal,
    *,
    current_scene: SceneState | None,
) -> None:
    """Reject foreign H6 prose without penalizing inconclusive short PT-BR."""

    generated_fields = _generated_scene_text_fields(proposal)
    aggregate_counts = _language_marker_counts(
        "\n".join(
            value
            for field_name, value in generated_fields
            if not field_name.startswith("npcs_present[")
        )
    )
    aggregate_portuguese = aggregate_counts["portuguese"] >= 2 and (
        aggregate_counts["portuguese"]
        >= max(
            aggregate_counts["english"],
            aggregate_counts["spanish"],
            aggregate_counts["french"],
        )
    )

    for field_name, value in generated_fields:
        if (
            field_name == "location"
            and current_scene is not None
            and _normalize_for_policy(value)
            == _normalize_for_policy(current_scene.location)
        ):
            continue
        counts = _language_marker_counts(value)
        detected = _clearly_foreign_language(value)
        if detected is not None:
            detected_language = detected[0]
        elif _is_name_field(field_name) and _is_name_like(value):
            continue
        elif counts["portuguese"] > 0 or aggregate_portuguese:
            continue
        else:
            detected_language = "undetermined"
        raise SceneProposalError(
            "scene_output_not_portuguese",
            evidence={
                "field": field_name,
                "rule": "portuguese_required",
                "detected_language": detected_language,
                "portuguese_marker_count": counts["portuguese"],
                "english_marker_count": counts["english"],
            },
        )


def _is_name_field(field_name: str) -> bool:
    return field_name == "location" or field_name.startswith("npcs_present[")


def _is_name_like(value: str) -> bool:
    """Recognize compact proper names only where the schema expects a name."""

    words = re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", value, flags=re.UNICODE)
    if not 1 <= len(words) <= 5:
        return False
    connectors = {"da", "das", "de", "do", "dos", "e", "of", "the"}
    return words[0][0].isupper() and all(
        word.casefold() in connectors or word[0].isupper()
        for word in words[1:]
    )


def _validate_player_prompt(
    value: str,
    *,
    player_aliases: Iterable[str] = (),
    npc_aliases: Iterable[str] = (),
) -> None:
    player_alias_records = tuple(player_aliases)
    words = re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", value, flags=re.UNICODE)
    if len(words) > 15:
        raise SceneProposalError(
            "scene_player_prompt_too_long",
            evidence={
                "field": "player_prompt",
                "rule": "open_player_action_question",
                "reason": "word_limit_exceeded",
                "word_count": len(words),
            },
        )
    if not value.rstrip().endswith("?"):
        raise SceneProposalError(
            "scene_player_prompt_not_open",
            evidence={
                "field": "player_prompt",
                "rule": "open_player_action_question",
                "reason": "missing_question_mark",
                "word_count": len(words),
            },
        )

    # A quoted inscription can contain '?'; only separate unquoted questions
    # can append an NPC/world question after an otherwise valid invitation.
    literal_quotes = re.compile(
        r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|«[^»\n]*»|'
        r"(?<!\w)'[^'\n]*'(?!\w)"
    )
    if literal_quotes.sub("", value).count("?") > 1:
        raise SceneProposalError(
            "scene_player_prompt_not_actionable",
            evidence={"field": "player_prompt", "rule": "open_player_action_question",
                      "reason": "multiple_questions", "word_count": len(words)},
        )

    normalized = _normalize_for_policy(value)
    raw_question_clause = re.split(r"[.;:]", value)[-1].strip()
    question_clause = re.split(r"[.;:]", normalized)[-1].strip()
    main_question_clause = re.split(
        r"\b(?:enquanto|quando|antes\s+que|depois\s+que|se|caso)\b",
        question_clause,
        maxsplit=1,
    )[0].strip()
    raw_main_question_clause = re.split(
        r"\b(?:enquanto|quando|antes\s+que|depois\s+que|se|caso)\b",
        raw_question_clause,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    normalized_player_aliases = _normalized_aliases(
        (
            "voce",
            "seu personagem",
            "sua personagem",
            "o personagem",
            "a personagem",
            *player_alias_records,
        )
    )
    normalized_named_player_aliases = _normalized_aliases(player_alias_records)
    normalized_npc_aliases = _normalized_aliases(npc_aliases)
    # Recognize registered player subjects with the same question cues as
    # "voce". Only the initial grammatical subject is normalized; mentions in
    # NPC objects or subordinate clauses must not become player invitations.
    player_subjects = "|".join(
        sorted(
            (re.escape(alias) for alias in normalized_player_aliases),
            key=len,
            reverse=True,
        )
    )
    player_cue_clause = re.sub(
        rf"^(como|o\s+que)\s+(?:{player_subjects})(?=\s)",
        r"\1 voce",
        main_question_clause,
        count=1,
    )
    full_player_cue_clause = re.sub(
        rf"^(como|o\s+que)\s+(?:{player_subjects})(?=\s)",
        r"\1 voce", normalized, count=1,
    )
    action_matches = _action_signature_matches(main_question_clause)
    player_precedes_action = any(
        _last_alias_position(
            main_question_clause[: action_match.start()],
            normalized_player_aliases,
        )
        >= 0
        for _, _, action_match in action_matches
    )
    explicit_player_cue = bool(
        re.search(
            r"\b(?:voce|seu\s+personagem|sua\s+personagem)\b"
            r"[^?]{0,40}\b(?:faz|fara|age|agira|reage|reagira|"
            r"responde|procedera|pretende|vai|lida|lidara)\b|"
            + _PLAYER_PROMPT_POSSESSIVE_ACTION,
            player_cue_clause,
        )
    )
    question_mentions_named_player = (
        _last_alias_position(
            main_question_clause,
            normalized_named_player_aliases,
        )
        >= 0
    )
    # This initial question has an omitted player subject. Keep its tail
    # limited to context/goal phrases: neither a postverbal NPC nor a
    # vocative may acquire the player's choice through this new cue.
    implicit_player_step = re.fullmatch(
        r"qual\s+(?:o\s+)?proximo\s+passo\s+deseja\s+tomar"
        r"(?:\s+(?:para|diante|em\s+relacao)\b[^,?]*)?\?",
        main_question_clause,
    )
    # These modal questions must occupy the whole field, not a clause left
    # after an instruction or asserted player action. Their context adjuncts
    # cannot contain another sentence, postverbal subject or NPC vocative.
    modal_question_tail = (
        r"(?:\s+(?:agora|a\s+seguir|em\s+seguida))?"
        r"(?:\s+(?:diante\s+(?:de|da|do|das|dos)|em\s+relacao\s+(?:a|ao|as|aos))"
        r"\s+[^.!?;:,]+)?\?"
    )
    player_continuation = re.fullmatch(
        r"como\s+(?:voce\s+)?(?:deseja|gostaria\s+de)\s+prosseguir" + modal_question_tail,
        full_player_cue_clause,
    ) or re.fullmatch(
        r"como\s+voce\s+quer\s+proceder\s+com\s+o\s+registro\s+molhado\?",
        full_player_cue_clause,
    )
    elided_player_intent = re.fullmatch(
        r"o\s+que\s+(?:voce\s+)?(?:deseja|quer|gostaria\s+de)\s+fazer" + modal_question_tail,
        full_player_cue_clause,
    )
    elided_second_person_action = re.fullmatch(
        r"o\s+que\s+fazes" + modal_question_tail,
        normalized,
    )
    if (player_continuation or elided_player_intent or elided_second_person_action) and re.search(
        r"\b(?:diante\s+(?:da|de)|em\s+relacao\s+a)\s+"
        r"(?:(?:escrita|narracao)\s+(?:da|de)\s+)?(?:historia|narrativa)\b",
        full_player_cue_clause,
    ):
        raise SceneProposalError(
            "scene_player_prompt_not_actionable",
            evidence={"field": "player_prompt", "rule": "open_player_action_question",
                      "reason": "does_not_invite_player_action", "word_count": len(words)},
        )
    # The article in 'Qual e a sua proxima acao?' does not change the owner.
    # Require the whole field: a trailing valid question must not hide an
    # instruction, an NPC's question, another sentence or a closed menu.
    articled_player_choice = re.fullmatch(
        r"qual\s+(?:e|sera)\s+[ao]\s+" + _PLAYER_PROMPT_POSSESSIVE_ACTION
        + modal_question_tail,
        normalized,
    )
    # A whole-field question about an intended action preserves open agency;
    # no leading instruction, NPC owner or closed-menu suffix can match.
    intended_player_action = re.fullmatch(
        r"que\s+acao\s+voce\s+pretende\s+realizar" + modal_question_tail,
        normalized,
    )
    implicit_player_action = bool(
        implicit_player_step or player_continuation or elided_player_intent
        or elided_second_person_action or articled_player_choice or intended_player_action
    )
    question_addresses_player = (
        player_precedes_action
        or explicit_player_cue
        or question_mentions_named_player
        or implicit_player_action
    )
    question_mentions_npc = (
        _last_alias_position(main_question_clause, normalized_npc_aliases) >= 0
    )
    first_player_position = _first_alias_position(
        main_question_clause,
        normalized_player_aliases,
    )
    # "Qual será sua próxima atitude diante de Mara?" addresses the player;
    # the later NPC is context, not the owner of the possessive choice.
    # Anchor this form to the main question so an NPC's decision containing
    # "sua atitude" cannot turn into authorization to choose for that NPC.
    possessive_choice = re.match(
        r"^qual\s+(?:e|sera)\s+" + _PLAYER_PROMPT_POSSESSIVE_ACTION,
        main_question_clause,
    )
    if possessive_choice or implicit_player_action:
        first_player_position = 0
    first_npc_position = _first_alias_position(
        main_question_clause,
        normalized_npc_aliases,
    )
    npc_precedes_player = first_npc_position >= 0 and (
        first_player_position < 0 or first_npc_position < first_player_position
    )
    npc_is_addressee = any(
        re.search(rf",\s*{re.escape(alias)}\s*(?:,|\?\s*$|$)", main_question_clause)
        for alias in normalized_npc_aliases
    )
    has_named_actor_structure = bool(
        _PLAYER_PROMPT_NAMED_ACTOR.search(raw_main_question_clause)
    )
    has_common_actor_structure = bool(
        _PLAYER_PROMPT_COMMON_ACTOR.search(raw_main_question_clause)
    )
    actor_structure_names_player = _named_actor_structure_names_player(
        main_question_clause,
        normalized_player_aliases,
    )
    if (
        has_named_actor_structure or has_common_actor_structure
    ) and not actor_structure_names_player:
        raise SceneProposalError(
            "scene_player_prompt_not_actionable",
            evidence={
                "field": "player_prompt",
                "rule": "open_player_action_question",
                "reason": "addresses_non_player_actor",
                "word_count": len(words),
            },
        )
    if question_mentions_npc and (
        npc_precedes_player or npc_is_addressee or not question_addresses_player
    ):
        raise SceneProposalError(
            "scene_player_prompt_not_actionable",
            evidence={
                "field": "player_prompt",
                "rule": "open_player_action_question",
                "reason": "addresses_non_player_actor",
                "word_count": len(words),
            },
        )

    if _PLAYER_PROMPT_WORLD_FACT.search(normalized):
        raise SceneProposalError(
            "scene_player_prompt_not_actionable",
            evidence={
                "field": "player_prompt",
                "rule": "open_player_action_question",
                "reason": "asks_world_fact_or_npc_decision",
                "word_count": len(words),
            },
        )

    has_explicit_open_cue = bool(
        _PLAYER_PROMPT_ACTION_CUE.search(player_cue_clause) or implicit_player_action
    )
    starts_with_interrogative = bool(
        re.match(
            r"^(?:como|onde|quando|qual|que|o que|por que)\b",
            main_question_clause,
        )
    )
    names_player = _first_alias_position(main_question_clause, normalized_player_aliases) >= 0
    asks_player_action = bool(_action_concepts(main_question_clause))
    if (
        has_explicit_open_cue
        and (question_addresses_player or not question_mentions_npc)
    ) or (starts_with_interrogative and names_player and asks_player_action):
        return

    reason = (
        "closed_player_question"
        if re.match(
            r"^(?:voce|seu\s+personagem|sua\s+personagem)\b",
            main_question_clause,
        )
        else "does_not_invite_player_action"
    )
    code = (
        "scene_player_prompt_not_open"
        if reason == "closed_player_question"
        else "scene_player_prompt_not_actionable"
    )
    raise SceneProposalError(
        code,
        evidence={
            "field": "player_prompt",
            "rule": "open_player_action_question",
            "reason": reason,
            "word_count": len(words),
        },
    )


def _player_visible_scene_fields(
    proposal: SceneContinuationProposal,
) -> tuple[str, ...]:
    return (
        proposal.narrative,
        proposal.location,
        proposal.scene_summary,
        *proposal.npcs_present,
        *proposal.open_threads,
        *proposal.resolved_threads,
        proposal.player_prompt,
        *(
            fact.summary
            for fact in proposal.new_facts
            if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        ),
    )


def _player_visible_scene_assertions(
    proposal: SceneContinuationProposal,
) -> tuple[str, ...]:
    """Return claims about the turn, excluding questions and pending tasks."""

    return (
        proposal.narrative,
        proposal.scene_summary,
        *(
            fact.summary
            for fact in proposal.new_facts
            if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        ),
    )


def _meaningful_policy_tokens(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.findall(r"[a-z0-9]+", _normalize_for_policy(value))
        if len(token) >= 3 and token not in _POLICY_STOPWORDS
    )


def _paraphrase_concepts(value: str) -> frozenset[str]:
    normalized = _normalize_for_policy(value)
    return frozenset(
        concept
        for concept, pattern in _SECRET_PARAPHRASE_CONCEPTS
        if re.search(pattern, normalized)
    )


def _secret_overlap_evidence(secret: str, visible: str) -> dict[str, object] | None:
    """Explain the existing overlap gate without retaining either text."""
    secret_normalized = _normalize_for_policy(secret)
    visible_normalized = _normalize_for_policy(visible)
    if not secret_normalized or not visible_normalized:
        return None
    if secret_normalized in visible_normalized:
        return {
            "comparison": "normalized_substring", "shared_token_count": None,
            "token_denominator": None, "shared_concept_count": None,
        }

    secret_tokens = _meaningful_policy_tokens(secret)
    visible_tokens = _meaningful_policy_tokens(visible)
    shared_tokens = secret_tokens & visible_tokens
    denominator = max(1, min(len(secret_tokens), len(visible_tokens)))
    comparison = None
    if len(shared_tokens) >= 3:
        comparison = "shared_tokens"
    elif len(shared_tokens) >= 2 and len(shared_tokens) / denominator >= 0.5:
        comparison = "shared_token_ratio"
    if comparison is not None:
        return {
            "comparison": comparison, "shared_token_count": len(shared_tokens),
            "token_denominator": denominator, "shared_concept_count": None,
        }

    shared_concepts = _paraphrase_concepts(secret) & _paraphrase_concepts(visible)
    if len(shared_concepts) >= 2:
        return {
            "comparison": "shared_concepts", "shared_token_count": len(shared_tokens),
            "token_denominator": denominator, "shared_concept_count": len(shared_concepts),
        }
    return None


def _secret_overlaps_visible(secret: str, visible: str) -> bool:
    return _secret_overlap_evidence(secret, visible) is not None


def _validate_secret_separation(
    proposal: SceneContinuationProposal,
    visible_fields: tuple[str, ...],
    *,
    protected_secrets: Iterable[str] = (),
) -> None:
    secrets: dict[str, str] = {}
    for fact in proposal.new_facts:
        if fact.visibility is Visibility.STORYTELLER:
            secrets.setdefault(fact.summary, "in_proposal")
    for value in protected_secrets:
        if value.strip():
            secrets.setdefault(" ".join(value.split()), "protected_context")
    # Order and duplicate precedence match the original gate. Indices refer
    # only to the fixed visible-field sequence, never to secret text or IDs.
    field_names = (
        "narrative", "location", "scene_summary",
        *("npcs_present" for _ in proposal.npcs_present),
        *("open_threads" for _ in proposal.open_threads),
        *("resolved_threads" for _ in proposal.resolved_threads),
        "player_prompt",
        *(
            "new_facts" for fact in proposal.new_facts
            if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        ),
    )
    for secret, source in secrets.items():
        for index, field in enumerate(visible_fields):
            evidence = _secret_overlap_evidence(secret, field)
            if evidence is not None:
                diagnostic = (
                    {"field": field_names[index], "field_index": index,
                     "source": source, **evidence}
                    if index < len(field_names) else None
                )
                raise SceneProposalError(
                    "scene_secret_disclosed", evidence=diagnostic,
                )


def _has_passive_player_agent(
    value: str, action_match: re.Match[str], *, player_aliases: Iterable[str] = (),
) -> bool:
    """A perceived passive must not hide an explicit player as its agent."""

    if not re.fullmatch(r"(?:[a-z]+(?:ad|id)[oa]s?|ocult[oa]s?)", action_match.group()):
        return False
    agents = {"voce", "mim", "jogador", "personagem", *_normalized_aliases(player_aliases)}
    agent_pattern = "|".join(re.escape(alias) for alias in sorted(agents, key=len, reverse=True))
    return re.match(
        rf"^(?:\s+por\s+(?:entulhos|escombros)(?:\s+e|\s*,)\s+(?:(?:por|pelo|pela)\s+)?|"
        rf"\s+(?:por|pelo|pela)\s+)(?:(?:o|a|seu|sua)\s+)?(?:{agent_pattern}|suas?\s+maos?)\b",
        value[action_match.end() :],
    ) is not None


def _is_found_physical_cover(value: str, action_match: re.Match[str]) -> bool:
    """A discovered door's attributed cover is not concealment by the player.

    Limit the exception to this adjective and its physical cause; neither the
    discovery verb nor the rest of the clause receives blanket authorization.
    """

    if action_match.group() != "oculta":
        return False
    return bool(
        re.search(
            r"\b(?:encontra|encontro|encontrou|ve|vejo|viu)\s+(?:uma|a)\s+porta"
            r"(?:\s+(?:de\s+ferro|lateral|enferrujada|parcialmente|completamente))*\s+$",
            value[: action_match.start()],
        )
        and re.match(
            r"^\s+por\s+(?:entulhos|escombros)\b(?=\s*[,.;!?]|\s*$|\s+e\b)",
            value[action_match.end() :],
        )
    )


def _is_perceived_environmental_participle(value: str, action_match: re.Match[str]) -> bool:
    """Recognize attributed erosion, not a new voluntary erasing action.

    This is deliberately a narrow adjective/physical-cause construction. It
    does not infer the actor of arbitrary passives or waive a following verb.
    """

    if not re.fullmatch(r"apagad[oa]s?", action_match.group()):
        return False
    prefix = value[: action_match.start()]
    if "," not in prefix:
        return False
    perceived, modifier = prefix.rsplit(",", 1)
    if not re.fullmatch(r"\s*(?:(?:parcialmente|completamente|quase|totalmente)\s+)?", modifier):
        return False
    perceptions = tuple(_PERCEPTION_VERB.finditer(perceived))
    if not perceptions:
        return False
    complement = perceived[perceptions[-1].end() :].strip()
    if not re.fullmatch(
        r"(?:que\s+)?(?:a|o|as|os|um|uma)\s+"
        r"(?:linhas?|padrao|runas?|placas?|textos?|simbolos?|sinais?|"
        r"inscricoes|inscricao|marcas?|desenhos?|letreiros?)\b[^,;.!?]{0,160}",
        complement,
    ):
        return False
    if _PLAYER_CONTROL_CUE.search(complement) or re.search(
        r"\b(?:voce|jogador|personagem|corpo|pele|dedos?|maos?|rosto|olhos?|"
        r"obrig\w*|mand\w*|faz|fazem|fazer|forc\w*)\b", complement,
    ):
        return False
    return re.match(
        r"^\s+(?:por(?:\s+(?:a|o))?|pelo|pela)\s+"
        r"(?:ferrugem|chuva|agua|umidade|desgaste|erosao)\b(?=\s*[,.;!?]|\s*$)",
        value[action_match.end() :],
    ) is not None


def _is_known_npc_relative_action(
    value: str, action_match: re.Match[str], *, concept: str, npc_aliases: Iterable[str],
    player_aliases: Iterable[str],
) -> bool:
    """Bind only the immediate verb of a perceived, named NPC's relative."""

    # Naming the NPC as actor does not authorize imposing decisions, persuasion
    # outcomes, injury or feeding on the player. Leave these existing checks in
    # force; this exception only resolves bounded external-world attribution.
    if concept in {"choice", "social", "combat", "consume"}:
        return False
    players = {"voce", "eu", "jogador", "personagem", *_normalized_aliases(player_aliases)}
    npcs = set(_normalized_aliases(npc_aliases)) - players
    if not npcs:
        return False
    player_pattern = "|".join(re.escape(alias) for alias in sorted(players, key=len, reverse=True))
    complement = value[action_match.end() :]
    # Opening a door "por você" is still the NPC's own action. Do not confuse
    # that final beneficiary with a player as direct target or possessive owner.
    complement = re.sub(rf"\s+por\s+(?:{player_pattern})\s*$", "", complement)
    if re.search(rf"\b(?:{player_pattern}|mim|seu|sua|seus|suas)\b", complement):
        return False
    npc_pattern = "|".join(re.escape(alias) for alias in sorted(npcs, key=len, reverse=True))
    return re.fullmatch(
        r"\s*(?:(?:observ\w*|perceb\w*|ve|vejo|viu|escut\w*|ouv\w*)\s+(?:(?:a|o)\s+)?|"
        r"fix(?:a|o|ou)\s+o\s+olhar\s+(?:em|na|no)\s+(?:(?:figura|rosto)\s+de\s+)?)"
        rf"(?:{npc_pattern}),\s*que\s+(?:(?:ainda|ja|nao)\s+)*",
        value[: action_match.start()],
    ) is not None


def _is_perceived_actor_action(
    value: str, action_match: re.Match[str], *, player_aliases: Iterable[str] = (),
) -> bool:
    """Return true when the matched verb belongs to what the player perceives.

    In Portuguese, perception commonly uses a bare infinitive with its own
    subject (``você sente o frio subir``). Scanning the entire player clause
    otherwise misattributes ``subir`` to the player. Volitional complements
    such as ``para subir`` and ``decide subir`` deliberately remain player
    actions.
    """

    if _has_passive_player_agent(value, action_match, player_aliases=player_aliases):
        return False
    if _is_found_physical_cover(value, action_match) or _is_perceived_environmental_participle(value, action_match):
        return True
    prefix = value[: action_match.start()]
    boundaries = tuple(
        re.finditer(r",|\b(?:e|mas|porem|entao|enquanto|quando)\b", prefix)
    )
    segment = prefix[boundaries[-1].end() :] if boundaries else prefix
    # A conjunction can introduce a new, explicit environmental subject:
    # ``sente passos, mas a sombra permanece oculta``. The perception's
    # complement does not have to repeat its verb. Only this bounded subject
    # vocabulary is recognized; an omitted subject or ``ela`` stays ambiguous.
    # Never waive a later player subject, obligation or voluntary action.
    player_subject = re.compile(
        r"\b(?:voce|eu|jogador|personagem)\b"
    )
    if (
        boundaries
        and _PERCEPTION_VERB.search(prefix[: boundaries[-1].start()])
        and re.match(
            r"^\s*(?:(?:apenas|somente)\s+)?(?:a|o|as|os|um|uma|uns|umas)\s+"
            r"(?:sombra|sombras|mare|frio|vento|chuva|agua|fumaca|nevoa|"
            r"corrente|luz|luzes|porta|portas|janela|janelas|informacao|informacoes)\b",
            segment,
        )
        and len(re.findall(r"[a-z0-9]+", segment)) <= 10
        and not player_subject.search(segment)
        and not _PLAYER_CONTROL_CUE.search(segment)
        # Relative clauses and causative/command complements can introduce
        # a different actor, including a named player; do not infer its owner.
        and not re.search(
            r"\b(?:que|quem|obrig\w*|mand\w*|faz|fazem|fazer|forc\w*)\b",
            segment,
        )
    ):
        return True
    perception_matches = tuple(_PERCEPTION_VERB.finditer(segment))
    if not perception_matches:
        return False

    complement = segment[perception_matches[-1].end() :].strip()
    if (
        not complement
        or _PLAYER_CONTROL_CUE.search(complement)
        or player_subject.search(complement)
        or re.search(r"\b(?:obrig\w*|mand\w*|faz|fazem|fazer|forc\w*)\b", complement)
        or re.fullmatch(r"que(?:\s+(?:ja|nao|ainda|esta|estava|estou|foi|fui))*", complement)
    ):
        return False
    complement_tokens = re.findall(r"[a-z0-9]+", complement)
    return 1 <= len(complement_tokens) <= 6


def _action_signature_matches(
    value: str, *, player_aliases: Iterable[str] = (),
) -> tuple[tuple[str, str, re.Match[str]], ...]:
    normalized = _normalize_for_policy(value)
    matches: list[tuple[str, str, re.Match[str]]] = []
    for concept, family, pattern in _PLAYER_ACTION_PATTERNS:
        for match in re.finditer(pattern, normalized):
            # The noun in em mente is not the verb mentir. Skip this token
            # only; actual lying and coordinated player actions stay visible.
            if (family == "lie" and match.group() == "mente"
                    and re.search(r"\bem\s+$", normalized[:match.start()])):
                continue
            # The exact noun material is not a conjugation of matar.
            # Skip only this token; real killing and later actions remain.
            if family == "kill" and match.group() == "material":
                continue
            # A future passive condition of the record executes no inspection.
            # Keep actual player examination and every later verb visible.
            if (family == "inspect_general" and match.group() == "examinado"
                    and re.search(r"\bo registro ficara em melhores condicoes para ser\s+$", normalized[:match.start()])
                    and re.match(r"\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Water traversing record pages is not player travel.
            # Retain any other crossing or subsequent player action.
            if (family == "cross" and match.group() == "atravessar"
                    and re.search(r"\ba agua continua sobre a bancada baixa ate\s+$", normalized[:match.start()])
                    and re.match(r"\s+completamente o registro\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            if (family == "cross" and match.group() == "atravessa"
                    and re.search(r"\bmas a agua continua sobre a bancada baixa e\s+$", normalized[:match.start()])
                    and re.match(r"\s+o registro\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            if (family == "cross" and match.group() == "atravessa"
                    and re.search(r"\benquanto\s+a\s+agua\s+alcanca\s+a\s+bancada\s+baixa\s+e\s+$", normalized[:match.start()])
                    and re.match(r"\s+as\s+paginas\s+do\s+registro\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Water owns this explicit contact; the waiting player does not.
            # Keep every other touch/action visible to the agency guard.
            if (family == "touch" and match.group() == "toca"
                    and re.search(r"\benquanto\s+a\s+agua\s+alcanca\s+a\s+bancada\s+baixa\s+e\s+$", normalized[:match.start()])
                    and re.match(r"\s+o\s+registro\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Explicit infiltration, not the waiting player, advances here.
            # A relative clause with explicit drops has the same nonplayer
            # actor. Skip that verb only, never coordinated player movement.
            if (family == "advance" and match.group() == "avancam"
                    and re.search(r"\bas gotas que\s+$", normalized[:match.start()])
                    and re.match(r"\s+pela estrutura\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Its spatial complement cannot change that actor. Skip only this
            # token, retaining every coordinated/subsequent player action.
            if (family == "advance" and match.group() == "avanca"
                    and re.search(r"\b(?:a\s+(?:infiltracao|agua)|na\s+umidade\s+que)\s+$", normalized[:match.start()])):
                continue
            # Infiltration owns this bounded gerund, not the waiting player.
            if (family == "advance" and match.group() == "avancando"
                    and re.search(r"\bmas a agua continua\s+$", normalized[:match.start()])):
                continue
            if (family == "advance" and match.group() == "avancando"
                    and re.search(r"\ba\s+infiltracao\s+se\s+espalha\s+pela\s+parede\s+do\s+arquivo,\s*$", normalized[:match.start()])
                    and re.match(r"\s+o\s+bastante\s+para\s+tornar\s+o\s+risco\s+imediato\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # This separate water clause also has an explicit nonplayer actor.
            # Keep all later verbs and any other actor visible to the guard.
            if (family == "advance" and match.group() == "avanca"
                    and re.search(r"\be\s+a\s+agua\s+$", normalized[:match.start()])
                    and re.match(r"\s+sobre\s+o\s+registro\s+na\s+bancada\s+baixa\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Following legible marks during this explicit record inspection
            # describes reading, not a journey. No later verb is skipped.
            if (family == "follow" and match.group() == "seguindo"
                    and re.search(r"\bexamina\s+o\s+registro\s+sobre\s+a\s+bancada\s+baixa\s+no\s+arquivo,\s*$", normalized[:match.start()])
                    and re.match(r"\s+marcas\s+e\s+trechos\s+ainda\s+legiveis\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # 'Mantendo o tom contido' names vocal tone, not taking control.
            # Only the nominal token is waived; later player verbs remain.
            if (family == "take_control" and match.group() == "tom"
                    and re.search(r"\bmantendo\s+o\s+$", normalized[:match.start()])
                    and re.match(r"\s+contido(?=\s*(?:[.!?;:,]|$)|\s+apesar\b)", normalized[match.end():])):
                continue
            # This bounded environmental subject owns the threat, not a
            # player mentioned earlier. Keep all subsequent actions visible.
            if (family == "threaten" and match.group() == "ameaca"
                    and re.search(r"\benquanto\s+a\s+infiltracao\s+$", normalized[:match.start()])
                    and re.match(r"\s+a\s+bancada\s+baixa\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # In this local removal clause, -o refers to the explicit record,
            # not a reflexive player retreat. Do not waive another antecedent.
            if (family == "withdraw" and match.group() == "afastando"
                    and re.search(r"\bretira o registro molhado da bancada baixa,\s*$", normalized[:match.start()])
                    and re.match(r"[-\u2010\u2011]o da agua que se espalha pelo arquivo\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            if (family == "withdraw" and match.group() == "afastando"
                    and re.search(r"\bretira\s+o\s+registro\b[^.!?;:]*,\s*$", normalized[:match.start()])
                    and re.match(r"[-\u2010\u2011]o\s+da\s+infiltracao\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # This explicit atmospheric subject is not the player closing.
            # Keep concrete player actions and every subsequent verb visible.
            if (family == "close" and match.group() == "fechar"
                    and re.search(r"\bo\s+arquivo\s+parece\s+se\s+$", normalized[:match.start()])
                    and re.match(r"\s+ao\s+redor\s+da\s+bancada\s+baixa\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Avoiding an object's exposure does not assert player waiting.
            # Restrict to this explicit object/state frame, not later actions.
            if (family == "remain" and match.group() == "permaneca"
                    and re.search(r"\bevitando\s+que\s+o\s+registro\s+$", normalized[:match.start()])
                    and re.match(r"\s+exposto\s+ao\s+risco\s+atual\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # The explicit infiltration subject owns this bounded gerund,
            # not the waiting player. Keep every later action visible.
            if (family == "approach" and match.group() == "aproximando"
                    and re.search(r"\ba\s+infiltracao\s+se\s+espalha\s+pelas\s+paredes\s+do\s+arquivo,\s*$", normalized[:match.start()])
                    and re.match(r"-se\s+da\s+bancada\s+baixa\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # A bounded temporal clause names moisture, not the player.
            # Skip only its advance predicate; all later actions stay visible.
            if (family == "advance" and match.group() == "avance"
                    and re.search(r"\bantes\s+que\s+a\s+umidade\s+$", normalized[:match.start()])
                    and re.match(r"(?:\s+mais)?\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            # Plural document fragments are not the player's departure.
            # Require this bounded nominal frame; later verbs remain scanned.
            # Possessive + legibility explicitly names document parts, not
            # player departure. Skip only this token, retaining later verbs.
            if (family == "depart" and match.group() == "parte"
                    and re.search(r"\brecuper(?:a|ou)\s+$", normalized[:match.start()])
                    and re.match(r"\s+da informacao\b", normalized[match.end():])):
                continue
            if (family == "depart" and match.group() == "partes"
                    and re.search(r"\b(?:de\s+suas|das)\s+$", normalized[:match.start()])
                    and re.match(r"\s+ainda\s+legiveis\s*(?:[.!?;:,]|$)", normalized[match.end():])):
                continue
            if (family == "depart" and match.group() == "partes"
                    and re.search(r"\bentre\s+as\s+$", normalized[:match.start()])
                    and re.match(r"\s+(?:preservadas\b|(?:ainda\s+)?legiveis\s*(?:[.!?;:,]|$))", normalized[match.end():])):
                continue
            if family == "manipulate":
                if re.search(
                    r"\b(?:nao|nunca|jamais)\s+(?:tenta\s+)?$", normalized[:match.start()],
                ):
                    continue
                # Only a condition on this manipulation makes it hypothetical;
                # another actor/action after a boundary keeps its own scope.
                complement = re.split(
                    r"[?!;:.]|,(?!\s*(?:se|caso)\b)|\b(?:e|mas|porem|enquanto|quando)\b",
                    normalized[match.end():], maxsplit=1,
                )[0]
                if re.search(r"\b(?:se|caso)\b", complement):
                    continue
            if _is_perceived_actor_action(normalized, match, player_aliases=player_aliases):
                continue
            matches.append((concept, family, match))
    return tuple(matches)


def _action_signatures(value: str) -> frozenset[tuple[str, str]]:
    return frozenset(
        (concept, family)
        for concept, family, _ in _action_signature_matches(value)
    )


def _action_concepts(value: str) -> frozenset[str]:
    return frozenset(concept for concept, _ in _action_signatures(value))


def _action_target_tokens(
    normalized: str,
    action_match: re.Match[str],
) -> tuple[str, ...]:
    """Extract a bounded, non-sensitive signature of an explicit target."""

    suffix = normalized[action_match.end() :]
    boundary = _ACTION_TARGET_BOUNDARY.search(suffix)
    segment = suffix[: boundary.start()] if boundary is not None else suffix
    return tuple(
        dict.fromkeys(
            token
            for token in re.findall(r"[a-z0-9]+", segment)
            if len(token) >= 3 and token not in _ACTION_TARGET_STOPWORDS
        )
    )


def _declared_player_exploration_targets(value: str) -> tuple[tuple[str, ...], ...]:
    """Keep the new exploration family limited to positive player declarations."""
    unquoted = re.sub(r'["“«`\x27][^"”»`\x27]*(?:["”»`\x27]|$)', " ", value)
    unquoted = re.sub(r":[^\n]*|(?:^|\n)\s*[-—–][^\n]*", " ", unquoted)
    targets = []
    for statement in re.finditer(r"([^.!?;\n]*)([.!?;\n]|$)", unquoted):
        clause = statement.group(1)
        if statement.group(2) == "?" or re.search(
            r"\b(?:se|caso|quando|talvez|ou)\b", clause,
        ):
            continue
        for index, fragment in enumerate(re.split(r"\s+(?:e|mas)\s+", clause)):
            # A coordinated first-person verb states its own player subject;
            # an infinitive alone must not inherit an ambiguous actor.
            declaration = re.match(
                r"^\s*(?:eu\s+)?(?P<action>exploro|(?:vou|tento)\s+explorar"
                + (r"|explorar" if index == 0 else "") + r")\b", fragment,
            )
            if declaration is not None:
                targets.append(_action_target_tokens(fragment, declaration))
    return tuple(targets)


def _declared_player_manipulation_targets(value: str) -> tuple[tuple[str, ...], ...]:
    """The new manipulation family requires a positive player declaration."""
    unquoted = re.sub(r'["“‘«`\x27][^"”’»`\x27]*(?:["”’»`\x27]|$)', " ", value)
    unquoted = re.sub(r":[^\n]*|(?:^|\n)\s*[-—–][^\n]*", " ", unquoted)
    targets = []
    for statement in re.finditer(r"([^.!?;\n]*)([.!?;\n]|$)", unquoted):
        clause = statement.group(1)
        if statement.group(2) == "?" or re.search(r"\b(?:se|caso|quando|talvez|ou)\b", clause):
            continue
        for index, fragment in enumerate(re.split(r"\s+(?:e|mas)\s+", clause)):
            declaration = re.match(
                r"^\s*(?:eu\s+)?(?:manipulo|(?:vou|tento)\s+manipular"
                + (r"|manipular" if index == 0 else "") + r")\b", fragment,
            )
            if declaration is not None:
                targets.append(_action_target_tokens(fragment, declaration))
    return tuple(targets)


def _action_authorizations(
    value: str,
) -> dict[tuple[str, str], tuple[tuple[str, ...], ...]]:
    normalized = _normalize_for_policy(value)
    targets: dict[tuple[str, str], list[tuple[str, ...]]] = {}
    for concept, family, match in _action_signature_matches(normalized):
        if family in {"explore", "manipulate"}:
            # The newly recognized family needs a declaration, not a quoted,
            # conditional or NPC mention. Existing families stay unchanged.
            continue
        targets.setdefault((concept, family), []).append(
            _action_target_tokens(normalized, match)
        )
    for target in _declared_player_exploration_targets(normalized):
        targets.setdefault(("inspect", "explore"), []).append(target)
    for target in _declared_player_manipulation_targets(normalized):
        targets.setdefault(("interact", "manipulate"), []).append(target)
    # Only an explicit, positive player declaration grants cross-family wait
    # equivalence. Keep existing families (especially "remain") distinct.
    # Quoted speech cannot grant it, nor can an NPC, negation or "esperanca".
    unquoted = re.sub(r'["“«`\x27][^"”»`\x27]*(?:["”»`\x27]|$)', " ", normalized)
    unquoted = re.sub(r":[^\n]*|(?:^|\n)\s*[-—–][^\n]*", " ", unquoted)
    for sentence in re.split(r"[.!?;\n]", unquoted):
        clauses = re.split(r"\s+e\s+", sentence)
        player_coordination = bool(re.match(
            r"^\s*(?:eu\s+)?(?:observo|investigo|examino|olho|escuto|ouco|espero|aguardo)\b",
            clauses[0],
        ))
        for index, clause in enumerate(clauses):
            if index and not player_coordination and not re.match(r"^\s*eu\s+", clause):
                continue
            wait_pattern = (
                r"^\s*(?:eu\s+)?(?P<action>espero|aguardo|vou\s+(?:esperar|aguardar))\b"
                if index else
                r"^\s*(?:eu\s+)?(?:vou\s+)?(?P<action>espero|aguardo|esperar|aguardar)\b"
            )
            wait = re.match(wait_pattern, clause)
            if wait:
                targets.setdefault(("wait", "explicit_wait_equivalent"), []).append(
                    _equivalent_wait_target(_action_target_tokens(clause, wait))
                )
            elif index:
                # Do not carry the implicit player through a changed subject,
                # a command or a negated action to another coordinated verb.
                player_coordination = False
    return {signature: tuple(values) for signature, values in targets.items()}


def _equivalent_wait_target(target: tuple[str, ...]) -> tuple[str, ...]:
    return tuple("resposta" if token == "reacao" else token for token in target)


def _action_target_is_authorized(
    proposed_target: tuple[str, ...],
    declared_targets: tuple[tuple[str, ...], ...],
) -> bool:
    # An omitted or pronominal object may safely refer back to the declared
    # action. If both sides name an object, at least one meaningful token must
    # remain compatible as a phrase. A subset supports an implicit or more
    # specific reference to the same object; partial overlap never lets a
    # shared adjective turn ``porta lateral`` into ``janela lateral``. Tokens
    # remain internal and are never included in evidence.
    if not proposed_target or any(not target for target in declared_targets):
        return True
    proposed = frozenset(proposed_target)
    return any(
        proposed_target == target[: len(proposed_target)]
        or target == proposed_target[: len(target)]
        for target in declared_targets
    )


def _is_explicit_barrier_state(
    value: str, action_match: re.Match[str], *, antecedent_prefix: str = "",
    player_aliases: Iterable[str] = (),
) -> bool:
    """Resolve only a barrier's physical remain-state, not another pronoun action."""
    if action_match.group() != "permanece" or not re.match(
        r"\s+(?:firme|fechad[oa]|trancad[oa]|travad[oa])\b", value[action_match.end():],
    ):
        return False
    prefix = antecedent_prefix + value[:action_match.start()]
    subject = re.search(
        rf"(?:^|,\s*(?:(?:mas|porem|e)\s+)?|\b(?:mas|porem|e)\s+)"
        rf"(?P<subject>ele|ela|(?:a|o)\s+{_MECHANICAL_BARRIER})\s*$", prefix,
    )
    if subject is None:
        return False
    if subject.group("subject") not in {"ele", "ela"}:
        return True
    players = "|".join(re.escape(alias) for alias in _normalized_aliases((
        "voce", "seu personagem", "sua personagem", "o personagem", "a personagem", *player_aliases,
    )))
    antecedent = re.fullmatch(
        rf"\s*(?:(?:{players})\s+)?(?:tenta\s+)?"
        r"(?:examina|investiga|observa|manipula|examinar|investigar|observar|manipular)\s+"
        r"(?P<article>o|a)\s+(?:cadeado|portao|porta|grade|tranca|fechadura)"
        r"(?:\s+(?:lateral|extern[oa]|intern[oa]|enferrujad[oa]|trancad[oa]))*\s*",
        prefix[:subject.start()],
    )
    return antecedent is not None and (
        (subject.group("subject") == "ele") == (antecedent.group("article") == "o")
    )


def _unauthorized_action_concepts(
    value: str,
    *,
    authorized_actions: Mapping[
        tuple[str, str], tuple[tuple[str, ...], ...]
    ],
    player_aliases: Iterable[str] = (),
    npc_aliases: Iterable[str] = (),
    npc_observer_object: bool = False,
    antecedent_prefix: str = "",
) -> list[str]:
    normalized = _normalize_for_policy(value)
    unauthorized: set[str] = set()
    for concept, family, match in _action_signature_matches(normalized, player_aliases=player_aliases):
        if concept == "wait" and family == "remain" and _is_explicit_barrier_state(
            normalized, match, antecedent_prefix=antecedent_prefix, player_aliases=player_aliases,
        ):
            continue
        if family == "manipulate":
            players = {"voce", "eu", "personagem", "jogador", *_normalized_aliases(player_aliases)}
            npcs = set(_normalized_aliases(npc_aliases)) - players
            npc_subjects = "|".join(re.escape(alias) for alias in sorted(npcs, key=len, reverse=True))
            target_clause = _ACTION_TARGET_BOUNDARY.split(normalized[match.end():], maxsplit=1)[0]
            if npcs and re.search(
                rf"(?:^|,\s*|\b(?:mas|porem|e)\s+)(?:{npc_subjects})\s+(?:tenta\s+)?$",
                normalized[:match.start()],
            ) and not re.search(
                r"\b(?:voce|mim|personagem|seus?|suas?|teus?|tuas?)\b", target_clause,
            ) and _last_alias_position(target_clause, tuple(players)) < 0:
                continue
        if npc_observer_object and _is_npc_observer_coordinate_action(
            normalized, match, concept=concept, player_aliases=player_aliases,
        ):
            continue
        if _is_known_npc_relative_action(
            normalized, match, concept=concept, npc_aliases=npc_aliases,
            player_aliases=player_aliases,
        ):
            continue
        declared_targets = authorized_actions.get((concept, family))
        if (
            declared_targets is None
            and concept == "wait" and family in {"wait", "await"}
            and _equivalent_wait_target(_action_target_tokens(normalized, match))
            in authorized_actions.get(("wait", "explicit_wait_equivalent"), ())
        ):
            continue
        target_mismatch = (
            concept in _TARGET_SENSITIVE_ACTION_CONCEPTS
            and declared_targets is not None
            and not _action_target_is_authorized(
                _action_target_tokens(normalized, match),
                declared_targets,
            )
        )
        if declared_targets is None or target_mismatch:
            unauthorized.add(concept)
    return sorted(unauthorized)


def _observer_narration_without_speech(value: str) -> str | None:
    """Mask balanced speech only for actor proof, preserving every offset.

    The actual agency scan still sees the complete original text. An object
    inside unfinished speech cannot borrow an actor from outside that speech.
    """
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’", "«": "»", "`": "`"}
    masked = list(value)
    closing: str | None = None
    for index, character in enumerate(value):
        if closing is not None:
            masked[index] = " "
            if character == closing:
                closing = None
        elif character in pairs:
            if character == "'" and 0 < index < len(value) - 1 and value[index - 1].isalpha() and value[index + 1].isalpha():
                continue
            closing = pairs[character]
            masked[index] = " "
        elif character in {"”", "’", "»"}:
            return None
        elif character in {"—", "–"}:
            # Direct speech without a delimited quotation is not narrator
            # evidence of a named actor. The recorded reporting clause has
            # a dash followed by a complete quoted block, then 'diz ela'.
            following = value[index + 1:].lstrip()
            if not following or following[0] not in pairs:
                return None
    return None if closing is not None else "".join(masked)


def _observer_subject_tail(tail: str) -> bool:
    """Require the entire local gesture/reporting tail to remain non-personal.

    Unknown comma fragments invalidate attribution; a recognized subject at
    the beginning cannot hide a subsequent person with an unfamiliar verb.
    """
    parts = [part.strip() for part in tail.split(",")]
    if re.fullmatch(
        r"(?:(?:a\s+(?:cabeca|mao)|o\s+(?:rosto|braco)|os\s+(?:olhos|ombros))"
        r"(?:\s+(?:devagar|lentamente|levemente))?|devagar|lentamente|levemente)?",
        parts[0],
    ) is None:
        return False
    adjunct = re.compile(
        r"(?:(?:o\s+(?:sorriso|rosto)|os\s+(?:dedos|olhos)|as\s+maos)\s+"
        r"[a-z]+(?:ando|endo|indo)\b[^,]*|"
        r"[a-z]+(?:ado|ada|ido|ida)\s+por\s+[^,]+|"
        r"a\s+voz\s+(?:baixa|suave|firme)|"
        r"quase\s+(?:um|uma)\s+(?:sussurro|murmurio|suspiro)|"
        r"como\s+se\s+(?:tentasse|buscasse|quisesse)\s+[^,]+)"
    )
    return all(adjunct.fullmatch(part) is not None for part in parts[1:])


def _known_npc_observes_player_object(
    prefix: str, *, player_aliases: Iterable[str], npc_aliases: Iterable[str],
) -> bool:
    players = {"voce", "jogador", "personagem", *_normalized_aliases(player_aliases)}
    npcs = set(_normalized_aliases(npc_aliases)) - players
    sentence_prefix = re.split(r"[.!?;:]", prefix)[-1]
    if any(re.fullmatch(
        rf"\s*(?:(?:a|o)\s+)?{re.escape(npc)}\s+(?:observa|ve)\s+",
        sentence_prefix,
    ) for npc in npcs):
        return True
    if not npcs:
        return False
    unquoted = _observer_narration_without_speech(prefix)
    if unquoted is None:
        return False
    segments = [part.strip(" ,—–-\t\r\n") for part in re.split(r"[.!?;:]", unquoted)]
    segments = [part for part in segments if part]
    if not segments:
        return False
    names = "|".join(re.escape(alias) for alias in sorted(npcs, key=len, reverse=True))
    # This local chain recognizes subjects of ordinary gestures/reporting;
    # a last mention, a roster entry or a name used as object is insufficient.
    predicates = r"(?:inclina|ergue|levanta|para|sorri|observa|ve|diz|responde|pergunta|explica)"
    subject = re.compile(rf"^(?:(?:a|o)\s+)?(?P<actor>{names}|ele|ela)\s+{predicates}\b")
    actor: str | None = None
    for segment in segments[:-1]:
        if (_last_alias_position(segment, tuple(players)) >= 0
                or re.search(r"\b(?:e|mas|porem|enquanto|quando|que|quem)\b", segment)
                or re.search(r"\b(?:seus?|suas?|teus?|tuas?|mim|lhe|te|ti)\b", segment)):
            actor = None
            continue
        declared = subject.match(segment)
        reporting = re.match(r"^(?:diz|responde|pergunta|explica)\s+(?:ele|ela)\b", segment)
        predicate = declared or reporting
        if predicate is None or not _observer_subject_tail(segment[predicate.end():]):
            actor = None
            continue
        mentioned = {npc for npc in npcs if _last_alias_position(segment, (npc,)) >= 0}
        if declared is not None and declared.group("actor") in npcs:
            actor = declared.group("actor") if mentioned == {declared.group("actor")} else None
        elif ((declared is not None and declared.group("actor") in {"ele", "ela"})
                or reporting is not None):
            if mentioned:
                actor = None
        else:
            actor = None
    perception = re.fullmatch(
        rf"(?:(?:a|o)\s+)?(?P<actor>{names}|ele|ela)\s+"
        r"(?:(?:observa|ve)|(?:para|sorri)\s*,\s*(?:observando|vendo)|"
        r"continua\s+(?:observando|vendo))",
        segments[-1],
    )
    if perception is None:
        return False
    observer = perception.group("actor")
    return observer in npcs or (observer in {"ele", "ela"} and actor is not None)


def _observer_wait_predicate(
    value: str, action_match: re.Match[str], *, protected_reference: str,
) -> bool:
    """Prove only this wait gerund or this non-personal information state.

    The comma attaches the gerund to the observer. In an indirect question,
    the explicit informational noun owns its state and the 'ou se' predicate.
    Neither proof authorizes another verb in the same player-object clause.
    """
    prefix, complement = value[:action_match.start()], value[action_match.end():]
    if re.search(protected_reference, value):
        return False
    adjunct = r"\s*(?:com\s+(?:atencao|cuidado|curiosidade)\s*)?,\s*"
    if action_match.group() in {"esperando", "aguardando"}:
        return re.fullmatch(adjunct, prefix) is not None
    if action_match.group() != "permanece":
        return False
    return re.fullmatch(
        adjunct + r"(?:esperando|aguardando)\s+para\s+ver\s+se\s+"
        r"(?:a\s+(?:explicacao|resposta|informacao|ideia|mensagem)|o\s+argumento)"
        r"(?:\s+(?:ressoa|faz\s+sentido)\s+ou\s+se)?\s*",
        prefix,
    ) is not None and re.match(r"\s+(?:vag[oa]|clar[oa]|confus[oa]|incomplet[oa]|ambigu[oa])\b", complement) is not None

def _is_npc_observer_coordinate_action(
    value: str, action_match: re.Match[str], *, concept: str, player_aliases: Iterable[str],
) -> bool:
    """Resolve an object in 'Mara observa voce, ...', one action at a time.

    Immediate coordination, the bounded arms-crossed posture and a holding
    NPC's deliberation keep their subject. This does not realize an infinitive;
    relatives, coercion and a later player remain checked.
    """
    if concept in {"choice", "social", "combat", "consume"}:
        return False
    players = {"voce", "eu", "jogador", "personagem", *_normalized_aliases(player_aliases)}
    player_pattern = "|".join(re.escape(alias) for alias in sorted(players, key=len, reverse=True))
    protected_reference = (
        rf"\b(?:{player_pattern}|mim|lhe|te|ti|teu|tua|teus|tuas|seu|sua|seus|suas|que|obrig\w*|forc\w*|mand\w*)\b"
    )
    prefix = value[:action_match.start()]
    complement = value[action_match.end():]
    if concept == "wait" and _observer_wait_predicate(
        value, action_match, protected_reference=protected_reference,
    ):
        return True
    if not re.fullmatch(r"\s*,\s*(?:cruza\s+os\s+bracos\s+e\s+)?", prefix):
        # A bounded nominal object and an explicit deliberation predicate
        # preserve the known NPC as subject of the following infinitive.
        # Never extend this attribution through a player/relative/coercion cue.
        if (
            concept != "take"
            or not re.fullmatch(
                r"\s*,\s*segura\s+(?:o|a|um|uma)\s+[a-z]+(?:\s+[a-z]+){0,3}"
                r"\s+e\s+parece\s+indecis[oa]\s+sobre\s+", prefix,
            )
            or not (
                re.fullmatch(r"[a-z]+[aei]r", action_match.group())
                or (
                    re.fullmatch(r"[a-z]+[aei]", action_match.group())
                    and re.match(r"[-\u2010\u2011]l[oa]s?\b", complement)
                )
            )
            or re.search(protected_reference, prefix)
        ):
            return False
    complement = re.sub(rf"\s+por\s+(?:{player_pattern})\s*$", "", complement)
    return re.search(protected_reference, complement) is None


def _mask_known_npc_gaze_report(
    value: str, *, player_aliases: Iterable[str], npc_aliases: Iterable[str],
) -> str:
    """Exclude only a proven NPC's reporting/contact verb, never quoted content.

    In 'Mara ergue os olhos para voce e fala em voz baixa:', 'voce' is
    the gaze object. An unresolved pronoun or any different coordination
    remains conservative. Offsets and every other action stay unchanged.
    """
    players = {"voce", "eu", "personagem", "jogador", "jogadora", "o jogador", "a jogadora",
               "seu personagem", "sua personagem", "o personagem", "a personagem",
               *_normalized_aliases(player_aliases)}
    npcs = set(_normalized_aliases(npc_aliases)) - players
    narration = _observer_narration_without_speech(value)
    if not npcs or narration is None:
        return value
    names = "|".join(re.escape(name) for name in sorted(npcs, key=len, reverse=True))
    objects = "|".join(re.escape(name) for name in sorted(players, key=len, reverse=True))
    gaze = re.compile(
        rf"(?:^|(?<=[.!?;:]))\s*(?:(?:a|o)\s+)?(?P<actor>{names}|ele|ela)\s+"
        rf"(?:ergue|levanta)\s+os\s+olhos\s+para\s+(?:{objects})\s+e\s+"
        r"(?P<report>fala)\s+em\s+voz\s+(?:baixa|suave|firme)\s*:"
    )
    # A non-personal object state can intervene only in this bounded frame.
    # A mention, unknown actor, dialogue or player subject cannot own 'ela'.
    antecedent = re.compile(
        rf"(?:(?:a|o)\s+)?(?P<owner>{names})\s+se\s+inclina\s+sobre\s+a\s+bancada"
        r"(?:\s+baixa)?\s*,\s*sem\s+tocar\s+no\s+"
        r"(?P<object>registro|documento|livro|papel)\s*;\s*o\s+(?P=object)\s+"
        r"permanece\s+seco(?:\s*,\s*ainda\s+no\s+mesmo\s+lugar)?"
    )
    masked = list(value)
    npc_no_contact = re.compile(
        rf"(?:^|(?<=[.!?;:]))\s*(?:{names}) acompanha o avanco da agua "
        rf"e volta-se para (?:{objects}), tensa, sem (?P<contact>tocar) no objeto[.!?]"
    )
    for match in npc_no_contact.finditer(narration):
        start, end = match.span('contact')
        masked[start:end] = [' '] * (end - start)
    for match in gaze.finditer(narration):
        if match.group('actor') not in npcs:
            previous = [part.strip() for part in re.split(r'[.!?:]', narration[:match.start()])
                        if part.strip()]
            proof = antecedent.fullmatch(previous[-1]) if previous else None
            if proof is None and previous:
                # A named NPC observing object moisture can own the next
                # pronoun gaze/report; no player, relative or quoted actor.
                proof = re.fullmatch(
                    rf"(?:(?:a|o)\s+)?(?P<owner>{names})\s+acompanha\s+as\s+"
                    r"marcas\s+de\s+umidade\s+sem\s+tocar\s+no\s+objeto",
                    previous[-1],
                )
            if (proof is None
                    or _last_alias_position(previous[-1], tuple(players)) >= 0
                    or {npc for npc in npcs if _last_alias_position(previous[-1], (npc,)) >= 0}
                    != {proof.group('owner')}):
                continue
        start, end = match.span('report')
        masked[start:end] = [' '] * (end - start)
    return ''.join(masked)


def _validate_declared_player_actions(
    proposal: SceneContinuationProposal,
    *,
    authorized_actions: Mapping[
        tuple[str, str], tuple[tuple[str, ...], ...]
    ],
    player_aliases: Iterable[str] = (),
    npc_aliases: Iterable[str] = (),
) -> None:
    assertion_fields = (
        ("narrative", proposal.narrative),
        ("scene_summary", proposal.scene_summary),
        *(
            (f"open_threads[{index}]", value)
            for index, value in enumerate(proposal.open_threads)
        ),
        *(
            (f"resolved_threads[{index}]", value)
            for index, value in enumerate(proposal.resolved_threads)
        ),
        *(
            (f"new_facts[{index}].summary", fact.summary)
            for index, fact in enumerate(proposal.new_facts)
            if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}
        ),
    )
    normalized_player_aliases = _normalized_aliases(player_aliases)
    normalized_npc_aliases = _normalized_aliases(npc_aliases)
    player_subject_pattern = _subject_pattern(normalized_player_aliases)
    conditional_players = "|".join(re.escape(name) for name in sorted({
        "voce", "seu personagem", "sua personagem", "o personagem", "a personagem",
        "personagem", *normalized_player_aliases,
    }, key=len, reverse=True))
    conditional_actions = re.compile(
        rf"(?P<prefix>(?:^|[.!?;:\"“‘«'`])\s*(?:se|caso)\s+"
        rf"(?:{conditional_players})\s+(?:nao\s+)?)"
        r"(?P<action>explorar|explore|manipular|manipule|"
        r"observar|observe|examinar|examine)\b"
    )
    conditional_need_move = re.compile(
        rf"(?P<prefix>(?:^|[.!?;:\"“‘«'`])\s*(?:se|caso)\s+"
        rf"(?:{conditional_players})\s+(?:nao\s+)?precisar\s+)"
        r"(?P<action>move|manipula)(?P<clitic>[-\u2010\u2011]l[oa]s?)(?=\s*,)"
    )
    pending_player_decision = re.compile(
        rf"(?P<prefix>\bate\s+que\s+(?:{conditional_players})\s+)"
        r"(?P<action>decida)(?=\s+como\s+proceder\s*(?:[.!?;:,\"”’»'`]|$))"
    )
    future_player_decision = re.compile(
        rf"(?P<prefix>\bao\s+que\s+(?:{conditional_players})\s+)"
        r"(?P<action>decidir)(?=\s+fazer\s*(?:[.!?;:,\"”’»'`]|$))"
    )
    ongoing_player_deliberation = re.compile(
        rf"(?P<prefix>\benquanto\s+(?:{conditional_players})\s+)"
        r"(?P<action>decide)(?=\s+como\s+proceder\s*(?:[.!?;:,\"”’»'`]|$))"
    )
    conditional_player_decision = re.compile(
        rf"(?P<prefix>\bse\s+(?:{conditional_players})\s+)"
        r"(?P<action>decidir)(?=\s+(?:como\s+)?agir\s*(?:[.!?;:,\"”’»'`]|$))"
    )
    conditional_perception = re.compile(
        rf"(?P<prefix>(?:^|[.!?;:\"“‘«'`])\s*(?:se|caso)\s+"
        rf"(?:{conditional_players})\s+(?:nao\s+)?)"
        r"(?P<action>observar|observe|examinar|examine)\b"
        r"(?P<middle>[^.!?;:]*)\b(?P<consequence>vera|percebera|notara)\b"
    )
    hypothetical_interest_advice = re.compile(
        rf"(?:^|[.!?;:\"“‘«'`])\s*(?:mas\s+)?se\s+houver\s+algo(?:\s+especifico)?\s+que\s+"
        rf"(?:{conditional_players})\s+(?P<interest>procura)\b,\s*"
        r"talvez\s+seja\s+melhor\s+(?P<advice>seguir)\b"
    )
    dependent_interest = re.compile(
        rf"\bdependendo\s+do\s+que\s+(?:{conditional_players})\s+"
        r"(?P<dependent_interest>procura)\b"
        r"(?=\s*(?:[.!?;:\"”’»'`]|$))"
    )

    def mask_hypothetical_actions(match: re.Match[str]) -> str:
        # A hypothetical interest and a modal recommendation execute no action.
        # Preserve subjects/offsets and every other verb, including those in
        # the same quotation or a later coordinated clause.
        masked = list(match.group())
        for group in ("interest", "advice", "dependent_interest"):
            if match.groupdict().get(group) is None:
                continue
            start, end = match.start(group) - match.start(), match.end(group) - match.start()
            masked[start:end] = [" "] * (end - start)
        return "".join(masked)

    def mask_conditional_perception(match: re.Match[str]) -> str:
        masked = list(match.group())
        for group in ("action", "consequence"):
            start, end = match.start(group) - match.start(), match.end(group) - match.start()
            masked[start:end] = [" "] * (end - start)
        return "".join(masked)

    for field_name, field_value in assertion_fields:
        # Mask only this hypothetical verb, retaining subjects, offsets and
        # every later action. A condition never grants action authorization.
        normalized = conditional_perception.sub(
            mask_conditional_perception,
            _mask_quoted_player_preference_questions(
                _normalize_for_policy(field_value)
            ),
        )
        normalized = conditional_actions.sub(
            lambda match: match.group("prefix") + " " * len(match.group("action")),
            normalized,
        )
        normalized = hypothetical_interest_advice.sub(mask_hypothetical_actions, normalized)
        normalized = dependent_interest.sub(mask_hypothetical_actions, normalized)
        # Clitic move-lo/manipula-lo after conditional need asserts no action.
        # Keep later actions and all offsets.
        normalized = conditional_need_move.sub(
            lambda match: match.group('prefix') + ' ' * len(match.group('action'))
            + match.group('clitic'), normalized,
        )
        # 'Until you decide how to proceed' keeps the choice pending.
        # Mask only this subjunctive, never a following action or decision.
        normalized = pending_player_decision.sub(
            lambda match: match.group('prefix') + ' ' * len(match.group('action')),
            normalized,
        )
        normalized = future_player_decision.sub(
            lambda match: match.group('prefix') + ' ' * len(match.group('action')),
            normalized,
        )
        # Deliberation without a chosen action keeps the player's choice open.
        # Concrete choices or subsequent verbs do not match this narrow frame.
        normalized = ongoing_player_deliberation.sub(
            lambda match: match.group('prefix') + ' ' * len(match.group('action')),
            normalized,
        )
        # 'If you decide to act' is conditional, not an asserted choice.
        # Only this open-ended decision verb is masked, not a later action.
        normalized = conditional_player_decision.sub(
            lambda match: match.group('prefix') + ' ' * len(match.group('action')),
            normalized,
        )
        normalized = _mask_known_npc_gaze_report(
            normalized, player_aliases=normalized_player_aliases,
            npc_aliases=normalized_npc_aliases,
        )
        # An untargeted declared wait may mention the exact current place.
        # Mask only that grounded adjunct, never a destination or later verb.
        if () in authorized_actions.get(("wait", "explicit_wait_equivalent"), ()):
            current_place = _normalize_for_policy(proposal.location)
            if current_place:
                grounded_wait = re.compile(
                    r"\bvoce\s+(?:espera|aguarda)\s+"
                    rf"(?P<place>(?:no|na)\s+{re.escape(current_place)})"
                    r"(?=\s*(?:[.!?;:,]|$)|\s+enquanto\b)"
                )
                normalized = grounded_wait.sub(
                    lambda match: match.group()[:match.start('place')-match.start()]
                    + ' ' * len(match.group('place')), normalized,
                )
        for clause_index, match in enumerate(
            _PLAYER_SUBJECT_CLAUSE.finditer(normalized)
        ):
            unauthorized = _unauthorized_action_concepts(
                match.group("clause"),
                authorized_actions=authorized_actions,
                player_aliases=normalized_player_aliases,
                npc_aliases=normalized_npc_aliases,
                npc_observer_object=_known_npc_observes_player_object(
                    normalized[:match.start()], player_aliases=normalized_player_aliases,
                    npc_aliases=normalized_npc_aliases,
                ),
            )
            if unauthorized:
                raise SceneProposalError(
                    "scene_player_agency_violation",
                    evidence={
                        "field": field_name,
                        "rule": "undeclared_player_action",
                        "subject": match.group("subject"),
                        "clause_index": clause_index,
                        "unauthorized_concepts": unauthorized,
                    },
                )
        if player_subject_pattern is not None:
            for clause_index, match in enumerate(
                player_subject_pattern.finditer(normalized)
            ):
                prefix_words = re.findall(r"[a-z0-9]+", normalized[: match.start()])
                if prefix_words and prefix_words[-1] in {
                    "a",
                    "ao",
                    "com",
                    "da",
                    "de",
                    "do",
                    "para",
                    "por",
                }:
                    continue
                clause = match.group(1)
                unauthorized = _unauthorized_action_concepts(
                    clause,
                    authorized_actions=authorized_actions,
                    player_aliases=normalized_player_aliases,
                    npc_aliases=normalized_npc_aliases,
                    npc_observer_object=_known_npc_observes_player_object(
                        normalized[:match.start()], player_aliases=normalized_player_aliases,
                        npc_aliases=normalized_npc_aliases,
                    ),
                )
                if unauthorized:
                    raise SceneProposalError(
                        "scene_player_agency_violation",
                        evidence={
                            "field": field_name,
                            "rule": "undeclared_player_action",
                            "subject": "player_alias",
                            "clause_index": clause_index,
                            "unauthorized_concepts": unauthorized,
                        },
                    )
        _validate_pronoun_actions(
            normalized,
            field_name=field_name,
            authorized_actions=authorized_actions,
            player_aliases=normalized_player_aliases,
            npc_aliases=normalized_npc_aliases,
        )


def _implicit_opening_history_concepts(
    summary: str, *, npc_aliases: Iterable[str] = (),
) -> frozenset[str]:
    """Catch bounded subjectless bootstrap claims, not arbitrary waking imagery.

    Compact summaries often omit the player subject. Only an initial nominal
    waking+location or memory-loss assertion is treated this way; named owners,
    lore, quotations, negations and hypotheses do not match these openings.
    """
    normalized = _normalize_for_policy(summary).strip()
    first_clause = re.split(r"[.!?;]", normalized)[0]
    if re.search(
        r"\b(?:nao|nunca|jamais)\s+(?:ocorreu|aconteceu|houve)\b|"
        r"\b(?:seria|poderia)\b|"
        r"\b(?:e|era)\s+(?:(?:o|um)\s+)?(?:titulo|nome|relato)\b",
        first_clause,
    ):
        return frozenset()
    for alias in _normalized_aliases(npc_aliases):
        if re.search(
            rf"\b(?:afeta|acomete)\s+(?:(?:apenas|somente)\s+)?{re.escape(alias)}\b",
            first_clause,
        ):
            return frozenset()
    waking = bool(re.match(
        r"^(?:(?:o|um)\s+)?(?:despertar|acordar)\s+"
        r"(?:em|no|na|nos|nas|num|numa)\b", normalized,
    ))
    memory_start = bool(re.match(
        r"^(?:amnesia(?=\s+(?:em|no|na|nos|nas|num|numa)\b|[,;.]|$)|"
        r"(?:sem\s+memoria|nenhuma\s+lembranca)\s+"
        r"(?:(?:da|de)\s+)?(?:chegada|como\s+cheg\w*))\b", normalized,
    ))
    concepts = {"wake"} if waking else set()
    if memory_start or (waking and re.search(
        r"\b(?:sem\s+memoria|nenhuma\s+lembranca|com\s+amnesia)\b", normalized,
    )):
        concepts.add("memory_loss")
    return frozenset(concepts)


def _declared_opening_history_concepts(player_input: str) -> frozenset[str]:
    """Require affirmative first-person grounding, not a mentioned action verb."""
    normalized = _normalize_for_policy(player_input)
    # Quoted dialogue/lore is not a declaration of the player's past. Discard
    # unclosed quotes too, conservatively, rather than attributing their content.
    normalized = re.sub(r'["“`][^"”`]*(?:["”`]|$)', "", normalized)
    concepts: set[str] = set()
    for match in re.finditer(r"([^.!?;\n]+)([.!?;\n]|$)", normalized):
        clause = match.group(1).strip()
        if match.group(2) == "?" or re.search(r"\b(?:se|caso|talvez)\b", clause):
            continue
        waking = bool(re.match(r"^(?:eu\s+)?(?:acordei|despertei|acordo|desperto)\b", clause))
        if waking:
            concepts.add("wake")
        # An adjacent NPC's memory loss must not become player grounding.
        self_subject = False
        for fragment in re.split(r",|\b(?:e|mas|enquanto|quando)\b", clause):
            fragment = fragment.strip()
            self_state = bool(re.match(
                r"^(?:eu\s+)?(?:acordei|despertei|acordo|desperto|estou)\b",
                fragment,
            ))
            absent_memory = bool(re.match(
                r"^(?:eu\s+)?(?:nao\s+me\s+lembro|nao\s+tenho\s+memoria)\b",
                fragment,
            ))
            memory_adjunct = self_subject and bool(re.match(
                r"^(?:sem\s+memoria|nenhuma\s+lembranca)\b", fragment,
            ))
            direct_memory_state = bool(re.match(
                r"^(?:eu\s+)?(?:tenho\s+amnesia|estou\s+(?:sem\s+memoria|com\s+amnesia))\b",
                fragment,
            ))
            waking_with_memory_loss = bool(re.match(
                r"^(?:eu\s+)?(?:acordei|despertei|acordo|desperto)\b", fragment,
            )) and bool(re.search(
                r"\b(?:sem\s+memoria|nenhuma\s+lembranca|com\s+amnesia)\b", fragment,
            ))
            if absent_memory or memory_adjunct or direct_memory_state or waking_with_memory_loss:
                concepts.add("memory_loss")
            self_subject = self_state or direct_memory_state or memory_adjunct or absent_memory
    return frozenset(concepts)


def _validate_implicit_opening_history(
    summary: str, player_input: str, *, npc_aliases: Iterable[str] = (),
) -> None:
    proposed = _implicit_opening_history_concepts(summary, npc_aliases=npc_aliases)
    if not proposed:
        return
    ungrounded = proposed - _declared_opening_history_concepts(player_input)
    if ungrounded:
        raise SceneProposalError(
            "scene_player_agency_violation",
            evidence={
                "field": "scene_summary",
                "rule": "unestablished_opening_history",
                "history_concepts": sorted(ungrounded),
            },
        )


def _present_nominal_passive_is_negated(value: str, match: re.Match, prefix: str) -> bool:
    """Recognize a local negative subject, not normalized conjunction 'e'.

    'Nenhum indício é encontrado' negates that achievement. Restrict this to
    participles and a short nominal subject; 'vê nenhum indício e encontra a
    prova' or a new subject after the participle must not inherit the negation.
    """
    if not re.fullmatch(r"(?:[a-z]+(?:ad[oa]s?|id[oa]s?)|descobert[oa]s?)", match.group()):
        return False
    if not re.search(
        r"(?:^|,)\s*(?:nenhum|nenhuma|nenhuns|nenhumas)\s+(?!e\b|ou\b|mas\b)[a-z][a-z0-9]*"
        r"(?:\s+nov[oa]s?)?\s+(?:e|sao)\s*$", prefix,
    ):
        return False
    # A second noun phrase can be the affirmative passive's actual subject:
    # '... é encontrado o registro'. Do not waive such an ambiguous clause.
    return not re.match(
        r"\s+(?:a|o|as|os|um|uma|uns|umas|nenhu\w*|voce|ele|ela)\b",
        value[match.end():],
    )


def _affirmative_goal_matches(value: str):
    """Yield local affirmative achievements, not negated/failed attempts."""

    for match in _FAILURE_GOAL_GRANT.finditer(value):
        # Water reaching the bench and wetting the record is damage, not a
        # player's achieved objective. Leave every later result visible.
        if (match.group() == "alcanca"
                and re.search(r"(?:^|[.])\s*a\s+agua\s+$", value[:match.start()])
                and re.match(r"\s+a\s+bancada\s+baixa\s+no\s+arquivo\s+e\s+molha\s+as\s+paginas\s+do\s+registro\s*(?:[.!?;:,]|$)", value[match.end():])):
            continue
        clause_start = max(
            value.rfind(separator, 0, match.start())
            for separator in (".", "!", "?", ";", ":")
        )
        prefix = value[clause_start + 1 : match.start()]
        active_prefix = re.split(
            r"\b(?:mas|porem|contudo|entretanto|ainda\s+assim)\b",
            prefix,
        )[-1]
        if _IMMEDIATE_NEGATION_PREFIX.search(active_prefix):
            continue
        # 'Nada cede' negates this predicate, but 'do nada encontra' does not.
        # Require a local subject boundary, not merely the token 'nada'.
        if _LOCAL_NOTHING_SUBJECT_PREFIX.search(active_prefix):
            continue
        if _NEGATED_GOAL_PREFIX.search(active_prefix):
            continue
        if _PASSIVE_NEGATED_GOAL_PREFIX.search(active_prefix):
            continue
        if _present_nominal_passive_is_negated(value, match, active_prefix):
            continue
        # Water reaching document pages is a damaging environmental effect,
        # not the player's achievement. Later affirmative grants still count.
        if (match.group() == "alcanca"
                and re.search(r"(?:^|,)\s*a\s+(?:umidade|agua)\s*$", active_prefix)
                and re.match(r"\s+as\s+paginas(?=\s*(?:[.!?;:,]|$)|\s+e\b)", value[match.end():])):
            continue
        # This new recovery marker requires an explicit affirmative player
        # subject. Conditions, wishes and attempts cannot substantiate it.
        if (re.fullmatch(r"recuper(?:a|ou)\s+(?:informacao\s+util|informacoes\s+uteis|parte\s+da\s+informacao)", match.group())
                and not re.search(
                    r"(?:^|,)\s*(?:[”»]\s*)?voce"
                    r"(?:\s+examina o registro (?:na|sobre a) bancada baixa do arquivo e)?\s*$",
                    active_prefix)):
            continue
        # This discovery is still a goal under time pressure, not a result.
        # Skip only its infinitive; a later affirmative discovery still counts.
        if (
            match.group() == "descobrir"
            and re.search(r"\bo\s+tempo\s+para\s*$", active_prefix)
            and re.match(
                r"\s+(?:a|o|as|os)\s+[a-z0-9]+(?:\s+[a-z0-9]+){0,6}\s+"
                r"esta\s+se\s+esgotando\b(?=\s*(?:[.!?;:,]|$)|\s+e\b)",
                value[match.end():],
            )
        ):
            continue
        # An infinitive names the attempted goal, not its achievement:
        # "Tentativa de abrir o cadeado falha". Require a local affirmative
        # failure predicate; a later contrasting grant is checked separately.
        if re.search(r"\btentativa\s+de\s*$", active_prefix):
            suffix = re.split(
                r"[.!?;:,]|\b(?:mas|porem|contudo|entretanto)\b",
                value[match.end():], maxsplit=1,
            )[0]
            failure = re.match(
                r"(?P<target>(?:\s+[a-z0-9]+){0,8})\s+"
                r"(?:falha|falhou|fracassa|fracassou)\b", suffix,
            )
            if failure and not re.search(
                r"\b(?:nao|nunca|jamais|sem|se|caso|talvez)\b", failure["target"],
            ):
                continue
        yield match


def _mechanical_targets(player_input: str) -> frozenset[str]:
    return frozenset(
        token for targets in _action_authorizations(player_input).values()
        for target in targets for token in target
    )


def _unrelated_visual_reaction(
    value: str, match: re.Match, *, player_input: str, current_scene: SceneState | None,
) -> bool:
    """Disambiguate a bounded visual predicate, never waive a whole sentence.

    A light exposing anonymous shapes is not opening a lock. Identity, evidence,
    possessions, other coordinated objects, and goal-related shapes are not
    covered. With no declared target we retain the conservative rejection.
    """
    targets = _mechanical_targets(player_input)
    if not targets or not re.fullmatch(r"revel(?:a|am|ou|aram|ando)", match.group()):
        return False
    start = max(value.rfind(mark, 0, match.start()) for mark in (".", "!", "?", ";", ":", "\n"))
    prefix = value[start + 1:match.start()].strip()
    if not re.match(r"^(?:a|o|as|os|uma?|umas?|uns?)\s+(?:luz|luzes|lanterna|lanternas|farol|farois|lampada|lampadas)\b", prefix):
        return False
    tail = re.split(r"[.!?;:\n]", value[match.end():], maxsplit=1)[0]
    # Full-match a generic appearance plus optional position/approach. A new
    # object after 'e', an identifying complement or an artifact fails closed.
    generic_appearance = re.fullmatch(
        r"\s*(?:(?:uma?|umas?|uns?|as?|os?)\s+)?"
        r"(?P<shape>silhuetas?|sombras?|vultos?|figuras?)"
        r"(?:\s+(?:junto\s+(?:a|ao|da|do)|perto\s+(?:da|do)|entre|na|no)\s+"
        r"(?:a\s+|o\s+|as\s+|os\s+)?(?:grade|entrada|vigas|corredor))?"
        r"(?:\s+que\s+(?:se\s+aproximam|avancam)(?:\s+com\s+passos\s+pesados)?)?\s*",
        tail,
    )
    if generic_appearance is None:
        return False
    goals = _normalize_for_policy(" ".join((
        player_input, *(current_scene.open_threads if current_scene else ()),
    )))
    if re.search(r"\b(?:quem|identidade|individuos?|pessoas?|silhuetas?|sombras?|vultos?|figuras?)\b", goals):
        return False
    return not (targets & _meaningful_policy_tokens(tail))


def _failure_goal_is_granted(
    value: str, *, player_input: str = "", current_scene: SceneState | None = None,
) -> bool:
    if _failed_barrier_is_open(value, player_input=player_input, current_scene=current_scene):
        return True
    return any(
        not _unrelated_visual_reaction(value, match, player_input=player_input, current_scene=current_scene)
        for match in _affirmative_goal_matches(value)
    )


_MECHANICAL_BARRIER = r"(?:cadeados?|grades?|portas?|portao|portoes|trancas?|fechaduras?)"
_BARRIER_OPEN_STATE = re.compile(
    rf"\b(?P<object>{_MECHANICAL_BARRIER}(?:\s+[a-z0-9]+){{0,3}}?)\s+"
    r"(?:esta|estao|ficou|ficaram|permanece|permanecem|segue|seguem)\s+"
    r"(?:(?:agora|finalmente|completamente)\s+)?abert[oa]s?\b"
)
_BARRIER_CLOSED_STATE = re.compile(
    rf"\b(?P<object>{_MECHANICAL_BARRIER}(?:\s+[a-z0-9]+){{0,3}}?)\s+"
    r"(?:fechad[oa]s?|trancad[oa]s?)\b"
)
_FAILURE_IMPASSABLE_BARRIER_STATE = re.compile(
    rf"\b(?P<object>{_MECHANICAL_BARRIER}(?:\s+[a-z0-9]+){{0,3}}?)\s+"
    r"(?:esta|estao|ficou|ficaram|permanece|permanecem|segue|seguem)\s+"
    r"(?:(?:agora|ainda|completamente)\s+)?intransponiv(?:el|eis)\b"
)
_BARRIER_STATE_AUXILIARIES = frozenset({
    "esta", "estao", "ficou", "ficaram", "permanece", "permanecem", "segue", "seguem",
})


def _failed_barrier_is_open(
    value: str, *, player_input: str, current_scene: SceneState | None,
) -> bool:
    """Catch present opening states only for a mechanically active barrier.

    An open mouth/window or another door is not a failed lock objective. A
    barrier is active when named by the action or explicitly closed in the
    existing scene. This checks direct assertions, not past/hypothetical states.
    """
    return _mechanically_active_barrier_has_state(
        value, state_pattern=_BARRIER_OPEN_STATE,
        player_input=player_input, current_scene=current_scene,
    )


def _mechanically_active_barrier_has_state(
    value: str, *, state_pattern: re.Pattern, player_input: str,
    current_scene: SceneState | None,
) -> bool:
    """Match a present assertion against a declared or canonically closed barrier."""
    def object_tokens(value: str) -> tuple[str, ...]:
        return tuple(
            token for token in re.findall(r"[a-z0-9]+", value)
            if token not in _ACTION_TARGET_STOPWORDS and token not in _BARRIER_STATE_AUXILIARIES
        )

    def is_current_assertion(clause: str, match: re.Match) -> bool:
        context = re.split(
            r"\b(?:mas|porem|contudo|entretanto)\b", clause[:match.end()],
        )[-1]
        temporal_context = re.split(r"\b(?:agora|hoje)\b", context)[-1]
        if re.search(r"\b(?:ontem|antes|anteriormente|antigamente|outrora)\b|\bno\s+passado\b", temporal_context):
            return False
        if re.search(
            r"\b(?:nao|nunca|jamais|talvez|provavelmente|possivelmente|"
            r"estava|estavam|era|eram|esteve|estiveram)\b", match["object"],
        ):
            return False
        if re.search(
            r"(?:^|,\s*)(?:se|caso|talvez)\b|"
            r"\b(?:ninguem|nao)\s+(?:se\s+)?sabe\b|"
            r"\bnao\s+(?:e|era|esta|foi)\s+(?:verdade|certo|claro|confirmado|estabelecido)\b|"
            r"\b(?:nao\s+ha|sem)\s+(?:confirmacao|certeza)\b",
            context,
        ):
            return False
        return True

    active = [
        target for targets in _action_authorizations(player_input).values() for target in targets
        if any(re.fullmatch(_MECHANICAL_BARRIER, token) for token in target)
    ]
    if current_scene is not None:
        for detail in (current_scene.summary, *current_scene.details):
            for clause in _narrative_assertive_clauses(detail):
                for match in _BARRIER_CLOSED_STATE.finditer(clause):
                    if is_current_assertion(clause, match):
                        active.append(object_tokens(match["object"]))
    if not active:
        return False
    for clause in _narrative_assertive_clauses(value):
        for match in state_pattern.finditer(clause):
            if is_current_assertion(clause, match) and _action_target_is_authorized(
                object_tokens(match["object"]), tuple(active),
            ):
                return True
    return False


_CLUE_RELATIONAL_WORDS = frozenset({
    "ate", "segue", "seguem", "escorre", "escorrem", "conduz", "conduzem",
    "atravessa", "atravessam", "surge", "surgem", "aparece", "aparecem",
    "esta", "estao", "existe", "existem", "fica", "ficam",
})
_GENERIC_CLUE_WORDS = frozenset({
    "pista", "indicio", "evidencia", "descoberta", "nova", "novo", "concreta",
    "concreto", "relevante", "interessante", "importante", "util",
})


def _narrative_assertive_clauses(value: str) -> tuple[str, ...]:
    # Reported dialogue and a question are not narrator confirmation of a roll.
    normalized = _normalize_for_policy(value)
    normalized = re.sub(r'["“«`][^"”»`]*(?:["”»`]|$)', "", normalized)
    return tuple(
        match[1].strip()
        for match in re.finditer(r"([^.!?;\n]+)([.!?;\n]|$)", normalized)
        if match[2] != "?" and match[1].strip()
    )


def _clue_content_tokens(value: str) -> frozenset[str]:
    # Short counts/IDs matter even though ordinary policy stopword extraction
    # drops short tokens. A clue describing 2 traces is not evidence for 3.
    return (_meaningful_policy_tokens(value) | frozenset(re.findall(r"\b\d+\b", value))) - _CLUE_RELATIONAL_WORDS


def _clue_content_order_is_preserved(clue: str, sentence: str) -> bool:
    content = _clue_content_tokens(clue)
    expected = (word for word in re.findall(r"[a-z0-9]+", _normalize_for_policy(clue)) if word in content)
    actual = iter(re.findall(r"[a-z0-9]+", sentence))
    # Ordered corroboration, not bag-of-words: reversing endpoints or actors
    # does not describe the same discovery even when every noun is present.
    return all(any(candidate == word for candidate in actual) for word in expected)


def _investigation_clue_is_grounded(
    proposal: SceneContinuationProposal, *, player_input: str, current_scene: SceneState | None,
) -> bool:
    actions = _action_authorizations(player_input)
    targets = tuple(
        value for (concept, _), values in actions.items() if concept == "inspect"
        for value in values if value
    )
    if not targets:
        return False
    place = current_scene.location if current_scene else proposal.location
    place_tokens = tuple(
        token for token in re.findall(r"[a-z0-9]+", _normalize_for_policy(place))
        if token in _meaningful_policy_tokens(place)
    )
    # Inspecting the lock *of the warehouse* is not inspecting the whole area.
    # Keep the head of each declared object, not every shared place/adjective.
    target_heads = frozenset(target[0] for target in targets)
    area_investigation = bool(place_tokens and place_tokens[0] in target_heads)
    prior_details = tuple(
        _clue_content_tokens(detail) for detail in (current_scene.details if current_scene else ())
    )
    for fact in proposal.new_facts:
        if fact.kind is not SceneFactKind.CLUE or fact.visibility not in {Visibility.PLAYER, Visibility.PUBLIC}:
            continue
        tokens = _clue_content_tokens(fact.summary)
        if len(tokens - _GENERIC_CLUE_WORDS) < 3 or (not area_investigation and not target_heads & tokens):
            continue
        if any(tokens <= known for known in prior_details):
            continue
        for sentence in _narrative_assertive_clauses(proposal.narrative):
            if re.search(r"\b(?:nao|nenhum\w*|nada|sem|talvez|poderia|caso|se)\b", sentence):
                continue
            # Do not use a similarity threshold here: many shared adjectives
            # must not hide a changed substance, actor, number or qualifier.
            if tokens <= _clue_content_tokens(sentence) and _clue_content_order_is_preserved(fact.summary, sentence):
                return True
    return False


def validate_mechanical_narrative(
    narrative: str, *, outcome: str, proposal: SceneContinuationProposal | None = None,
    player_input: str = "", current_scene: SceneState | None = None,
) -> None:
    """Shared mechanical checks for synthetic evaluation and turn execution.

    Only assertions can substantiate a result; questions and open tasks cannot.
    Structured clues supplement lexical markers for declared investigations.
    These are bounded local checks, not a general semantic proof of prose.
    """
    if proposal is not None and proposal.outcome != outcome:
        raise SceneProposalError("scene_outcome_mismatch")
    text = ". ".join(_narrative_assertive_clauses(narrative))
    if outcome == "success":
        explicit_failure = re.search(
            r"\b(?:investigacao|busca|tentativa|acao|esforco|voce)\s+(?:falh\w*|fracass\w*)\b|"
            r"\bnao\s+(?:teve|obteve|alcancou|atingiu)\s+sucesso\b", text,
        )
        grounded = proposal is not None and _investigation_clue_is_grounded(
            proposal, player_input=player_input, current_scene=current_scene,
        )
        positive_result = any(
            not _unrelated_visual_reaction(text, match, player_input=player_input, current_scene=current_scene)
            for match in _affirmative_goal_matches(text)
        )
        if explicit_failure or not (positive_result or grounded):
            raise SceneProposalError("scene_success_not_honored")
    if outcome != "failure":
        return
    if not _FAILURE_MARKER.search(text) and not _mechanically_active_barrier_has_state(
        text, state_pattern=_FAILURE_IMPASSABLE_BARRIER_STATE,
        player_input=player_input, current_scene=current_scene,
    ):
        raise SceneProposalError("scene_failure_not_honored")
    if proposal is not None:
        for fact in proposal.new_facts:
            if fact.kind in {SceneFactKind.OBSERVATION, SceneFactKind.CLUE} and not fact.pending:
                code = "scene_failure_granted_conclusive_clue" if fact.kind is SceneFactKind.CLUE else "scene_failure_granted_conclusive_observation"
                raise SceneProposalError(code)
    assertions = _player_visible_scene_assertions(proposal) if proposal else (narrative,)
    for assertion in assertions:
        normalized = _normalize_for_policy(assertion)
        # An explicit environment carrying tension grants no player possession.
        # Scan every other match, including later possession in the same text.
        possession_granted = any(
            not (match.group() == "carrega"
                 and re.search(r"\be\s+o\s+ambiente\s+agora\s+$", normalized[:match.start()])
                 and re.match(r"\s+uma\s+tensao\s+evidente\s*(?:[.!?;:,]|$)", normalized[match.end():]))
            for match in _FAILURE_POSSESSION_GRANT.finditer(normalized)
        )
        if _failure_goal_is_granted(normalized, player_input=player_input, current_scene=current_scene) or possession_granted:
            raise SceneProposalError("scene_failure_granted_goal")


def _thread_resolution_is_grounded(thread: str, evidence: str) -> bool:
    normalized_evidence = _normalize_for_policy(evidence)
    if _THREAD_UNRESOLVED_MARKER.search(normalized_evidence):
        return False
    if not _THREAD_RESOLUTION_MARKER.search(normalized_evidence):
        return False
    thread_tokens = _meaningful_policy_tokens(thread)
    shared = thread_tokens & _meaningful_policy_tokens(normalized_evidence)
    return bool(thread_tokens) and bool(shared)


def _normalized_aliases(values: Iterable[str]) -> tuple[str, ...]:
    aliases: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_for_policy(value)
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        aliases.append(normalized)
    return tuple(aliases)


def _subject_pattern(aliases: tuple[str, ...]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    subjects = "|".join(
        sorted((re.escape(value) for value in aliases), key=len, reverse=True)
    )
    return re.compile(rf"(?<!\w)(?:{subjects})(?!\w)([^.!?;:]*)")


def _last_alias_position(value: str, aliases: tuple[str, ...]) -> int:
    positions = (
        match.start()
        for alias in aliases
        for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", value)
    )
    return max(positions, default=-1)


def _first_alias_position(value: str, aliases: tuple[str, ...]) -> int:
    positions = (
        match.start()
        for alias in aliases
        for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", value)
    )
    return min(positions, default=-1)


def _named_actor_structure_names_player(
    value: str,
    player_aliases: tuple[str, ...],
) -> bool:
    """Return true only when the grammatical actor is a known player alias."""

    for alias in player_aliases:
        escaped = re.escape(alias)
        if re.search(
            rf"\b(?:faz|fara|age|agira|reage|reagira|responde|respondera|"
            rf"procede|procedera|pretende|decide|decidira|verifica|verificara|aborda|abordara)\s+{escaped}\b",
            value,
        ):
            return True
        if re.search(
            rf"^(?:o\s+que|como)\s+{escaped}\s+"
            rf"(?:faz|fara|age|agira|reage|reagira|responde|respondera|"
            rf"procede|procedera|pretende|decide|decidira|verifica|verificara|aborda|abordara)\b",
            value,
        ):
            return True
        if re.search(
            rf"^(?:que|qual)\s+[^?]{{0,50}}\b{escaped}\s+"
            rf"(?:escolhe|escolhera|prefere|decide|decidira)\b",
            value,
        ):
            return True
    return False


def _validate_pronoun_actions(
    value: str,
    *,
    field_name: str,
    authorized_actions: Mapping[
        tuple[str, str], tuple[tuple[str, ...], ...]
    ],
    player_aliases: tuple[str, ...],
    npc_aliases: tuple[str, ...],
) -> None:
    last_named_actor: str | None = None
    for clause_index, segment in enumerate(re.split(r"[.!?;:]", value)):
        segment = segment.strip()
        if not segment:
            continue
        player_position = _last_alias_position(segment, player_aliases)
        npc_position = _last_alias_position(segment, npc_aliases)
        pronoun_matches = re.finditer(r"\b(?:ele|ela)\b(.*)", segment)
        for match in pronoun_matches:
            prefix = segment[: match.start()]
            player_before = _last_alias_position(prefix, player_aliases)
            npc_before = _last_alias_position(prefix, npc_aliases)
            if npc_before > player_before:
                refers_to_npc = True
            elif player_before > npc_before:
                refers_to_npc = False
            else:
                refers_to_npc = last_named_actor == "npc"
            clause = match.group(1)
            unauthorized = _unauthorized_action_concepts(
                clause,
                authorized_actions=authorized_actions,
                player_aliases=player_aliases, npc_aliases=npc_aliases,
                antecedent_prefix=segment[:match.start(1)],
            )
            if not refers_to_npc and unauthorized:
                raise SceneProposalError(
                    "scene_player_agency_violation",
                    evidence={
                        "field": field_name,
                        "rule": "undeclared_player_action",
                        "subject": "ambiguous_pronoun",
                        "clause_index": clause_index,
                        "unauthorized_concepts": unauthorized,
                    },
                )
        if player_position > npc_position:
            last_named_actor = "player"
        elif npc_position > player_position:
            last_named_actor = "npc"


def _validate_implicit_player_contact(
    proposal: SceneContinuationProposal,
    *,
    authorized_actions: Mapping[tuple[str, str], tuple[tuple[str, ...], ...]],
    player_input: str = "",
    player_aliases: Iterable[str] = (),
) -> None:
    """Catch narrow body/force constructions that omit an explicit player subject.

    These patterns cover contact with objects and pressure applied to barriers,
    not generic body sensations, injury, or environmental collapse. They do not
    attempt to infer every possible implicit action from natural language.
    """

    fields = (
        ("narrative", proposal.narrative),
        ("scene_summary", proposal.scene_summary),
        *((f"open_threads[{i}]", value) for i, value in enumerate(proposal.open_threads)),
        *((f"resolved_threads[{i}]", value) for i, value in enumerate(proposal.resolved_threads)),
        *((f"new_facts[{i}].summary", fact.summary)
          for i, fact in enumerate(proposal.new_facts)
          if fact.visibility in {Visibility.PUBLIC, Visibility.PLAYER}),
    )
    hand_contact = re.compile(
        r"(?:^|[.!?;])\s*(?:seus\s+dedos|suas\s+maos)\s+"
        r"(?:escorregam|deslizam)\s+(?:no|na|nos|nas|sobre)\s+"
        r"(?P<target>[^.!?;:,]+)"
    )
    hand_removal = re.compile(
        r"(?:^|[.!?;])\s*(?:seus\s+dedos|suas\s+maos)\s+"
        r"arrancam\s+(?P<target>[^.!?;:,]+)"
    )
    hand_brush = re.compile(
        r"(?:^|[.!?;])\s*(?:seus\s+dedos|suas\s+maos)\s+"
        r"rocam\s+(?P<target>[^.!?;:,]+)"
    )
    barrier_force = re.compile(
        r"\b(?:cede|vibra)(?:\s+(?:apenas|fracamente|lentamente))?\s+"
        r"sob\s+(?:sua\s+forca|seu\s+peso)\b"
    )
    barrier_hand = re.compile(
        r"\b(?:range|vibra|cede)(?:\s+(?:apenas|fracamente|lentamente))?\s+"
        r"sob\s+(?:a\s+)?sua\s+mao\b"
    )
    barrier = re.compile(r"\b(?:cadeado|porta|portao|grade)\b")
    npc_names = _normalized_aliases(proposal.npcs_present)

    def target_tokens(value: str) -> tuple[str, ...]:
        boundary = _ACTION_TARGET_BOUNDARY.search(value)
        target = value[:boundary.start()] if boundary else value
        return tuple(dict.fromkeys(
            token for token in re.findall(r"[a-z0-9]+", target)
            if len(token) >= 3 and token not in _ACTION_TARGET_STOPWORDS
        ))

    def require_contact(field: str, target: tuple[str, ...], families: tuple[str, ...]) -> None:
        if any(
            (declared := authorized_actions.get(("interact", family))) is not None
            and _action_target_is_authorized(target, declared)
            for family in families
        ):
            return
        raise SceneProposalError(
            "scene_player_agency_violation",
            evidence={"field": field, "rule": "undeclared_player_contact",
                      "unauthorized_concepts": ["interact"]},
        )

    for field_name, field_value in fields:
        normalized = _normalize_for_policy(field_value)
        hand_matches = (
            *((match, ("touch", "push", "pull")) for match in hand_contact.finditer(normalized)),
            *((match, ("tear_off",)) for match in hand_removal.finditer(normalized)),
            *((match, ("brush",)) for match in hand_brush.finditer(normalized)),
        )
        for match, families in hand_matches:
            prefix = normalized[:match.start()]
            previous_clause = re.split(r"[.!?;]", prefix)[-1].strip()
            # A direct named-NPC subject in the preceding sentence owns its
            # possessive continuation; merely mentioning an NPC as object does
            # not make the player's hands that NPC's hands.
            if any(re.match(rf"^{re.escape(npc)}\s+\w+", previous_clause)
                   for npc in npc_names):
                continue
            require_contact(field_name, target_tokens(match.group("target")), families)
        barrier_matches = (
            *((match, ("push", "pull", "force")) for match in barrier_force.finditer(normalized)),
            *((match, ("touch", "push", "pull")) for match in barrier_hand.finditer(normalized)),
        )
        for match, families in barrier_matches:
            # Restrict force to a named barrier in this or the preceding short
            # clause. A floor collapsing beneath the player is not an action.
            prefix = normalized[:match.start()]
            sentence_start = max(prefix.rfind(separator) for separator in (".", "!", "?"))
            active_clause = prefix[sentence_start + 1:]
            if any(re.search(
                rf"\b{re.escape(npc)}\s+(?:empurra|puxa|pressiona|forca|toca)\b",
                active_clause,
            ) for npc in npc_names):
                continue
            candidates = tuple(barrier.finditer(active_clause))
            if not candidates:
                continue
            # A later environmental subject must not inherit an earlier
            # barrier's implied interaction ("a porta range e o chão cede").
            if re.search(r"\b(?:chao|piso|solo|pavimento)\b", active_clause[candidates[-1].end():]):
                continue
            require_contact(field_name, target_tokens(candidates[-1].group()), families)

    _validate_implicit_instrument_and_prompt_actions(
        proposal, fields=fields, authorized_actions=authorized_actions,
        player_input=player_input, player_aliases=player_aliases,
    )


def _declared_temporal_barrier_open_targets(player_input: str) -> tuple[tuple[str, ...], ...]:
    """Ground this implicit opening in a positive player declaration, not a mention."""
    normalized = _normalize_for_policy(player_input)
    unquoted = re.sub(r'["“‘«`\x27][^"”’»`\x27]*(?:["”’»`\x27]|$)', " ", normalized)
    unquoted = re.sub(r":[^\n]*|(?:^|\n)\s*[-—–][^\n]*", " ", unquoted)
    targets = []
    for statement in re.finditer(r"([^.!?;\n]*)([.!?;\n]|$)", unquoted):
        sentence = statement.group(1)
        # Keep a question's terminator and suffix conditions: neither an
        # option nor a conditional opening is a selected, performed action.
        if statement.group(2) == "?" or re.search(
            r"\b(?:se|caso|quando|talvez|ou)\b", sentence,
        ):
            continue
        clauses = re.split(r"\s+(?:e|mas)\s+", sentence)
        player_coordination = bool(re.match(
            r"^\s*(?:eu\s+)?(?:nao\s+)?"
            r"(?:observo|investigo|examino|olho|escuto|ouco|espero|aguardo|abro|vou|tento|abrir)\b",
            clauses[0],
        ))
        for index, clause in enumerate(clauses):
            # Do not extract a player declaration from an embedded denial or
            # NPC statement merely because a later coordinated verb is abro.
            if index and not player_coordination:
                continue
            declaration = re.match(
                r"^\s*(?:eu\s+)?(?:(?:vou|tento)\s+)?(?:tentar\s+)?"
                r"(?:abro|abrir)\b", clause,
            )
            if declaration is None or not re.match(
                r"\s+(?:a|o|as|os)\s+"
                r"(?:cadeados?|portas?|portoes|portao|grades?|trancas?)\b",
                clause[declaration.end():],
            ):
                if index:
                    player_coordination = False
                continue
            targets.append(_action_target_tokens(clause, declaration))
    return tuple(targets)


def _validate_implicit_instrument_and_prompt_actions(
    proposal: SceneContinuationProposal,
    *,
    fields: tuple[tuple[str, str], ...],
    authorized_actions: Mapping[tuple[str, str], tuple[tuple[str, ...], ...]],
    player_input: str = "",
    player_aliases: Iterable[str] = (),
) -> None:
    """Check bounded tool-use claims and presuppositions, not every infinitive.

    ``Ao mover a lanterna`` presents a performed action, unlike a conditional
    invitation. Only a small instrumental construction is recognized without
    a named subject. NPC/environment owners are kept distinct. In the player
    question, temporal action complements presuppose a choice already made;
    perception, nominal events and prospective invitations do not.
    """

    npc_names = _normalized_aliases(proposal.npcs_present)
    instrumental = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?P<action>mover|acender|apagar)\s+"
        r"(?:a|o|as|os|sua|seu)\s+"
        r"(?:lanterna|espelho|lupa|binoculos|camera)\b[^.!?;:,]*,"
    )
    barrier_attempt = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?:tentar\s+)?(?P<action>forcar)\s+"
        r"(?:a|o|as|os)\s+(?:cadeados?|portas?|portoes|portao|grades?|trancas?)"
        r"\b[^.!?;:,]*,"
    )
    barrier_contact = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?:tentar\s+)?(?P<action>tocar)\s+"
        r"(?:a|o|as|os)\s+(?:cadeados?|portas?|portoes|portao|grades?|trancas?)"
        r"\b[^.!?;:,]*,"
    )
    barrier_open = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?:tentar\s+)?(?P<action>abrir)\s+"
        r"(?:a|o|as|os)\s+(?:cadeados?|portas?|portoes|portao|grades?|trancas?)"
        r"\b[^.!?;:,]*,"
    )
    # The following explicit player owns this search. Do not infer a player
    # from an NPC/ambiguous continuation or generalize to every infinitive.
    temporal_search = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?P<action>vasculhar)\b[^.!?;:,]*,"
        r"(?=\s*(?:voce|(?:seu|sua|o|a)\s+personagem)\b)"
    )
    # Bind a nominal failed opening to the immediately preceding player
    # inspection of a barrier's mechanism. Perceiving an NPC attempt does not
    # establish the player as its actor, so keep this context explicit.
    inspected_player_barrier = re.compile(
        rf"(?:^|[.!?;])\s*ao\s+(?:examinar|investigar|observar)\s+"
        rf"(?P<target>(?:a|o|as|os)\s+{_MECHANICAL_BARRIER}(?:\s+[a-z0-9]+){{0,3}}),\s*"
        r"(?:voce|(?:seu|sua|o|a)\s+personagem)\s+(?:percebe|nota|observa)\s+"
        r"que\s+o\s+mecanismo\s+(?:esta|permanece)\s+"
        r"(?:corroid[oa]|travad[oa]|enferrujad[oa]|fechad[oa]|danificad[oa])"
        r"(?:\s+e\s+(?:corroid[oa]|travad[oa]|enferrujad[oa]|fechad[oa]|danificad[oa]))*\s*$"
    )
    nominal_open_attempt = re.compile(
        r"(?:^|[.!?;])\s*a\s+tentativa\s+de\s+abrir"
        rf"(?P<target>(?:\s+(?:a|o|as|os)\s+{_MECHANICAL_BARRIER}(?:\s+[a-z0-9]+){{0,3}})?)"
        r"\s+(?:falha|falhou|fracassa|fracassou)\b"
    )
    opening_targets = _declared_temporal_barrier_open_targets(player_input)
    barrier_push = re.compile(
        r"(?:^|[.!?;])\s*ao\s+(?:tentar\s+)?(?P<action>empurrar\s+"
        r"(?:a|o)\s+(?:porta|portao|grade)\b[^.!?;:,]*|"
        r"empurra[-\u2010\u2011]l[ao]),"
    )

    def require_action(value: str, field: str, rule: str) -> None:
        unauthorized = _unauthorized_action_concepts(
            value, authorized_actions=(
                {("interact", "open"): opening_targets}
                if rule in {
                    "undeclared_player_barrier_open", "undeclared_player_nominal_open_attempt",
                    "presupposed_player_barrier_open",
                }
                else authorized_actions
            ),
        )
        if unauthorized:
            raise SceneProposalError(
                "scene_player_agency_violation",
                evidence={"field": field, "rule": rule,
                          "unauthorized_concepts": unauthorized},
            )

    for field_name, field_value in fields:
        normalized = _normalize_for_policy(field_value)
        # A failed attempt is still an action. Restrict this added form to
        # explicit barriers, using the same actor and target checks as tools.
        temporal_actions = (
            *((match, "undeclared_player_instrument_action")
              for match in instrumental.finditer(normalized)),
            *((match, "undeclared_player_barrier_attempt")
              for match in barrier_attempt.finditer(normalized)),
            # Investigating a barrier does not imply touching it. Keep the
            # same actor/family/target checks as an explicit forcing attempt.
            *((match, "undeclared_player_contact")
              for match in barrier_contact.finditer(normalized)),
            *((match, "undeclared_player_barrier_open")
              for match in barrier_open.finditer(normalized)),
            *((match, "undeclared_player_barrier_push")
              for match in barrier_push.finditer(normalized)),
            *((match, "undeclared_player_temporal_search")
              for match in temporal_search.finditer(normalized)),
        )
        for match, rule in temporal_actions:
            previous = re.split(r"[.!?;]", normalized[:match.start()])[-1].strip()
            following = normalized[match.end():].lstrip()
            following_player = bool(re.match(
                r"^(?:voce|(?:seu|sua|o|a)\s+personagem)\b", following,
            ))
            if not (rule in {
                "undeclared_player_barrier_push", "undeclared_player_barrier_open",
                "undeclared_player_temporal_search",
            } and following_player) and any(
                re.match(rf"^{re.escape(npc)}\s+\w+", clause)
                for npc in npc_names for clause in (previous, following)
            ):
                continue
            # A grammatical NPC pronoun can own the temporal action; a name
            # used only as the instrument's owner does not do so by itself.
            if (
                re.match(r"^(?:ela|ele)\s+\w+", following)
                and _last_alias_position(match.group(), npc_names) >= 0
            ):
                continue
            # Weather after an opening may only describe its consequence;
            # it does not identify who opened the barrier. Explicit weather
            # openings and nominal observations are outside this new pattern.
            if rule != "undeclared_player_barrier_open" and re.match(
                r"^(?:o\s+vento|a\s+chuva|a\s+corrente\s+de\s+ar)\b", following,
            ):
                continue
            if rule == "undeclared_player_barrier_push" and re.fullmatch(
                r"empurra[-\u2010\u2011]l[ao]", match.group("action"),
            ):
                # A clitic is not a wildcard target. Resolve only one explicit
                # barrier in the immediately preceding sentence; ambiguity is
                # not permission to push a different object.
                barriers = tuple(re.finditer(r"\b(?:porta|portao|grade)\b", previous))
                if len(barriers) != 1:
                    raise SceneProposalError(
                        "scene_player_agency_violation",
                        evidence={"field": field_name, "rule": rule,
                                  "unauthorized_concepts": ["interact"]},
                    )
                target_phrase = "empurrar " + previous[barriers[0].start():]
                push_match = re.match("empurrar", target_phrase)
                declared_targets = authorized_actions.get(("interact", "push"))
                # Parse the antecedent as an object, not as a fresh action
                # clause (its adjectives may themselves resemble verbs).
                if declared_targets is None or not _action_target_is_authorized(
                    _action_target_tokens(target_phrase, push_match), declared_targets,
                ):
                    raise SceneProposalError(
                        "scene_player_agency_violation",
                        evidence={"field": field_name, "rule": rule,
                                  "unauthorized_concepts": ["interact"]},
                    )
                continue
            require_action(
                normalized[match.start("action"):match.end() - 1],
                field_name, rule,
            )

        for match in nominal_open_attempt.finditer(normalized):
            context = inspected_player_barrier.search(normalized[:match.start()])
            if context is None or re.search(
                r"\b(?:nao|nunca|jamais|sem|se|caso|talvez)\b", match.group("target"),
            ):
                continue
            # Infer the actor only for a categorical failure: a following
            # condition or another actor changes that attribution. Keep the
            # observed physical consequence, without skipping later clauses.
            suffix = re.split(r"[.!?;:]", normalized[match.end():], maxsplit=1)[0].strip()
            if suffix and (
                not re.fullmatch(
                    rf",\s*deixando\s+(?:a|o|as|os)\s+(?:metal|mecanismo|{_MECHANICAL_BARRIER})"
                    r"\b[^.!?;:]*", suffix,
                )
                or re.search(r"\b(?:se|caso|quando|talvez|nas?\s+maos?)\b", suffix)
                or _last_alias_position(suffix, npc_names) >= 0
            ):
                continue
            target = match.group("target") or " " + context.group("target")
            require_action("abrir" + target, field_name, "undeclared_player_nominal_open_attempt")

    question = _normalize_for_policy(proposal.player_prompt)
    # These two present/recent openings explicitly name the player. Keep
    # their targets and positive declarations; neither an NPC action nor a
    # future/negated option establishes a performed opening.
    player_subjects = "|".join(re.escape(alias) for alias in _normalized_aliases((
        "voce", "seu personagem", "sua personagem", "o personagem", "a personagem",
        *player_aliases,
    )))
    unquoted_question = re.sub(
        r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|«[^»\n]*»|'
        r"(?<!\w)'[^'\n]*'(?!\w)", " ", question,
    )
    current_opening = re.compile(
        rf"\benquanto\s+(?:{player_subjects})\s+abre\s+"
        rf"(?P<target>(?:a|o|as|os)\s+{_MECHANICAL_BARRIER}\b[^?!;,]*)"
    )
    recent_opening = re.compile(
        rf"\b(?P<target>{_MECHANICAL_BARRIER}(?:\s+(?!(?:que|e|mas|ou)\b)[a-z0-9]+){{0,3}})"
        rf"\s+que\s+(?:{player_subjects})\s+acaba\s+de\s+abrir\b"
    )
    for pattern in (current_opening, recent_opening):
        for match in pattern.finditer(unquoted_question):
            # A comma may introduce this opening's condition. A condition
            # after a new coordinated/subordinate action belongs to that
            # action, and cannot waive the preceding player opening.
            opening_clause = re.split(
                r"[?!;:.]|,(?!\s*(?:se|caso)\b)|\b(?:e|mas|porem|enquanto|quando)\b",
                unquoted_question[match.start("target"):], maxsplit=1,
            )[0]
            if re.search(r"\b(?:se|caso)\b", opening_clause):
                continue
            target = _ACTION_TARGET_BOUNDARY.split(match.group("target"), maxsplit=1)[0]
            require_action(
                "abrir " + target, "player_prompt",
                "presupposed_player_barrier_open",
            )
    for match in re.finditer(r"\b(?:ao|depois\s+de|apos)\s+(?P<action>[^?!;,]+)", question):
        clause = match.group("action")
        first_word = re.match(r"[a-z]+", clause)
        if first_word is None:
            continue
        # These perceptions and impersonal events do not describe a selected
        # voluntary action. A choice such as "ao decidir entrar" still does.
        if first_word.group() in {
            "ver", "ouvir", "sentir", "perceber", "notar", "anoitecer", "amanhecer",
        }:
            continue
        # A nominal infinitive ("ao abrir da porta") is an event, not a
        # transitive action whose omitted subject is the player.
        if re.match(r"\w+\s+(?:da|do|das|dos)\b", clause):
            continue
        actions = _action_signature_matches(clause)
        if not any(action.start() == 0 and action.group().endswith("r")
                   for _, _, action in actions):
            continue
        require_action(clause, "player_prompt", "presupposed_player_action")
