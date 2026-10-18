"""Two independently authored synthetic cases for offline record observations.

No historical API output or campaign data is read. The unchanged packet builder
retains its ``original_synthetic_corpus`` context tags: for these cases that tag
means this new corpus, whose exact path and hash appear in ``case.source``.
The corpus contains inputs only; it defines neither desired records nor scores.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

# This must precede derivation's API imports, independently of the caller.
os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"

from scripts.narrator_record_derivation import DerivationCase, DerivationContractError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION = "record-independent-cases-v1"
CORPUS_PATH = PROJECT_ROOT / "evals/narrator/record_independent_cases_v1.json"
CORPUS_SHA256 = "fb7ca3efe4bb950969c18f72f704b4ab41f7039bdd2685ab7c774b58ce4f8353"
CASE_IDS = ("uncertain-signal", "sensory-evidence")
_CORPUS_ID = "storyteller-record-independent-cases-v1"
_CORPUS_REL = "evals/narrator/record_independent_cases_v1.json"
_ORIGIN = "agent_authored_synthetic_cases"
_CONTEXT = "A crônica é urbana, contemporânea e gótico-punk."
_FIXED_INPUTS = (
    ("uncertain-signal", "independent-uncertainty", "derive-uncertainty",
     "A luz de uma luminária acesa ilumina o interior da biblioteca, que está vazia naquele momento. Um ruído vindo de trás da estante sugere que algum mecanismo talvez esteja funcionando ali."),
    ("sensory-evidence", "independent-sensory", "derive-sensory",
     "No interior da oficina deserta, há um cheiro de tinta fresca que permanece no ar daquele lugar. Sobre a bancada da oficina, uma lâmpada de cor azul pisca de maneira intermitente."),
)
_ERROR_CODES = frozenset({
    "record_independent_cases_source_unavailable",
    "record_independent_cases_hash_mismatch",
    "record_independent_cases_identity_mismatch",
    "record_independent_cases_fixed_case_mismatch",
})


class IndependentCasesError(DerivationContractError):
    """A fixed safe reason, compatible with the existing derivation boundary."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERROR_CODES else "record_independent_cases_identity_mismatch"
        super().__init__(self.code)


def load_independent_cases() -> tuple[DerivationCase, ...]:
    """Reload the frozen corpus and enforce its exact types, identities and order."""
    try:
        content = CORPUS_PATH.read_bytes()
    except OSError:
        raise IndependentCasesError("record_independent_cases_source_unavailable") from None
    if hashlib.sha256(content).hexdigest() != CORPUS_SHA256:
        raise IndependentCasesError("record_independent_cases_hash_mismatch")
    try:
        document = json.loads(content)
        if (type(document) is not dict
                or set(document) != {"corpus_id", "synthetic_only", "origin", "cases"}
                or document["corpus_id"] != _CORPUS_ID
                or document["synthetic_only"] is not True
                or document["origin"] != _ORIGIN
                or type(document["cases"]) is not list
                or len(document["cases"]) != len(_FIXED_INPUTS)):
            raise ValueError
        cases = []
        for index, (item, fixed) in enumerate(zip(document["cases"], _FIXED_INPUTS)):
            case_id, episode_id, turn_id, narrative = fixed
            expected = {"case_id": case_id, "episode_id": episode_id,
                        "turn_id": turn_id, "narrative": narrative,
                        "player_input": "Onde estou?", "outcome": "unresolved",
                        "scene": None, "known_context": _CONTEXT}
            if (type(item) is not dict or set(item) != set(expected)
                    or any(type(item[key]) is not type(value) or item[key] != value
                           for key, value in expected.items())):
                raise ValueError
            source = {
                "case_binding": VERSION, "origin": _ORIGIN,
                "synthetic_only": True, "corpus_id": _CORPUS_ID,
                "corpus_file": _CORPUS_REL, "corpus_sha256": CORPUS_SHA256,
                "case_path": f"/cases/{index}", "case_id": case_id,
                "episode_id": episode_id, "turn_id": turn_id,
                "field": "narrative",
                "narrative_sha256": hashlib.sha256(narrative.encode("utf-8")).hexdigest(),
                "context_origin": "original_synthetic_corpus",
                "protected_secrets_count": 0,
            }
            cases.append(DerivationCase(**expected, source=source))
        return tuple(cases)
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise IndependentCasesError("record_independent_cases_identity_mismatch") from None


def verify_independent_case(case: DerivationCase) -> None:
    """Do not authorize a forged narrative, source, context, or mutable snapshot."""
    if type(case) is not DerivationCase or type(case.source) is not dict:
        raise IndependentCasesError("record_independent_cases_fixed_case_mismatch")
    for fixed in load_independent_cases():
        fields = ("case_id", "episode_id", "turn_id", "narrative", "player_input",
                  "outcome", "scene", "known_context")
        # Dataclass/dict equality alone equates bool and int. Every source value
        # here is a scalar, so require its exact frozen type before equality.
        if (all(type(getattr(case, name)) is type(getattr(fixed, name))
                for name in fields)
                and set(case.source) == set(fixed.source)
                and all(type(key) is str
                        and type(case.source[key]) is type(fixed.source[key])
                        for key in case.source)
                and case == fixed):
            return
    raise IndependentCasesError("record_independent_cases_fixed_case_mismatch")
