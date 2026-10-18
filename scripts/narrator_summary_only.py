"""Experimental summary-only shape and explicit word measurement; no semantic gate."""
from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr

VERSION = "record-summary-only-v1"
WORD_PATTERN = r"[^\W_]+(?:[-’'][^\W_]+)*"


class SummaryOnlyProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    summary: Annotated[StrictStr, Field(min_length=8, max_length=600)]


def measure_summary_words(summary: str) -> dict[str, object]:
    if type(summary) is not str:
        raise TypeError("Summary measurement requires a string")
    count = len(re.findall(WORD_PATTERN, summary, flags=re.UNICODE))
    return {
        "method": "unicode_words_with_internal_hyphen_or_apostrophe",
        "pattern": WORD_PATTERN,
        "word_count": count,
        "max_words": 25,
        "within_word_limit": count <= 25,
        "semantic_fidelity_evaluated": False,
    }
