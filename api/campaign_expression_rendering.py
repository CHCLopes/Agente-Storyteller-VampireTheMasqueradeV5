"""A1 frozen renderer v1: application facts and explicitly attributed free slots.

This is an experimental presentation contract, never semantic certification.
Keep the v1 compiler in the registry when adding future renderer versions.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from .campaign_progression_service import CampaignNarratorPacket
from .narrative_grounding import NarrativeVisibility

SHA = Annotated[StrictStr, Field(pattern=r'^[0-9a-f]{64}$')]
ID = Annotated[StrictStr, Field(min_length=1, max_length=240)]
RENDERER = 'campaign-expression-renderer.v1'
SOURCE_POLICY = 'campaign-expression-application-v2'


def digest(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode='json')
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class Frozen(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always', hide_input_in_errors=True)


class CriticalSegment(Frozen):
    segment_id: ID
    actor: Literal['player', 'environment', 'record', 'mara']
    referent: Literal['record', 'founder_identity', 'rescue_attempt']
    speaker: Literal['mara'] | None = None
    predicate: ID
    polarity: Literal['affirmative', 'negative'] = 'affirmative'
    modality: Literal['actual'] = 'actual'
    phase: Literal['prepared_result'] = 'prepared_result'
    effect_refs: tuple[ID, ...]
    fact_refs: tuple[ID, ...]
    text: Annotated[StrictStr, Field(min_length=1, max_length=1200)]
    visibility: Literal['player'] = 'player'


class ExpressionSlot(Frozen):
    slot_id: Literal['atmosphere', 'mara.reaction']
    actor: Literal['environment', 'mara']
    max_characters: Literal[240] = 240
    topic: StrictStr
    optional: Literal[True] = True


class RealizationPlan(Frozen):
    protocol: Literal['campaign-realization-plan-v2'] = 'campaign-realization-plan-v2'
    renderer_version: Literal['campaign-expression-renderer.v1'] = RENDERER
    session_id: ID
    operation_id: ID
    turn_id: ID
    base_revision: StrictInt = Field(ge=0)
    preparation_sha256: SHA
    critical: tuple[CriticalSegment, ...] = Field(min_length=1, max_length=3)
    slots: tuple[ExpressionSlot, ...] = Field(min_length=1, max_length=2)
    question: Literal['', 'O que você faz agora?']
    plan_sha256: SHA

    @model_validator(mode='after')
    def consistent(self):
        if (len({x.segment_id for x in self.critical}) != len(self.critical)
                or len({x.slot_id for x in self.slots}) != len(self.slots)
                or self.plan_sha256 != digest(self.model_dump(mode='json', exclude={'plan_sha256'}))):
            raise ValueError('campaign_expression_plan_invalid')
        return self


class SlotText(Frozen):
    slot_id: Literal['atmosphere', 'mara.reaction']
    text: Annotated[StrictStr, Field(max_length=240)]

    @field_validator('text', mode='before')
    @classmethod
    def normalize(cls, value):
        if type(value) is not str or any(unicodedata.category(c).startswith('C') for c in value):
            raise ValueError('campaign_expression_text_invalid')
        if any(c in value for c in '"“”«»<>`\n\r:—'):
            raise ValueError('campaign_expression_speaker_markup_forbidden')
        return ' '.join(unicodedata.normalize('NFC', value).split())


class CampaignExpressionProposal(Frozen):
    protocol: Literal['campaign-source-expression-v2'] = 'campaign-source-expression-v2'
    plan_sha256: SHA
    slots: tuple[SlotText, ...] = Field(min_length=1, max_length=2)


class PresentedSegment(Frozen):
    segment_id: ID
    origin: Literal['application', 'llm']
    actor: Literal['player', 'environment', 'record', 'mara']
    speaker: Literal['mara'] | None = None
    separator_before: Literal["", " "] = " "
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    text: StrictStr
    effect_refs: tuple[ID, ...] = ()
    fact_refs: tuple[ID, ...] = ()
    invocation_id: ID | None = None


class CampaignExpressionPresentation(Frozen):
    narrative: Annotated[StrictStr, Field(min_length=40, max_length=1600)]
    player_prompt: StrictStr
    realized_effects: tuple[StrictStr, ...]
    expression: CampaignExpressionProposal
    segments: tuple[PresentedSegment, ...]

    @property
    def player_text(self):
        return self.narrative + ('\n\n' + self.player_prompt if self.player_prompt else '')


class ComposedSource(Frozen):
    protocol: Literal['campaign-composed-source-v2'] = 'campaign-composed-source-v2'
    source_id: ID
    session_id: ID
    turn_id: ID
    invocation_id: ID
    authorship: Literal['segmented'] = 'segmented'
    text: StrictStr
    source_policy: Literal['campaign-expression-application-v2'] = SOURCE_POLICY
    visibility: NarrativeVisibility = NarrativeVisibility.PLAYER
    sha256: SHA

    @model_validator(mode='after')
    def valid(self):
        if self.sha256 != hashlib.sha256(self.text.encode('utf-8')).hexdigest():
            raise ValueError('campaign_expression_source_hash_mismatch')
        return self


class ComposedProjection(Frozen):
    source: ComposedSource
    text: StrictStr
    segments: tuple[PresentedSegment, ...]
    semantic_truth_assessed: Literal[False] = False
    canonical_authority: Literal['prepared_events_only'] = 'prepared_events_only'

    @model_validator(mode='after')
    def bound(self):
        if self.text != self.source.text or not self.segments:
            raise ValueError('campaign_expression_projection_mismatch')
        cursor = 0
        for index, segment in enumerate(self.segments):
            cursor += len(segment.separator_before)
            if ((index == 0 and segment.separator_before != "") or segment.start != cursor or segment.end != segment.start + len(segment.text)
                    or self.text[segment.start:segment.end] != segment.text
                    or segment.origin == 'application' and segment.invocation_id is not None
                    or segment.origin == 'llm' and segment.invocation_id != self.source.invocation_id):
                raise ValueError('campaign_expression_segment_mismatch')
            cursor = segment.end
        if self.text != ''.join(x.separator_before + x.text for x in self.segments):
            raise ValueError('campaign_expression_segment_coverage_mismatch')
        return self


def compile_plan_v1(packet: CampaignNarratorPacket, fact_refs: tuple[str, ...]) -> RealizationPlan:
    p = CampaignNarratorPacket.model_validate(packet)
    if p.state_before.content_version != 'record-at-risk.v2':
        raise ValueError('campaign_expression_requires_record_v2')
    rule = p.beat.selected_option_id.split('.', 1)[0]
    wet = p.state_after.record == 'wet'
    physical, speech, actor, referent = '', '', 'record', 'record'
    if rule == 'R-01':
        condition = 'molhado, com trechos ainda legíveis' if wet else 'seco, ameaçado pela infiltração'
        physical = f'O registro permanece na bancada baixa do Arquivo, {condition}. A posição do documento não mudou.'
        if 'mara.responds.to_rescue_request' in p.required_effects:
            speech = 'Mara responde: “Posso orientar você sobre o resgate do registro. A superfície seca fica na Galeria.”'
        elif 'safe_surface' in p.state_before.known_information:
            speech = 'Mara responde: “Como eu disse, a tarefa é preservar o registro da água. A superfície seca fica na Galeria.”'
        else:
            speech = 'Mara responde: “A tarefa é preservar o registro da água. Você pode levar o documento até a superfície seca da Galeria.”'
    elif rule == 'R-02':
        physical = 'O registro continua na bancada baixa do Arquivo, sob o risco da infiltração. A pergunta não altera a posição nem o estado do documento.'
        speech = 'Mara responde: “Não vou divulgar a identidade da fundadora.”'
        referent = 'founder_identity'
    elif rule == 'R-03':
        physical = 'A água pinga da infiltração e se aproxima do registro sobre a bancada baixa do Arquivo. O documento permanece seco e intacto; nenhuma folha foi movida.'
        speech = 'Mara avisa: “A água está chegando perto do registro.”'
        actor = 'environment'
    elif rule == 'R-03B':
        physical = 'A água da infiltração atinge o registro na bancada baixa do Arquivo. As páginas ficam molhadas e parte da tinta se espalha. Ainda há trechos legíveis; o documento continua na bancada.'
        speech = 'Mara diz: “A água molhou as páginas.”'
        actor = 'environment'
    elif rule == 'R-04':
        physical = 'A água continua caindo sobre o registro na bancada baixa do Arquivo. O texto se torna irrecuperável e o documento está perdido. As folhas permanecem na bancada, sem conteúdo legível para recuperar.'
        speech = 'Mara diz: “O conteúdo se perdeu.”'
        actor = 'environment'
    elif rule == 'R-05':
        physical = 'Você retira o registro da bancada baixa do Arquivo e o protege na superfície seca da Galeria. O documento foi salvo intacto, fora do alcance da água. O resgate está concluído.'
        speech = 'Mara diz: “O registro está preservado.”'
        actor = 'player'
    elif rule == 'R-06':
        physical = 'Você retira o registro molhado da bancada baixa e o coloca na superfície seca da Galeria. Apenas a parte ainda legível foi salva. O dano anterior permanece e as páginas continuam molhadas; o resgate parcial está concluído.'
        speech = 'Mara diz: “O que ainda dava para ler está preservado.”'
        actor = 'player'
    elif rule == 'R-07':
        physical = 'Durante o exame do registro, você consegue recuperar um trecho ainda legível. A informação obtida é parcial; outras linhas permanecem ilegíveis. O documento continua na bancada baixa do Arquivo. A investigação termina sem restaurar o registro inteiro.'
        speech = 'Mara diz: “Parte do conteúdo foi recuperada.”'
        actor = 'player'
    elif rule == 'R-08':
        physical = 'O exame falha: você não consegue ler o registro nem recuperar seu conteúdo. '
        physical += ('A água molha as páginas sobre a bancada baixa do Arquivo; ainda há trechos legíveis. O documento permanece na bancada, e o resgate parcial continua possível.' if wet else
                     'A água torna o texto do registro irrecuperável. O documento está perdido e permanece na bancada baixa do Arquivo. A tentativa termina sem conteúdo recuperado.')
        speech = 'Mara diz: “Não foi possível ler o registro.”'
        actor = 'player'
    elif rule == 'R-09':
        condition = 'molhado, com parte do texto ainda legível' if wet else 'seco, ainda ameaçado pela infiltração'
        physical = f'A tentativa termina com a desistência declarada. O registro permanece na bancada baixa do Arquivo, {condition}. O documento continua no mesmo lugar, sem ter sido resgatado.'
        speech = 'Mara reconhece a desistência: “Entendido. Não haverá ajuda no resgate.”'
        referent = 'rescue_attempt'
    else:
        raise ValueError('campaign_expression_rule_unsupported')
    critical = (
        CriticalSegment(segment_id='consequence', actor=actor, referent='record',
                        predicate=p.beat.selected_option_id, effect_refs=p.required_effects,
                        fact_refs=fact_refs, text=physical),
        CriticalSegment(segment_id='mara.essential', actor='mara', referent=referent, speaker='mara',
                        predicate='mara.refuses.identity' if rule == 'R-02' else 'mara.responds.to_prepared_result',
                        polarity='negative' if rule in {'R-02', 'R-08'} else 'affirmative',
                        effect_refs=p.required_effects, fact_refs=fact_refs, text=speech),
    )
    payload = dict(session_id=p.session_id, operation_id=p.operation_id, turn_id=p.turn_id,
                   base_revision=p.base_revision, preparation_sha256=p.preparation_sha256,
                   critical=critical, slots=(
                       ExpressionSlot(slot_id='atmosphere', actor='environment', topic='Ambiente público já estabelecido; nenhuma mudança física nova.'),
                       ExpressionSlot(slot_id='mara.reaction', actor='mara', topic='Reação breve compatível; sem tarefa, justificativa, efeito novo ou ação do jogador.'),
                   ), question='' if p.state_after.outcome is not None else 'O que você faz agora?')
    raw = RealizationPlan.model_construct(**payload, plan_sha256='0' * 64).model_dump(mode='json', exclude={'plan_sha256'})
    return RealizationPlan.model_validate({**raw, 'plan_sha256': digest(raw)})


_FROZEN_COMPILERS = {RENDERER: compile_plan_v1}


def build_realization_plan(packet, fact_refs):
    return compile_plan_v1(packet, fact_refs)


def verify_realization_plan(plan, packet, fact_refs):
    checked = RealizationPlan.model_validate(plan)
    if checked != _FROZEN_COMPILERS[checked.renderer_version](packet, fact_refs):
        raise ValueError('campaign_expression_plan_binding_mismatch')
    return checked


def compose_expression(value, *, plan: RealizationPlan, invocation_id: str | None = None):
    checked = CampaignExpressionProposal.model_validate(value)
    plan = RealizationPlan.model_validate(plan)
    if (checked.plan_sha256 != plan.plan_sha256
            or tuple(x.slot_id for x in checked.slots) != tuple(x.slot_id for x in plan.slots)):
        raise ValueError('campaign_expression_slot_binding_mismatch')
    rows = []
    slots = {x.slot_id: x.text for x in checked.slots}
    def add(sid, text, origin, actor, speaker=None, effects=(), facts=(), separator=" "):
        separator = separator if rows else ""
        start = (rows[-1].end if rows else 0) + len(separator)
        rows.append(PresentedSegment(segment_id=sid, origin=origin, actor=actor, speaker=speaker,
                                     separator_before=separator, start=start, end=start + len(text), text=text,
                                     effect_refs=effects, fact_refs=facts,
                                     invocation_id=invocation_id if origin == 'llm' else None))
    if slots['atmosphere']:
        add('atmosphere', slots['atmosphere'], 'llm', 'environment')
    for segment in plan.critical:
        add(segment.segment_id, segment.text, 'application', segment.actor, segment.speaker,
            segment.effect_refs, segment.fact_refs)
    if slots['mara.reaction']:
        add('mara.reaction.prefix', 'Mara diz: “', 'application', 'mara', 'mara')
        add('mara.reaction', slots['mara.reaction'], 'llm', 'mara', 'mara', separator='')
        add('mara.reaction.suffix', '”', 'application', 'mara', 'mara', separator='')
    effects = tuple(dict.fromkeys(effect for s in plan.critical for effect in s.effect_refs))
    result = CampaignExpressionPresentation(narrative=''.join(x.separator_before + x.text for x in rows), player_prompt=plan.question,
                                           realized_effects=effects, expression=checked, segments=tuple(rows))
    if not 30 <= len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", result.player_text)) <= 150:
        raise ValueError('campaign_expression_word_budget')
    return result
