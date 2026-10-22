"""Offline proposal boundary. No execution, gateway, RNG or persistence authority.

An accepted schema is not semantic proof. The independent guard deliberately
preserves existing classifier coverage and quarantines all unknown paraphrases.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from api.campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent

VERSION = 'intent-proposal-offline.v1'

class Frozen(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)

class Envelope(Frozen):
    version: Literal['intent-proposal-offline.v1'] = VERSION
    session_id: str = Field(min_length=1,max_length=160)
    operation_id: str = Field(min_length=1,max_length=160)
    state_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    player_input: str = Field(min_length=1,max_length=500)

    @property
    def fingerprint(self):
        raw=json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,separators=(',',':'))
        return sha256(raw.encode('utf-8')).hexdigest()

class EvidenceSpan(Frozen):
    start: int = Field(ge=0,le=500)
    end: int = Field(ge=1,le=500)
    text: str = Field(min_length=1,max_length=500)

    @model_validator(mode='after')
    def ordered(self):
        if self.end<=self.start: raise ValueError('evidence_range')
        return self

class Proposal(Frozen):
    version: Literal['intent-proposal-offline.v1'] = VERSION
    envelope_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    kind: Literal['known_intent','clarification','unsupported']
    intent: CampaignIntentKind | None
    evidence: tuple[EvidenceSpan,...] = Field(min_length=1,max_length=4)

    @model_validator(mode='after')
    def shape(self):
        if (self.kind=='known_intent') != (self.intent is not None):
            raise ValueError('intent_kind_mismatch')
        return self


def parse_proposal(raw: str, envelope: Envelope) -> Proposal:
    if type(raw) is not str or len(raw.encode('utf-8'))>4096:
        raise ValueError('proposal_size_or_type')
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('duplicate_key')
            result[k]=v
        return result
    # Validate JSON syntax/duplicates first; JSON-mode validation retains strict enum/tuple rules.
    value=json.loads(raw,object_pairs_hook=unique)
    if type(value) is not dict:raise ValueError('proposal_object_required')
    p=Proposal.model_validate_json(raw,strict=True)
    if p.envelope_sha256!=envelope.fingerprint:raise ValueError('proposal_binding')
    previous_end=0
    for span in p.evidence:
        if span.start<previous_end or envelope.player_input[span.start:span.end]!=span.text or span.end>len(envelope.player_input):
            raise ValueError('evidence_not_literal_or_overlapping')
        previous_end=span.end
    return p

@dataclass(frozen=True)
class Assessment:
    status: Literal['eligible_existing_intent','needs_independent_review','no_action']
    intent: CampaignIntentKind | None
    reason: str


def assess(raw: str, envelope: Envelope) -> Assessment:
    p=parse_proposal(raw,envelope)
    if p.kind!='known_intent':
        return Assessment('no_action',None,p.kind)
    independently_known=classify_campaign_intent(envelope.player_input)
    if independently_known is None:
        return Assessment('needs_independent_review',None,'source_not_independently_recognized')
    if independently_known!=p.intent:
        return Assessment('needs_independent_review',None,'source_intent_conflict')
    # Eligibility here is an offline judgment; this module cannot commit or execute it.
    return Assessment('eligible_existing_intent',p.intent,'existing_classifier_agrees')
