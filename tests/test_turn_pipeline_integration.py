from __future__ import annotations

import json

import pytest

from api.llm.contract import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CancellationToken,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    LLMTarget,
    utc_now,
)
from api.llm.testing import FakeLLMAdapter
from api.memory_service import create_consolidation
from api.core.config import settings
from api.orchestrator_service import (
    ROLL_POOL_REQUIRED_CODE,
    ROLL_POOL_REQUIRED_MESSAGE,
    STORYTELLER_SYSTEM_PROMPT,
    _explicit_test_pool,
    prepare_turn_pipeline,
    turn_requires_llm_runtime,
)
from api.persistence import SQLitePersistence
from api.scene_director_service import SceneContinuationProposal
from api.state_service import (
    configure_persistence_for_tests,
    get_persistence,
    sync_event_from_context,
)
from api.turn_execution_service import execute_prepared_lore_turn, execute_prepared_turn
from api.turn_models import (
    CanonicalEvent,
    CanonicalFact,
    ConsolidationScope,
    EpisodicMemory,
    NarrativeRecord,
    Visibility,
)


TARGET = LLMTarget(profile="pipeline-test", provider="fake", model="fake-model")
CAPABILITIES = CapabilitySet(
    target=TARGET,
    descriptors=(
        CapabilityDescriptor(
            name=CAPABILITY_TEXT_GENERATION,
            support=CapabilitySupport.NATIVE,
        ),
        CapabilityDescriptor(
            name=CAPABILITY_STRUCTURED_GENERATION,
            support=CapabilitySupport.EMULATED,
            source="offline Pydantic validation",
        ),
        CapabilityDescriptor(
            name=CAPABILITY_STREAMING,
            support=CapabilitySupport.NATIVE,
        ),
    ),
)


def test_h6_runtime_prompt_is_compact_and_preserves_core_invariants() -> None:
    assert len(STORYTELLER_SYSTEM_PROMPT.split()) <= 400
    assert not STORYTELLER_SYSTEM_PROMPT.startswith("---")
    assert "improviso coerente" in STORYTELLER_SYSTEM_PROMPT
    assert "não selecionar texto pronto" in STORYTELLER_SYSTEM_PROMPT
    assert "resultados mecânicos" in STORYTELLER_SYSTEM_PROMPT
    assert "Preserve a agência" in STORYTELLER_SYSTEM_PROMPT
    assert "português brasileiro idiomático" in STORYTELLER_SYSTEM_PROMPT
    assert "Sensação involuntária" in STORYTELLER_SYSTEM_PROMPT
    assert "Intenção ampla não autoriza microações" in STORYTELLER_SYSTEM_PROMPT
    assert "CONFIDENCIAIS" in STORYTELLER_SYSTEM_PROMPT
    assert "Responda somente com um objeto JSON" in STORYTELLER_SYSTEM_PROMPT
    assert "`f`: normalmente um fato" in STORYTELLER_SYSTEM_PROMPT
    assert "`k` (kind)" in STORYTELLER_SYSTEM_PROMPT
    assert "`q`: pergunta aberta" in STORYTELLER_SYSTEM_PROMPT
    assert "Nunca peça ao jogador fato" in STORYTELLER_SYSTEM_PROMPT
    assert "compartilham o estado final" in STORYTELLER_SYSTEM_PROMPT


@pytest.mark.parametrize(
    ("label", "skill"),
    (
        ("Atletismo", "Athletics"),
        ("Briga", "Brawl"),
        ("Ofício", "Craft"),
        ("Condução", "Drive"),
        ("Armas de Fogo", "Firearms"),
        ("Ladrão", "Larceny"),
        ("Armas Brancas", "Melee"),
        ("Furtividade", "Stealth"),
        ("Sobrevivência", "Survival"),
        ("Trato com Animais", "AnimalKen"),
        ("Etiqueta", "Etiquette"),
        ("Intuição", "Insight"),
        ("Intimidação", "Intimidation"),
        ("Liderança", "Leadership"),
        ("Performance", "Performance"),
        ("Persuasão", "Persuasion"),
        ("Manha", "Streetwise"),
        ("Subterfúgio", "Subterfuge"),
        ("Acadêmicos", "Academics"),
        ("Percepção", "Awareness"),
        ("Finanças", "Finance"),
        ("Investigação", "Investigation"),
        ("Medicina", "Medicine"),
        ("Ocultismo", "Occult"),
        ("Política", "Politics"),
        ("Ciência", "Science"),
        ("Tecnologia", "Technology"),
    ),
)
def test_every_frontend_skill_quick_action_has_a_local_pool(label, skill):
    resolved = _explicit_test_pool(f"Fazer teste de {label}")
    assert resolved is not None
    assert resolved[1].value == skill


def _scene_proposal(
    *,
    outcome: str,
    location: str,
    include_secret: bool = False,
    npcs_present: tuple[str, ...] = (),
) -> dict:
    if outcome == "success":
        narrative = (
            "Com um estalo seco, a porta cede e revela um corredor estreito sob "
            "lâmpadas instáveis; marcas recentes riscam o pó até uma escada metálica, "
            "enquanto passos contidos no piso superior transformam a passagem aberta "
            "em ameaça imediata."
        )
        scene_summary = (
            "A porta foi vencida, marcas recentes atravessam o corredor e alguém se "
            "move no piso superior."
        )
        visible_fact = {
            "kind": "observation",
            "summary": "Marcas recentes atravessam o corredor até a escada metálica.",
            "visibility": "player",
            "importance": 0.8,
            "pending": False,
        }
    elif outcome == "failure":
        narrative = (
            "A porta resiste ao impacto, e a tentativa falha enquanto a passagem "
            "permanece bloqueada; o "
            "estrondo percorre as paredes, acende uma luz vermelha ao fundo e transforma "
            "a demora em pressão quando passos apressados começam a se aproximar."
        )
        scene_summary = (
            "A porta continua fechada, uma luz de alerta foi acesa e passos se "
            "aproximam pelo corredor."
        )
        visible_fact = {
            "kind": "complication",
            "summary": "Uma luz de alerta acende e passos se aproximam pelo corredor.",
            "visibility": "player",
            "importance": 0.8,
            "pending": True,
        }
    elif location == "Elysium":
        narrative = (
            "No Elysium, conversas baixas cessam perto da porta principal enquanto o "
            "Xerife acompanha o salão; um envelope sem remetente "
            "aguarda sobre a mesa central, tornando a aparente calma uma tensão imediata."
        )
        scene_summary = (
            "O Elysium está tenso, o Xerife observa o salão e um envelope sem remetente "
            "aguarda na mesa central."
        )
        visible_fact = {
            "kind": "hook",
            "summary": "Um envelope sem remetente aguarda sobre a mesa central.",
            "visibility": "player",
            "importance": 0.7,
            "pending": True,
        }
    else:
        narrative = (
            "A rua industrial termina diante de um galpão abandonado, com janelas "
            "cobertas e uma porta lateral entreaberta; uma luz irregular pulsa no "
            "interior enquanto o som de metal arrastado estabelece uma ameaça imediata."
        )
        scene_summary = (
            "Um galpão abandonado domina a rua industrial, com luz irregular e ruído "
            "metálico vindo do interior."
        )
        visible_fact = {
            "kind": "observation",
            "summary": "Uma luz irregular pulsa atrás da porta lateral entreaberta.",
            "visibility": "player",
            "importance": 0.7,
            "pending": False,
        }

    facts = [visible_fact]
    if include_secret:
        facts.append(
            {
                "kind": "hook",
                "summary": "O Xerife acompanha a invasão por uma câmera oculta.",
                "visibility": "storyteller",
                "importance": 0.9,
                "pending": True,
            }
        )
    return {
        "narrative": narrative,
        "outcome": outcome,
        "location": location,
        "scene_summary": scene_summary,
        "npcs_present": list(npcs_present),
        "new_facts": facts,
        "open_threads": ["A origem dos passos permanece pendente"],
        "player_prompt": "Os passos param por um instante; como você reage?",
    }


class SequencedFakeLLM(FakeLLMAdapter):
    def __init__(self) -> None:
        super().__init__(
            capability_set=CAPABILITIES,
            text="A noite guarda as consequências da ação.",
            stream_deltas=("A porta cede ", "e o corredor se revela."),
        )
        self._structured = iter(
            (
                {"route": "action", "scene_notes": "Corredor escuro.", "lore_keywords": []},
                {
                    "intent": "Forçar a porta",
                    "attribute": "Strength",
                    "skill": "Athletics",
                    "power_used": None,
                    "weapon_category": "unarmed",
                    "is_aggressive": False,
                    "is_feeding": False,
                    "target_killed": True,
                    "is_bane_damage": True,
                    "is_blood_surge": False,
                    "is_willpower_reroll": False,
                    "action_target": "UNOPPOSED",
                    "is_compulsion_active": True,
                    "is_true_faith_active": True,
                    "inferred_difficulty": 7,
                    "npc_threat_level": 5,
                },
            )
        )
        self.scene_proposals: list[dict] = []

    async def generate_structured(self, request):
        if request.operation == "H6.direct_scene":
            prompt = request.messages[-1].content
            outcome = (
                "success"
                if "A ação teve sucesso." in prompt
                else "failure"
                if "A ação falhou." in prompt
                else "unresolved"
            )
            location = "Elysium" if "Local atual: Elysium." in prompt else "Corredor além da porta"
            self.structured_payload = _scene_proposal(
                outcome=outcome,
                location=location,
                include_secret=True,
            )
            self.scene_proposals.append(self.structured_payload)
        else:
            self.structured_payload = next(self._structured)
        return await super().generate_structured(request)


def _context() -> dict:
    return {
        "player_sheet": {
            "nome": "Karl",
            "clan": "brujah",
            "predator_type": "alleycat",
            "attributes": {
                "Strength": 3,
                "Athletics": 2,
                "Composure": 3,
                "Resolve": 3,
            },
            "skills": {"Athletics": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1,
                "current_hunger": 1,
                "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {
                    "size": 5,
                    "superficial": 0,
                    "aggravated": 0,
                },
            },
        },
        "last_action_cache": None,
        "pre_roll_snapshot": None,
    }


@pytest.mark.anyio
async def test_default_pipeline_attaches_mara_keyword_beat(tmp_path):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "mara-beat.sqlite3"))
    context = _context()
    context["scene"] = {"location": "Arquivo", "npcs_present": ["Mara"]}
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Mara, me fale sobre este lugar.",
            session_id="session-mara-beat",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-mara-beat",
            gateway=SequencedFakeLLM(),
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.draft is not None
    facts = [
        fact for fact in prepared.draft.facts
        if fact.fact_type == "world.scene.beat_resolution"
    ]
    assert len(facts) == 1, (
        prepared.kind,
        prepared.system_log,
        [fact.fact_type for fact in prepared.draft.facts],
    )
    assert facts[0].value["effect_keys"] == ["mara.answers.place_context"]
    packet = json.loads(prepared.system_log.split("\n", 1)[1])
    assert packet["scene_beat"]["value"]["guidance_keys"]


@pytest.mark.anyio
async def test_present_mara_question_routes_to_founder_beat_without_h0_lore(
    tmp_path, monkeypatch,
):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "mara-founder-route.sqlite3"))
    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", False)
    context = _context()
    context["scene"] = {"location": "Galeria", "npcs_present": ["Mara"]}
    gateway = FakeLLMAdapter(capability_set=CAPABILITIES)
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Mara, quem é a fundadora deste lugar?",
            session_id="session-mara-founder-route",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-mara-founder-route",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action"
    assert gateway.external_call_count == 0
    assert prepared.draft is not None
    beat_fact = next(
        fact for fact in prepared.draft.facts
        if fact.fact_type == "world.scene.beat_resolution"
    )
    assert beat_fact.value["selected_option_id"] == "mara.founder"
    assert beat_fact.value["effect_keys"] == [
        "mara.responds.without_founder_identity"
    ]


@pytest.mark.anyio
async def test_default_mara_keyword_beat_is_narrated_and_committed(tmp_path):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "mara-beat-commit.sqlite3")
    configure_persistence_for_tests(store)
    context = _context()
    context["scene"] = {"location": "Arquivo", "npcs_present": ["Mara"]}
    initial = sync_event_from_context("session-mara-commit", context)
    await store.ensure_campaign(
        "session-mara-commit", initial_state=initial.model_dump(mode="json")
    )
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Mara, me fale sobre este lugar.",
            session_id="session-mara-commit",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-mara-commit",
            gateway=SequencedFakeLLM(),
            target=TARGET,
            cancellation=CancellationToken(),
        )
        proposal = SceneContinuationProposal(
            n=(
                "Mara apoia a mão na capa do índice e responde com cautela. "
                "Explica que o Arquivo reúne passagens de visitantes e ocorrências "
                "da galeria, mas preserva nomes ligados à origem do acervo. Uma "
                "linha raspada interrompe as datas recentes e oferece um caminho "
                "concreto para a investigação sem encerrar a conversa."
            ),
            o="unresolved",
            e=("mara.answers.place_context",),
            l="Arquivo",
            s="Mara contextualizou o Arquivo e apontou uma irregularidade no índice.",
            p=("Mara",),
            f=(
                {"k": "npc_action", "s": "Mara abre o índice e explica a função do Arquivo."},
                {"k": "clue", "s": "Uma linha raspada interrompe as datas recentes."},
            ),
            t=("Investigar a linha raspada do índice",),
            r=(),
            q="O que você deseja examinar ou perguntar?",
        )
        narrator = FakeLLMAdapter(
            capability_set=CAPABILITIES,
            structured_payload=proposal.model_dump(mode="json", by_alias=True),
        )

        async def collect(_: str) -> None:
            return None

        completed = await execute_prepared_turn(
            prepared,
            session_id="session-mara-commit",
            operation_id="operation-mara-commit",
            user_input="Mara, me fale sobre este lugar.",
            chronicle_name="Teste",
            store=store,
            gateway=narrator,
            target=TARGET,
            cancellation=CancellationToken(),
            on_chunk=collect,
        )
    finally:
        configure_persistence_for_tests(previous)

    assert completed.status == "completed"
    assert completed.scene_resolution_receipt is not None
    assert completed.scene_resolution_receipt.effect_keys == (
        "mara.answers.place_context",
    )
    assert (await store.load_campaign("session-mara-commit"))["current_turn"] == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("user_input", "scene", "expected_status", "proposal", "expected_event_type"),
    (
        (
            "Onde estou?",
            None,
            "unknown",
            _scene_proposal(outcome="unresolved", location="Galpão abandonado"),
            "scene_established",
        ),
        (
            "Me mostre o lugar",
            {"location": "Elysium", "npcs_present": ["Príncipe", "Xerife"]},
            "known",
            _scene_proposal(
                outcome="unresolved",
                location="Elysium",
                npcs_present=("Príncipe", "Xerife"),
            ),
            "scene_advanced",
        ),
    ),
)
async def test_scene_queries_use_h6_to_establish_or_advance_canonical_state(
    tmp_path,
    user_input,
    scene,
    expected_status,
    proposal,
    expected_event_type,
):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / f"scene-query-{len(user_input)}.sqlite3")
    configure_persistence_for_tests(store)
    gateway = FakeLLMAdapter(
        capability_set=CAPABILITIES,
        structured_payload=proposal,
    )
    context = _context()
    session_id = f"session-scene-{len(user_input)}"
    operation_id = f"operation-scene-{len(user_input)}"
    if scene is not None:
        context["scene"] = scene
    try:
        initial = sync_event_from_context(session_id, context)
        await store.ensure_campaign(
            session_id,
            initial_state=initial.model_dump(mode="json"),
        )
        prepared = await prepare_turn_pipeline(
            user_input=user_input,
            session_id=session_id,
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id=operation_id,
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
        delivered: list[str] = []

        async def collect(text: str) -> None:
            delivered.append(text)

        result = await execute_prepared_turn(
            prepared,
            session_id=session_id,
            operation_id=operation_id,
            user_input=user_input,
            chronicle_name="Teste",
            store=store,
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
            on_chunk=collect,
        )

        assert prepared.kind == "action"
        assert prepared.draft is not None
        assert prepared.draft.facts[0].fact_type == "world.scene"
        assert prepared.draft.facts[0].value["status"] == expected_status
        assert prepared.draft.state_changes == ()
        assert prepared.context_packet is not None
        selected_items = [entry.item for entry in prepared.context_packet.selected]
        assert any(item.layer.value == "hot_scene" for item in selected_items)
        assert any("character" in item.tags for item in selected_items)
        assert any("catalog" in item.tags for item in selected_items)
        assert prepared.context_packet.estimated_tokens <= min(
            settings.context_token_budget,
            settings.narrator_context_token_budget,
        )
        if scene is not None:
            assert any("relationships" in item.tags for item in selected_items)
            assert "CONFIDENCIAL" in prepared.system_log
        assert turn_requires_llm_runtime(user_input, context) is True
        assert gateway.external_call_count == 1
        assert gateway.requests[0].operation == "H6.direct_scene"
        assert result.status == "completed", result.error
        assert result.narrative_mode == "llm"
        assert result.narrative is not None
        expected_text = SceneContinuationProposal.model_validate(proposal).player_text
        assert result.narrative.text == expected_text
        assert delivered == [expected_text]
        assert prepared.updated_context["scene"]["location"] == proposal["location"]
        assert prepared.updated_context["scene"]["summary"] == proposal["scene_summary"]
        assert prepared.updated_context["scene"]["open_threads"] == proposal["open_threads"]

        campaign = await store.load_campaign(session_id)
        assert campaign["current_turn"] == 1
        assert campaign["state"]["context"]["scene"]["location"] == proposal["location"]
        events = await store.list_events(session_id)
        assert [event["event_type"] for event in events] == [
            "player_scene_query",
            expected_event_type,
        ]
        memories = await store.list_episodic_memories(session_id)
        assert memories[0]["summary"] == proposal["scene_summary"]
    finally:
        configure_persistence_for_tests(previous)


@pytest.mark.anyio
async def test_scene_query_reuses_layered_context_and_keeps_aged_pending_secrets(
    tmp_path,
):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "scene-query-layered-context.sqlite3")
    configure_persistence_for_tests(store)
    session_id = "session-scene-layered-context"
    context = _context()

    async def ignore_chunk(_: str) -> None:
        return None

    try:
        initial = sync_event_from_context(session_id, context)
        await store.ensure_campaign(
            session_id,
            initial_state=initial.model_dump(mode="json"),
        )
        seed_gateway = SequencedFakeLLM()
        seeded = await prepare_turn_pipeline(
            user_input="Forço a porta do corredor.",
            session_id=session_id,
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-scene-layer-seed",
            gateway=seed_gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
        seeded_result = await execute_prepared_turn(
            seeded,
            session_id=session_id,
            operation_id="operation-scene-layer-seed",
            user_input="Forço a porta do corredor.",
            chronicle_name="Teste",
            store=store,
            gateway=seed_gateway,
            target=TARGET,
            cancellation=CancellationToken(),
            on_chunk=ignore_chunk,
        )
        assert seeded_result.status == "completed", seeded_result.error

        first_turn = (await store.list_turns(session_id))[0]
        aged_pending_fact = next(
            fact
            for fact in first_turn["facts"]
            if fact["visibility"] == "storyteller"
            and fact["fact_type"].startswith("world.scene.")
            and fact["value"].get("pending") is True
        )
        aged_pending_summary = aged_pending_fact["value"]["summary"]
        memory = EpisodicMemory.model_validate(
            (await store.list_episodic_memories(session_id))[0]["payload"]
        )
        consolidation = create_consolidation(
            (memory,),
            consolidation_id="consolidation-scene-query-layered",
            scope=ConsolidationScope.SCENE,
            proposed_summary="A passagem e a vigilância moldam a cena atual.",
        )
        await store.save_consolidation(consolidation)

        aged_context = seeded.updated_context
        aged_context["scene"]["npcs_present"] = ["Xerife"]
        recent_secret_summary = "O zelador recebeu ordem para apagar as câmeras."
        for number in range(2, 10):
            occurred_at = utc_now()
            turn_id = f"turn-scene-layer-{number}"
            visible_fact = CanonicalFact(
                fact_id=f"fact-scene-layer-visible-{number}",
                fact_type="world.scene.observation",
                predicate="scene_time_advanced",
                value={
                    "summary": f"O relógio avançou durante a espera {number}.",
                    "pending": False,
                },
                occurred_at=occurred_at,
                visibility=Visibility.PLAYER,
                importance=0.2,
                tags=("world", "scene", "observation"),
            )
            visible_event = CanonicalEvent(
                event_id=f"event-scene-layer-visible-{number}",
                session_id=session_id,
                turn_id=turn_id,
                sequence=0,
                event_type="scene_time_advanced",
                occurred_at=occurred_at,
                summary=visible_fact.value["summary"],
                fact_ids=(visible_fact.fact_id,),
                visibility=Visibility.PLAYER,
            )
            facts = [visible_fact]
            events = [visible_event]
            if number == 9:
                recent_secret = CanonicalFact(
                    fact_id="fact-scene-layer-recent-secret",
                    fact_type="world.scene.hook",
                    predicate="recent_storyteller_hook",
                    value={
                        "summary": recent_secret_summary,
                        "pending": False,
                    },
                    occurred_at=occurred_at,
                    visibility=Visibility.STORYTELLER,
                    importance=0.8,
                    tags=("world", "scene", "hook"),
                )
                facts.append(recent_secret)
                events.append(
                    CanonicalEvent(
                        event_id="event-scene-layer-recent-secret",
                        session_id=session_id,
                        turn_id=turn_id,
                        sequence=1,
                        event_type="storyteller_scene_thread_updated",
                        occurred_at=occurred_at,
                        summary="Uma informação reservada recente foi registrada.",
                        fact_ids=(recent_secret.fact_id,),
                        visibility=Visibility.STORYTELLER,
                    )
                )
            state = sync_event_from_context(
                session_id,
                aged_context,
                turn_number=number,
                state_revision=number - 1,
            )
            await store.commit_turn(
                session_id=session_id,
                operation_id=f"operation-scene-layer-{number}",
                turn_id=turn_id,
                turn_number=number,
                base_revision=number - 1,
                base_state_revision=number - 1,
                state=state.model_dump(mode="json"),
                narrative=NarrativeRecord(
                    narrative_id=f"narrative-scene-layer-{number}",
                    session_id=session_id,
                    turn_id=turn_id,
                    text=f"A espera prolonga a tensão da cena no turno {number}.",
                    source_event_ids=(visible_event.event_id,),
                ),
                facts=tuple(facts),
                events=tuple(events),
                context=aged_context,
                user_input="Espero e observo.",
                chronicle_name="Teste",
            )

        query_gateway = FakeLLMAdapter(
            capability_set=CAPABILITIES,
            structured_payload=_scene_proposal(
                outcome="unresolved",
                location=aged_context["scene"]["location"],
                npcs_present=("Xerife",),
            ),
        )
        prepared = await prepare_turn_pipeline(
            user_input="Onde estou?",
            session_id=session_id,
            context=aged_context,
            turn=10,
            chronicle_name="Teste",
            operation_id="operation-scene-layer-query",
            state_revision=9,
            gateway=query_gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )

        assert query_gateway.requests == []
        assert prepared.context_packet is not None
        selected_items = [entry.item for entry in prepared.context_packet.selected]
        assert any(item.item_id == memory.memory_id for item in selected_items)
        assert any(
            item.item_id == consolidation.consolidation_id for item in selected_items
        )
        assert any("character" in item.tags for item in selected_items)
        assert any(item.item_id == aged_pending_fact["fact_id"] for item in selected_items)
        assert any(
            item.item_id == "fact-scene-layer-recent-secret"
            for item in selected_items
        )
        assert prepared.system_log.count(aged_pending_summary) == 1
        assert prepared.system_log.count(recent_secret_summary) == 1
        _, packet_json = prepared.system_log.split("\n", 1)
        memory_context = json.loads(packet_json)["context"]["memory"]["text"]
        known_context, marker, confidential_context = memory_context.partition(
            "CONFIDENCIAL\n"
        )
        assert marker
        assert aged_pending_summary not in known_context
        assert recent_secret_summary not in known_context
        assert aged_pending_summary in confidential_context
        assert recent_secret_summary in confidential_context

        result = await execute_prepared_turn(
            prepared,
            session_id=session_id,
            operation_id="operation-scene-layer-query",
            user_input="Onde estou?",
            chronicle_name="Teste",
            store=store,
            gateway=query_gateway,
            target=TARGET,
            cancellation=CancellationToken(),
            on_chunk=ignore_chunk,
        )
        assert result.status == "completed", result.error
        assert [request.operation for request in query_gateway.requests] == [
            "H6.direct_scene"
        ]
        assert result.narrative is not None
        assert aged_pending_summary not in result.narrative.text
        assert recent_secret_summary not in result.narrative.text
    finally:
        configure_persistence_for_tests(previous)


@pytest.mark.anyio
async def test_compound_scene_question_keeps_the_action_pipeline(tmp_path):
    previous = get_persistence()
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / "compound-scene-action.sqlite3")
    )
    gateway = SequencedFakeLLM()
    user_input = "Onde estou e investigo a porta?"
    try:
        prepared = await prepare_turn_pipeline(
            user_input=user_input,
            session_id="session-compound-scene-action",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-compound-scene-action",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert turn_requires_llm_runtime(user_input, _context()) is True
    assert prepared.kind == "action", prepared.system_log
    assert prepared.draft is not None
    assert prepared.draft.facts[0].fact_type == "mechanics.resolution"
    assert gateway.requests == []


@pytest.mark.anyio
async def test_supported_investigation_survives_h1_failure_and_rolls_locally(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", True)
    previous = get_persistence()
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / "h1-target-unavailable.sqlite3")
    )
    class H1UnavailableFake(FakeLLMAdapter):
        async def generate_structured(self, request):
            if request.operation == "h0.triage":
                self.failure_category = None
                self.structured_payload = {
                    "route": "action",
                    "scene_notes": "",
                    "lore_keywords": [],
                }
            else:
                self.failure_category = ErrorCategory.INVALID_REQUEST
            return await super().generate_structured(request)

    gateway = H1UnavailableFake(capability_set=CAPABILITIES)
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Investigar o galpão abandonado.",
            session_id="session-h1-target-unavailable",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-h1-target-unavailable",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    assert prepared.draft is not None
    payload = prepared.updated_context["last_action_cache"]["payload"]
    assert payload["intent"] == "Investigar o galpão abandonado."
    assert payload["attribute"] == "Wits"
    assert payload["skill"] == "Investigation"
    assert payload["requires_roll"] is True
    assert prepared.draft.facts[0].fact_type == "mechanics.resolution"
    assert any(
        getattr(item, "category", None) is ErrorCategory.INVALID_REQUEST
        for item in prepared.llm_diagnostics
    )


@pytest.mark.anyio
async def test_generic_roll_request_is_rejected_without_guessing_a_pool(
    tmp_path, monkeypatch
):
    previous = get_persistence()
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / "generic-roll-request.sqlite3")
    )
    gateway = SequencedFakeLLM()
    context = _context()
    monkeypatch.setattr(
        "api.orchestrator_service.calculate_resolution",
        lambda *args, **kwargs: pytest.fail("generic clarification reached RNG"),
    )
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Quero rolar os dados.",
            session_id="session-generic-roll-request",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-generic-roll-request",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert turn_requires_llm_runtime("Quero rolar os dados.", context) is False
    assert prepared.kind == "clarification"
    assert prepared.is_clarification is True
    assert prepared.code == ROLL_POOL_REQUIRED_CODE == "roll_pool_required"
    assert prepared.message == ROLL_POOL_REQUIRED_MESSAGE
    assert prepared.system_log == f"[AÇÃO INCOMPLETA] {ROLL_POOL_REQUIRED_MESSAGE}"
    assert prepared.draft is None
    assert prepared.updated_context["last_action_cache"] is None
    assert prepared.updated_context is context
    assert gateway.requests == []
    assert gateway.external_call_count == 0


def test_explicit_deterministic_pool_requires_the_normal_runtime() -> None:
    context = _context()
    context["deterministic_mechanics"] = {
        "attribute": "Wits",
        "skill": "Investigation",
    }

    assert turn_requires_llm_runtime("Quero rolar os dados.", context) is True


def test_scene_query_produces_every_recognized_npc_as_independent_candidate() -> None:
    from api.catalog_models import CatalogDomain
    from api.orchestrator_service import _scene_query_catalog_candidates
    from api.rules_service import PlayerSheetModel
    from api.scene_service import SceneState

    scene = SceneState(
        location="Elysium",
        npcs_present=("Príncipe", "Xerife"),
    )
    sheet = PlayerSheetModel.model_validate(_context()["player_sheet"])

    candidates = _scene_query_catalog_candidates(scene, sheet)

    assert [(candidate.domain, candidate.entry_id) for candidate in candidates] == [
        (CatalogDomain.CLAN, "brujah"),
        (CatalogDomain.NPC_ARCHETYPE, "prince"),
        (CatalogDomain.NPC_ARCHETYPE, "sheriff"),
    ]
    npc_candidates = tuple(
        candidate
        for candidate in candidates
        if candidate.domain is CatalogDomain.NPC_ARCHETYPE
    )
    assert all(candidate.signals.active_in_scene for candidate in npc_candidates)
    assert [
        candidate.source_refs[0].record_id for candidate in npc_candidates
    ] == [
        "catalog:npc_archetype/prince",
        "catalog:npc_archetype/sheriff",
    ]


def test_h6_projection_contains_only_selected_content_once_and_keeps_secrets() -> None:
    from api.context_service import ContextItem, ContextLayer, ContextQuery, assemble_context
    from api.orchestrator_service import _context_prompt

    secret = ContextItem(
        item_id="required-secret",
        layer=ContextLayer.CANONICAL_FACTS,
        content="O xerife protege a passagem oculta.",
        visibility=Visibility.STORYTELLER,
        required=True,
    )
    selected_catalog = ContextItem(
        item_id="catalog:npc_archetype/prince",
        layer=ContextLayer.WORLD_STATE,
        content="O príncipe governa o domínio.",
        selection_priority=1,
        tags=("catalog",),
    )
    duplicate_text = ContextItem(
        item_id="memory:duplicate",
        layer=ContextLayer.EPISODIC_MEMORY,
        content=selected_catalog.content,
        importance=1.0,
    )
    omitted_catalog = ContextItem(
        item_id="catalog:npc_archetype/sheriff",
        layer=ContextLayer.WORLD_STATE,
        content="CONTEÚDO OMITIDO NÃO PODE CHEGAR A H6.",
        selection_priority=2,
        tags=("catalog",),
    )
    budget = sum(
        max(1, (len(value) + 3) // 4)
        for value in (secret.content, selected_catalog.content)
    )
    packet = assemble_context(
        [omitted_catalog, duplicate_text, selected_catalog, secret],
        ContextQuery(
            query_text="príncipe",
            allowed_visibilities=frozenset(
                {Visibility.PLAYER, Visibility.STORYTELLER}
            ),
            token_budget=budget,
            chars_per_token=4.0,
        ),
    )

    prompt = _context_prompt(packet)

    assert secret.content in prompt
    assert "CONFIDENCIAL" in prompt
    assert prompt.count(selected_catalog.content) == 1
    assert omitted_catalog.content not in prompt
    assert omitted_catalog.item_id in packet.omitted_item_ids


@pytest.mark.anyio
async def test_real_pipeline_separates_secret_facts_then_commits_one_atomic_turn(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", True)
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "story.sqlite3")
    configure_persistence_for_tests(store)
    gateway = SequencedFakeLLM()
    cancellation = CancellationToken()
    chunks: list[str] = []

    async def collect(chunk: str) -> None:
        chunks.append(chunk)

    try:
        initial = sync_event_from_context("session-pipeline", _context())
        await store.ensure_campaign(
            "session-pipeline", initial_state=initial.model_dump(mode="json")
        )
        prepared = await prepare_turn_pipeline(
            user_input="Forço a porta do corredor.",
            session_id="session-pipeline",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-pipeline",
            gateway=gateway,
            target=TARGET,
            cancellation=cancellation,
        )

        assert prepared.draft is not None
        assert [fact.fact_type for fact in prepared.draft.facts] == [
            "mechanics.resolution",
            "state.character",
            "world.relationships",
        ]
        assert "interpreted_action" not in prepared.draft.facts[0].value
        assert "Forço a porta do corredor." in prepared.draft.events[0].summary
        assert [event.visibility.value for event in prepared.draft.events] == [
            "player",
            "storyteller",
        ]
        assert set(prepared.draft.events[0].fact_ids) == {
            prepared.draft.facts[0].fact_id,
            prepared.draft.facts[1].fact_id,
        }
        assert prepared.draft.events[1].fact_ids == (
            prepared.draft.facts[2].fact_id,
        )
        assert "CONHECIDO" in prepared.system_log
        assert "NARRATIVA AUTORIZADA" not in prepared.system_log
        assert prepared.system_log.count("Forço a porta do corredor.") == 1
        assert "normal_rolls" not in prepared.system_log
        assert "hunger_rolls" not in prepared.system_log
        assert "Estado após a ação:" in prepared.system_log
        assert "Corredor escuro." not in prepared.system_log
        assert "score=" not in prepared.system_log
        assert "visibilidade=" not in prepared.system_log
        resolution_receipt = prepared.draft.facts[0].value
        assert resolution_receipt["attribute"] == "Strength"
        assert resolution_receipt["skill"] == "Athletics"
        assert resolution_receipt["dice_pool"] == 5
        assert resolution_receipt["hunger_dice"] == 1
        assert resolution_receipt["difficulty"] == 3
        assert resolution_receipt["dice_pool"] == len(
            resolution_receipt["normal_rolls"]
        ) + len(resolution_receipt["hunger_rolls"])
        assert resolution_receipt["hunger_dice"] == len(
            resolution_receipt["hunger_rolls"]
        )
        assert resolution_receipt["outcome"] == (
            "success" if resolution_receipt["is_success"] else "failure"
        )
        _, narrator_packet_json = prepared.system_log.split("\n", 1)
        narrator_packet = json.loads(narrator_packet_json)
        assert narrator_packet["expected_outcome"] == {
            "source": "deterministic_engine",
            "trusted": True,
            "value": resolution_receipt["outcome"],
            "output_field": "o",
            "instruction": "Copie value exatamente para o campo o; não reinterprete.",
        }
        assert resolution_receipt["messy"] == resolution_receipt["messy_critical"]
        assert resolution_receipt["bestial"] == resolution_receipt["bestial_failure"]
        assert prepared.context_packet is not None
        selected_items = [entry.item for entry in prepared.context_packet.selected]
        assert all(item.content != "Corredor escuro." for item in selected_items)
        static_lore_item = next(
            item for item in selected_items if "catalog" in item.tags
        )
        assert static_lore_item.content.startswith("Arma (unarmed):")
        assert [reference.record_id for reference in static_lore_item.source_refs] == [
            "catalog:weapon/unarmed"
        ]
        cached_payload = prepared.updated_context["last_action_cache"]["payload"]
        assert cached_payload["inferred_difficulty"] == 3
        assert cached_payload["npc_threat_level"] == 2
        assert cached_payload["target_killed"] is False
        assert cached_payload["is_bane_damage"] is False
        assert cached_payload["is_compulsion_active"] is False
        assert cached_payload["is_true_faith_active"] is False

        result = await execute_prepared_turn(
            prepared,
            session_id="session-pipeline",
            operation_id="operation-pipeline",
            user_input="Forço a porta do corredor.",
            chronicle_name="Teste",
            store=store,
            gateway=gateway,
            target=TARGET,
            cancellation=cancellation,
            on_chunk=collect,
        )

        assert result.status == "completed", result.error
        assert result.narrative_mode == "llm"
        assert [record.operation for record in result.invocations] == [
            "h0.triage",
            "h1.extract_intent.attempt_1",
            "H6.direct_scene",
        ]
        assert len(
            {
                record.evidence.provenance.invocation_id
                for record in result.invocations
            }
        ) == 3
        assert result.narrative is not None
        assert len(gateway.scene_proposals) == 1
        proposal = SceneContinuationProposal.model_validate(gateway.scene_proposals[0])
        assert chunks == [result.narrative.text]
        assert result.narrative.text == proposal.player_text
        secret_summary = proposal.new_facts[1].summary
        assert secret_summary not in result.narrative.text
        if prepared.draft.facts[0].value["is_success"]:
            assert proposal.outcome == "success"
            assert "porta cede" in result.narrative.text
        else:
            assert proposal.outcome == "failure"
            assert "tentativa falha" in result.narrative.text
        persisted_events = await store.list_events("session-pipeline")
        persisted_turn = (await store.list_turns("session-pipeline"))[0]
        memories = await store.list_episodic_memories("session-pipeline")
        assert [event["visibility"] for event in persisted_events] == [
            "player",
            "storyteller",
            "player",
            "storyteller",
        ]
        assert [event["event_type"] for event in persisted_events] == [
            "player_action_resolved",
            "relationship_state_updated",
            "scene_established",
            "storyteller_scene_thread_updated",
        ]
        persisted_fact_types = [fact["fact_type"] for fact in persisted_turn["facts"]]
        assert set(persisted_fact_types) == {
            "mechanics.resolution",
            "state.character",
            "world.relationships",
            "world.scene",
            f"world.scene.{proposal.new_facts[0].kind.value}",
            "world.scene.hook",
            "world.scene.thread_opened",
        }
        assert len(persisted_fact_types) == 7
        visible_scene_event = next(
            event for event in persisted_events if event["event_type"] == "scene_established"
        )
        assert set(persisted_turn["narrative"]["source_event_ids"]) == {
            prepared.draft.events[0].event_id,
            visible_scene_event["event_id"],
        }
        assert [
            row["operation"]
            for row in persisted_turn["provenance"]["invocations"]
        ] == [
            "h0.triage",
            "h1.extract_intent.attempt_1",
            "H6.direct_scene",
        ]
        assert memories[0]["source_event_ids"] == [
            visible_scene_event["event_id"]
        ]
        assert memories[0]["summary"] == proposal.scene_summary
        assert prepared.updated_context["scene"]["location"] == proposal.location
        assert prepared.updated_context["scene"]["summary"] == proposal.scene_summary
        assert prepared.updated_context["scene"]["open_threads"] == list(
            proposal.open_threads
        )
        assert (await store.load_campaign("session-pipeline"))["current_turn"] == 1
        narrator_request = gateway.requests[-1]
        assert narrator_request.operation == "H6.direct_scene"
        assert narrator_request.response_model is SceneContinuationProposal
        assert "CONFIDENCIAIS" in narrator_request.messages[0].content
        assert "improviso coerente" in narrator_request.messages[0].content
        assert "Preserve a agência" in narrator_request.messages[0].content
        assert narrator_request.messages[1].content == prepared.system_log
        assert "CONHECIDO" in narrator_request.messages[1].content
        assert (
            narrator_request.parameters.max_output_tokens
            == settings.llm_scene_director_max_output_tokens
        )
        assert (
            narrator_request.parameters.temperature
            == settings.llm_scene_director_temperature
        )

        memory = EpisodicMemory.model_validate(memories[0]["payload"])
        consolidation = create_consolidation(
            (memory,),
            consolidation_id="consolidation-pipeline",
            scope=ConsolidationScope.SCENE,
            proposed_summary="A porta vencida abriu acesso ao corredor escuro.",
        )
        await store.save_consolidation(consolidation)
        next_gateway = SequencedFakeLLM()
        next_prepared = await prepare_turn_pipeline(
            user_input="Examino o corredor além da porta.",
            session_id="session-pipeline",
            context=prepared.updated_context,
            turn=2,
            chronicle_name="Teste",
            operation_id="operation-pipeline-next",
            gateway=next_gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
        assert next_prepared.draft is not None
        assert memory.summary in next_prepared.system_log
        assert proposal.scene_summary in next_prepared.system_log
        assert proposal.new_facts[0].summary in next_prepared.system_log
        assert proposal.open_threads[0] in next_prepared.system_log
        assert secret_summary in next_prepared.system_log
        _, packet_json = next_prepared.system_log.split("\n", 1)
        memory_context = json.loads(packet_json)["context"]["memory"]["text"]
        _, confidential_marker, confidential_context = memory_context.partition(
            "CONFIDENCIAL\n"
        )
        assert confidential_marker
        assert secret_summary in confidential_context
        assert "A porta vencida abriu acesso ao corredor escuro." not in (
            next_prepared.system_log
        )
        assert any(
            selected.item.item_id == consolidation.consolidation_id
            for selected in next_prepared.context_packet.selected
        )
    finally:
        configure_persistence_for_tests(previous)


@pytest.mark.anyio
async def test_lore_query_persists_derived_narrative_memory_and_two_invocations(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "lore.sqlite3")
    configure_persistence_for_tests(store)
    gateway = FakeLLMAdapter(
        capability_set=CAPABILITIES,
        structured_payload={
            "route": "lore_query",
            "scene_notes": "",
            "lore_keywords": ["brujah"],
        },
        text="Os Brujah carregam uma história de rebeldia e força apaixonada.",
    )
    try:
        initial = sync_event_from_context("session-lore", _context())
        await store.ensure_campaign(
            "session-lore", initial_state=initial.model_dump(mode="json")
        )
        prepared = await prepare_turn_pipeline(
            user_input="O que devo saber sobre os Brujah?",
            session_id="session-lore",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-lore",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )

        result = await execute_prepared_lore_turn(
            prepared,
            session_id="session-lore",
            operation_id="operation-lore",
            user_input="O que devo saber sobre os Brujah?",
            chronicle_name="Teste",
            store=store,
        )

        assert result.status == "completed", result.error
        assert result.narrative is not None
        assert result.narrative.text.startswith("Os Brujah carregam")
        assert [record.operation for record in result.invocations] == [
            "h0.triage",
            "h4.answer_lore_query",
        ]
        turn = (await store.list_turns("session-lore"))[0]
        assert turn["narrative"]["text"] == result.narrative.text
        assert [
            row["operation"] for row in turn["provenance"]["invocations"]
        ] == ["h0.triage", "h4.answer_lore_query"]
        assert (await store.list_events("session-lore"))[0]["event_type"] == (
            "player_lore_query"
        )
        assert len(await store.list_episodic_memories("session-lore")) == 1
        assert (await store.load_campaign("session-lore"))["current_turn"] == 1
    finally:
        configure_persistence_for_tests(previous)


@pytest.mark.anyio
async def test_neutral_input_cannot_activate_state_changes_proposed_by_h1(
    tmp_path,
):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "neutral.sqlite3"))
    gateway = SequencedFakeLLM()
    gateway._structured = iter(
        (
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {
                "intent": "Observar a rua",
                "attribute": "Wits",
                "skill": "Awareness",
                "power_used": "feral_weapons",
                "weapon_category": "heavy_firearm",
                "is_aggressive": True,
                "is_feeding": True,
                "is_healing": True,
                "is_blood_surge": True,
                "is_willpower_reroll": True,
                "action_target": "OPPOSED",
                "target_killed": True,
                "is_bane_damage": True,
                "is_compulsion_active": True,
                "is_true_faith_active": True,
                "inferred_difficulty": 7,
                "npc_threat_level": 5,
            },
        )
    )
    context = _context()
    context["player_sheet"]["disciplines"] = {"feral_weapons": 1}
    context["player_sheet"]["status"]["current_hunger"] = 2
    context["player_sheet"]["status"]["health_tracker"]["superficial"] = 3

    try:
        prepared = await prepare_turn_pipeline(
            user_input="Observo a rua em silêncio.",
            session_id="session-neutral",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-neutral",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action"
    sheet = prepared.updated_context["player_sheet"]
    assert sheet["status"]["current_hunger"] == 2
    assert sheet["status"]["health_tracker"]["superficial"] == 3
    assert sheet["status"]["willpower_tracker"]["superficial"] == 0
    payload = prepared.updated_context["last_action_cache"]["payload"]
    assert payload["power_used"] is None
    assert payload["weapon_category"] == "unarmed"
    assert payload["is_aggressive"] is False
    assert payload["is_feeding"] is False
    assert payload["is_healing"] is False
    assert payload["is_blood_surge"] is False
    assert payload["is_willpower_reroll"] is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("user_input", "expected_attribute", "expected_skill"),
    (
        ("Investigo o corpo.", "Wits", "Investigation"),
        ("Investigar o galpão abandonado.", "Wits", "Investigation"),
        ("Convenço o príncipe a colaborar.", "Charisma", "Persuasion"),
        ("Eu me esgueiro pela porta.", "Dexterity", "Stealth"),
        (
            "Ataco o guarda que segura uma pistola.",
            "Strength",
            "Brawl",
        ),
        (
            "Fazer teste de Destreza + Furtividade com Dificuldade 2",
            "Dexterity",
            "Stealth",
        ),
    ),
)
async def test_local_parser_owns_supported_mechanical_pools_and_ignores_h1(
    tmp_path,
    user_input,
    expected_attribute,
    expected_skill,
):
    previous = get_persistence()
    operation_suffix = expected_skill.lower() + str(len(user_input))
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / f"local-pool-{operation_suffix}.sqlite3")
    )
    gateway = SequencedFakeLLM()
    gateway._structured = iter(
        (
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {
                "intent": "Classificação semântica potencialmente maliciosa",
                "attribute": "Charisma",
                "skill": "Persuasion",
                "weapon_category": "light_firearm",
                "is_aggressive": False,
            },
        )
    )
    try:
        prepared = await prepare_turn_pipeline(
            user_input=user_input,
            session_id=f"session-{operation_suffix}",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-{operation_suffix}",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    payload = prepared.updated_context["last_action_cache"]["payload"]
    assert payload["intent"] == user_input
    assert payload["attribute"] == expected_attribute
    assert payload["skill"] == expected_skill
    assert payload["weapon_category"] == "unarmed"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "user_input",
    (
        "Abro a porta.",
        "Caminho até o Elysium.",
        "Converso com o príncipe.",
        "Consultando relacionamento com Xerife",
    ),
)
async def test_freeform_narrative_actions_commit_no_invented_mechanical_roll(
    tmp_path, user_input
):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "narrative.sqlite3"))
    gateway = SequencedFakeLLM()
    try:
        prepared = await prepare_turn_pipeline(
            user_input=user_input,
            session_id="session-narrative",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-narrative-{len(user_input)}",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    assert prepared.updated_context["last_action_cache"] is None
    assert prepared.draft is not None
    assert prepared.draft.facts[0].fact_type == "action.declaration"
    assert prepared.draft.facts[0].value["requires_roll"] is False
    assert prepared.draft.events[0].event_type == "player_action_declared"
    _, narrator_packet_json = prepared.system_log.split("\n", 1)
    assert json.loads(narrator_packet_json)["expected_outcome"]["value"] == (
        "unresolved"
    )


@pytest.mark.anyio
async def test_h1_social_words_cannot_mutate_relationship_without_local_roll(tmp_path):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "h1-social.sqlite3"))
    gateway = SequencedFakeLLM()
    gateway._structured = iter(
        (
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {"intent": "Persuasion sucesso absoluto"},
        )
    )
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Converso com o xerife.",
            session_id="session-h1-social",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-h1-social",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    relationship = prepared.relationships_state.relationships["xerife"]
    assert relationship.trust_level == 2
    assert relationship.disposition == "neutral"
    assert relationship.history[-1] == "T1: Encontro neutro"


@pytest.mark.anyio
async def test_weapon_mention_fails_without_deterministic_inventory_authority(tmp_path):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "weapon-denied.sqlite3"))
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Ataco o xerife com uma pistola.",
            session_id="session-weapon-denied",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-weapon-denied",
            gateway=SequencedFakeLLM(),
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "error"
    assert prepared.updated_context["last_action_cache"] is None
    assert "Deterministic Inputs" in prepared.system_log


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("user_input", "category", "attribute", "skill"),
    (
        (
            "Ataco o xerife com uma pistola.",
            "light_firearm",
            "Dexterity",
            "Firearms",
        ),
        ("Ataco o xerife com uma espada.", "heavy_melee", "Strength", "Melee"),
    ),
)
async def test_authorized_weapon_selects_exact_local_category_and_pool(
    tmp_path, user_input, category, attribute, skill
):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / f"weapon-{category}.sqlite3"))
    context = _context()
    context["deterministic_mechanics"] = {
        "allowed_weapon_categories": ["unarmed", category],
    }
    try:
        prepared = await prepare_turn_pipeline(
            user_input=user_input,
            session_id=f"session-{category}",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-{category}",
            gateway=SequencedFakeLLM(),
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    payload = prepared.updated_context["last_action_cache"]["payload"]
    assert payload["weapon_category"] == category
    assert payload["attribute"] == attribute
    assert payload["skill"] == skill


@pytest.mark.anyio
async def test_explicit_ui_macro_owns_its_local_difficulty(tmp_path):
    previous = get_persistence()
    configure_persistence_for_tests(SQLitePersistence(tmp_path / "difficulty.sqlite3"))
    try:
        prepared = await prepare_turn_pipeline(
            user_input="Fazer teste de Destreza + Furtividade com Dificuldade 2",
            session_id="session-difficulty",
            context=_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-difficulty",
            gateway=SequencedFakeLLM(),
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    cache = prepared.updated_context["last_action_cache"]
    assert cache["payload"]["inferred_difficulty"] == 2
    assert cache["target_successes"] == 2


@pytest.mark.anyio
async def test_localized_quick_actions_resolve_owned_power_ids(
    tmp_path,
):
    command = "Ativar disciplina Armas Ferais"
    power_id = "feral_weapons"
    previous = get_persistence()
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / f"power-{power_id}.sqlite3")
    )
    gateway = SequencedFakeLLM()
    gateway._structured = iter(
        (
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {"intent": "Ativar poder declarado"},
        )
    )
    context = _context()
    context["player_sheet"]["disciplines"] = {power_id: 1}
    try:
        prepared = await prepare_turn_pipeline(
            user_input=command,
            session_id=f"session-{power_id}",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-{power_id}",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    payload = prepared.updated_context["last_action_cache"]["payload"]
    assert payload["power_used"] == power_id
    assert payload["attribute"] == "Strength"
    assert payload["skill"] == "Brawl"
    assert payload["requires_roll"] is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("command", "power_id"),
    (
        ("Ativar disciplina Fascínio", "awe"),
        ("Ativar disciplina Salto Ascendente", "soaring_leap"),
    ),
)
async def test_free_power_activation_does_not_invent_an_action_roll(
    tmp_path,
    command,
    power_id,
):
    previous = get_persistence()
    configure_persistence_for_tests(
        SQLitePersistence(tmp_path / f"power-free-{power_id}.sqlite3")
    )
    gateway = SequencedFakeLLM()
    gateway._structured = iter(
        (
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {"intent": "Ativar poder declarado"},
        )
    )
    context = _context()
    context["player_sheet"]["disciplines"] = {power_id: 1}
    try:
        prepared = await prepare_turn_pipeline(
            user_input=command,
            session_id=f"session-free-{power_id}",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-free-{power_id}",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    assert prepared.updated_context["last_action_cache"] is None
    assert prepared.draft is not None
    action_facts = [
        fact.value
        for fact in prepared.draft.facts
        if isinstance(fact.value, dict) and fact.value.get("power_used") == power_id
    ]
    assert len(action_facts) == 1
    assert action_facts[0]["requires_roll"] is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("case_id", "command", "owned_power_ids"),
    (
        (
            "known-but-not-owned",
            "Ativar disciplina Carne de Mármore",
            (),
        ),
        (
            "unknown",
            "Ativar disciplina Voo Sombrio",
            (),
        ),
        (
            "ambiguous",
            "Ativar disciplina Armas Ferais e ativar disciplina Fascínio",
            ("feral_weapons", "awe"),
        ),
    ),
)
async def test_invalid_explicit_power_stops_before_h4_h6_and_commit(
    tmp_path,
    case_id,
    command,
    owned_power_ids,
):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / f"power-denied-{case_id}.sqlite3")
    configure_persistence_for_tests(store)
    gateway = SequencedFakeLLM()
    context = _context()
    context["player_sheet"]["disciplines"] = {
        power_id: 1 for power_id in owned_power_ids
    }
    session_id = f"session-power-denied-{case_id}"

    try:
        prepared = await prepare_turn_pipeline(
            user_input=command,
            session_id=session_id,
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id=f"operation-power-denied-{case_id}",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
        persisted_turns = await store.list_turns(session_id)
        persisted_events = await store.list_events(session_id)
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "error"
    assert prepared.draft is None
    assert prepared.updated_context["last_action_cache"] is None
    assert gateway.requests == []
    assert gateway.external_call_count == 0
    assert persisted_turns == []
    assert persisted_events == []


def test_power_authorization_requires_possession_even_when_selected() -> None:
    from api.orchestrator_service import _authorize_power_use
    from api.rules_service import DeterministicTurnInputs, PlayerSheetModel

    sheet_data = _context()["player_sheet"]
    sheet_data["disciplines"] = {}
    sheet = PlayerSheetModel(**sheet_data)

    with pytest.raises(ValueError, match="not possessed"):
        _authorize_power_use(
            "armas ferais",
            DeterministicTurnInputs(allowed_power_ids=("feral_weapons",)),
            sheet,
        )


def test_power_authorization_resolves_registry_alias_and_checks_family_level() -> None:
    from api.orchestrator_service import _authorize_power_use
    from api.rules_service import DeterministicTurnInputs, PlayerSheetModel

    sheet_data = _context()["player_sheet"]
    sheet_data["disciplines"] = {"protean": 1}
    sheet = PlayerSheetModel(**sheet_data)
    selected = DeterministicTurnInputs(allowed_power_ids=("armas_ferais",))

    with pytest.raises(ValueError, match="exceeds the owned discipline level"):
        _authorize_power_use("armas ferais", selected, sheet)

    sheet_data["disciplines"] = {"protean": 2}
    sheet = PlayerSheetModel(**sheet_data)
    assert _authorize_power_use("armas ferais", selected, sheet) == "feral_weapons"


@pytest.mark.anyio
async def test_casual_power_mention_without_activation_verb_remains_narrative(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(settings, "narrator_context_token_budget", 512)
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "power-casual-mention.sqlite3")
    configure_persistence_for_tests(store)
    gateway = SequencedFakeLLM()
    context = _context()

    try:
        prepared = await prepare_turn_pipeline(
            user_input="Recordo as histórias sobre Armas Ferais.",
            session_id="session-power-casual-mention",
            context=context,
            turn=1,
            chronicle_name="Teste",
            operation_id="operation-power-casual-mention",
            gateway=gateway,
            target=TARGET,
            cancellation=CancellationToken(),
        )
    finally:
        configure_persistence_for_tests(previous)

    assert prepared.kind == "action", prepared.system_log
    assert prepared.updated_context["last_action_cache"] is None
    assert prepared.draft is not None
    assert prepared.draft.facts[0].value["requires_roll"] is False
    assert "h4.generate_lore_context" not in {
        request.operation for request in gateway.requests
    }
    assert prepared.context_packet is not None
    assert any(
        reference.record_id == "catalog:clan/brujah"
        for selected in prepared.context_packet.selected
        for reference in selected.item.source_refs
    )
