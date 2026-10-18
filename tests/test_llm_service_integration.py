import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import api.h0_controller_service as h0_service
import api.h4_lore_expert_service as h4_service
import api.llm.testing as llm_testing
import api.parser_service as parser_service
from api.h0_controller_service import H0StructuredResult, triage_input
from api.h4_lore_expert_service import answer_lore_query, generate_lore_context
from api.llm import (
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    ErrorCategory,
    LLMInvocationError,
    LLMTarget,
    NormalizedError,
    StructuredGenerationRequest,
)
from api.llm.testing import FakeLLMAdapter
from api.parser_service import extract_intent
from api.rules_service import PlayerSheetModel


@pytest.fixture(autouse=True)
def _enable_optional_llm_stages_for_integration_contracts(monkeypatch):
    """These tests exercise opt-in adapters; production defaults stay deterministic."""

    monkeypatch.setattr(h0_service.settings, "llm_h0_enabled", True)
    monkeypatch.setattr(parser_service.settings, "llm_h1_enabled", True)
    monkeypatch.setattr(
        h4_service.settings,
        "llm_h4_action_enrichment_enabled",
        True,
    )


def _target() -> LLMTarget:
    return LLMTarget(
        profile="offline-test",
        provider="synthetic",
        model="fake-model",
    )


def _capabilities(
    *, structured: CapabilitySupport = CapabilitySupport.EMULATED
) -> CapabilitySet:
    return CapabilitySet(
        target=_target(),
        descriptors=(
            CapabilityDescriptor(
                name=CAPABILITY_TEXT_GENERATION,
                support=CapabilitySupport.NATIVE,
            ),
            CapabilityDescriptor(
                name=CAPABILITY_STRUCTURED_GENERATION,
                support=structured,
                source=(
                    "offline local schema validation"
                    if structured is CapabilitySupport.EMULATED
                    else "offline test declaration"
                ),
            ),
        ),
    )


def _action_payload() -> dict[str, object]:
    return {
        "intent": "Atacar o invasor",
        "attribute": "Strength",
        "skill": "Brawl",
        "is_aggressive": True,
    }


def _player_sheet() -> PlayerSheetModel:
    return PlayerSheetModel(
        clan="brujah",
        predator_type="alleycat",
        attributes={"Strength": 3},
        skills={"Brawl": 2},
        disciplines={},
        status={
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
    )


def _capture_stage_deadlines(
    monkeypatch,
    *,
    global_timeout: float,
    h0_timeout: float,
    h1_timeout: float,
    h4_timeout: float,
) -> tuple[datetime, datetime, datetime]:
    fixed_now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    for module in (h0_service, parser_service, h4_service):
        monkeypatch.setattr(module, "utc_now", lambda: fixed_now)
    monkeypatch.setattr(llm_testing, "utc_now", lambda: fixed_now)
    monkeypatch.setattr(
        llm_testing,
        "seconds_until",
        lambda deadline: (deadline - fixed_now).total_seconds(),
    )

    configuration = h0_service.settings
    monkeypatch.setattr(configuration, "llm_timeout_seconds", global_timeout)
    monkeypatch.setattr(configuration, "llm_h0_timeout_seconds", h0_timeout)
    monkeypatch.setattr(configuration, "llm_h1_timeout_seconds", h1_timeout)
    monkeypatch.setattr(configuration, "llm_h4_timeout_seconds", h4_timeout)

    h0_adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={"route": "action"},
    )
    h1_adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload=_action_payload(),
    )
    h4_adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        text="A noite preserva o contexto estático da crônica.",
    )

    asyncio.run(triage_input("Observo.", gateway=h0_adapter, target=_target()))
    asyncio.run(extract_intent("Ataco.", gateway=h1_adapter, target=_target()))
    asyncio.run(
        generate_lore_context(
            "Investigo.",
            None,
            _player_sheet(),
            gateway=h4_adapter,
            target=_target(),
        )
    )

    return (
        h0_adapter.requests[0].deadline,
        h1_adapter.requests[0].deadline,
        h4_adapter.requests[0].deadline,
    )


def test_h0_h1_h4_use_their_explicit_stage_deadlines(monkeypatch) -> None:
    fixed_now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    deadlines = _capture_stage_deadlines(
        monkeypatch,
        global_timeout=120.0,
        h0_timeout=45.0,
        h1_timeout=70.0,
        h4_timeout=55.0,
    )

    assert deadlines == (
        fixed_now + timedelta(seconds=45),
        fixed_now + timedelta(seconds=70),
        fixed_now + timedelta(seconds=55),
    )


def test_global_timeout_caps_every_stage_deadline(monkeypatch) -> None:
    fixed_now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

    deadlines = _capture_stage_deadlines(
        monkeypatch,
        global_timeout=40.0,
        h0_timeout=45.0,
        h1_timeout=70.0,
        h4_timeout=55.0,
    )

    assert deadlines == (fixed_now + timedelta(seconds=40),) * 3


def test_h0_uses_product_schema_and_explicitly_allows_emulated_structure() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={
            "route": "lore_query",
            "scene_notes": "",
            "lore_keywords": ["camarilla", "seita"],
        },
    )

    result = asyncio.run(
        triage_input(
            "O que é a Camarilla?",
            gateway=adapter,
            target=_target(),
        )
    )

    assert result.is_lore_query is True
    assert result.lore_keywords == ["camarilla", "seita"]
    assert adapter.external_call_count == 1
    request = adapter.requests[0]
    assert isinstance(request, StructuredGenerationRequest)
    assert request.response_model is H0StructuredResult
    structured_requirement = next(
        requirement
        for requirement in request.required_capabilities
        if requirement.name == CAPABILITY_STRUCTURED_GENERATION
    )
    assert structured_requirement.allow_emulated is True


def test_h0_keeps_deterministic_fallback_and_reports_normalized_failure() -> None:
    diagnostics: list[object] = []
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={},
        failure_category=ErrorCategory.RATE_LIMITED,
    )

    result = asyncio.run(
        triage_input(
            "Caminho pela rua vazia.",
            gateway=adapter,
            target=_target(),
            diagnostics=diagnostics,
        )
    )

    assert result.route == "action"
    assert adapter.external_call_count == 1
    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], NormalizedError)
    assert diagnostics[0].category is ErrorCategory.RATE_LIMITED


def test_h0_can_use_explicit_deterministic_triage_without_an_external_call(
    monkeypatch,
) -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={"route": "action"},
    )
    monkeypatch.setattr(h0_service.settings, "llm_h0_enabled", False)

    result = asyncio.run(
        triage_input(
            "O que é a Camarilla?",
            gateway=adapter,
            target=_target(),
        )
    )

    assert result.is_lore_query is True
    assert adapter.external_call_count == 0


def test_h0_uses_configured_runtime_when_dependencies_are_not_injected(
    monkeypatch,
) -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={"route": "action"},
    )
    monkeypatch.setattr(
        h0_service,
        "get_llm_runtime",
        lambda: SimpleNamespace(gateway=adapter, target=_target()),
    )

    result = asyncio.run(h0_service.triage_input("Observo a rua."))

    assert result.route == "action"
    assert adapter.external_call_count == 1


def test_h1_uses_semantic_only_schema_with_explicit_emulation_opt_in() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload=_action_payload(),
    )

    result = asyncio.run(
        extract_intent(
            "Ataco o invasor",
            gateway=adapter,
            target=_target(),
        )
    )

    assert result.intent == "Atacar o invasor"
    assert result.model_dump() == {"intent": "Atacar o invasor"}
    request = adapter.requests[0]
    assert request.response_model.__name__ == "H1IntentPayload"
    structured_requirement = next(
        requirement
        for requirement in request.required_capabilities
        if requirement.name == CAPABILITY_STRUCTURED_GENERATION
    )
    assert structured_requirement.allow_emulated is True


def test_h1_can_be_explicitly_disabled_without_changing_player_input(
    monkeypatch,
) -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={"intent": "resumo que não deve ser usado"},
    )
    monkeypatch.setattr(parser_service.settings, "llm_h1_enabled", False)

    result = asyncio.run(
        extract_intent(
            "Investigar o galpão abandonado.",
            gateway=adapter,
            target=_target(),
        )
    )

    assert result.intent == "Investigar o galpão abandonado."
    assert adapter.external_call_count == 0
    assert adapter.requests == []


class _SequencedStructuredFake(FakeLLMAdapter):
    def __init__(self, payloads: list[object]) -> None:
        super().__init__(
            capability_set=_capabilities(),
            structured_payload=None,
        )
        self._payloads = iter(payloads)

    async def generate_structured(self, request):
        self.structured_payload = next(self._payloads)
        return await super().generate_structured(request)


def test_h1_retries_once_after_invalid_structure_on_the_same_target() -> None:
    diagnostics: list[object] = []
    invocations: list[object] = []
    adapter = _SequencedStructuredFake(
        [
            {},
            _action_payload(),
        ]
    )

    result = asyncio.run(
        extract_intent(
            "Ataco o invasor",
            gateway=adapter,
            target=_target(),
            diagnostics=diagnostics,
            invocations=invocations,
        )
    )

    assert result.intent == "Atacar o invasor"
    assert adapter.external_call_count == 2
    assert [request.target for request in adapter.requests] == [_target(), _target()]
    assert adapter.requests[0].deadline == adapter.requests[1].deadline
    assert adapter.requests[0].cancellation is adapter.requests[1].cancellation
    assert len(adapter.requests[1].messages) == len(adapter.requests[0].messages) + 2
    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], NormalizedError)
    assert diagnostics[0].category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
    assert [record.status.value for record in invocations] == ["failed", "completed"]
    assert len(
        {record.evidence.provenance.invocation_id for record in invocations}
    ) == 2


def test_h1_does_not_retry_a_non_structured_failure() -> None:
    diagnostics: list[object] = []
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload=_action_payload(),
        failure_category=ErrorCategory.PROVIDER_UNAVAILABLE,
    )

    result = asyncio.run(
        extract_intent(
            "Ataco o invasor",
            gateway=adapter,
            target=_target(),
            diagnostics=diagnostics,
        )
    )

    assert result.intent == "Ataco o invasor"
    assert adapter.external_call_count == 1
    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], NormalizedError)
    assert diagnostics[0].category is ErrorCategory.PROVIDER_UNAVAILABLE


def test_h1_stops_after_one_structured_retry() -> None:
    diagnostics: list[object] = []
    invocations: list[object] = []
    adapter = _SequencedStructuredFake(
        [
            {},
            {},
        ]
    )

    result = asyncio.run(
        extract_intent(
            "Ataco o invasor",
            gateway=adapter,
            target=_target(),
            diagnostics=diagnostics,
            invocations=invocations,
        )
    )

    assert result.intent == "Ataco o invasor"
    assert adapter.external_call_count == 2
    assert len(diagnostics) == 2
    assert all(
        isinstance(diagnostic, NormalizedError)
        and diagnostic.category is ErrorCategory.INVALID_STRUCTURED_OUTPUT
        for diagnostic in diagnostics
    )
    assert [record.status.value for record in invocations] == ["failed", "failed"]


def test_h4_uses_text_generation_and_preserves_positional_arguments() -> None:
    lore = "Os Brujah carregam uma história de rebeldia e força apaixonada."
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        text=lore,
    )
    player_sheet = _player_sheet()

    context = asyncio.run(
        generate_lore_context(
            "Investigo o Elysium",
            None,
            player_sheet,
            ["elysium"],
            "Lore estático",
            gateway=adapter,
            target=_target(),
        )
    )
    answer = asyncio.run(
        answer_lore_query(
            "O que devo saber sobre os Brujah?",
            player_sheet,
            gateway=adapter,
            target=_target(),
        )
    )

    assert context == f"[CONTEXTO DE MUNDO (H4)]:\n{lore}"
    assert answer == lore
    assert adapter.external_call_count == 2
    assert [request.operation for request in adapter.requests] == [
        "h4.generate_lore_context",
        "h4.answer_lore_query",
    ]
    assert all(request.target == _target() for request in adapter.requests)
    atmospheric_prompt = adapter.requests[0].messages[0].content
    grounded_request = adapter.requests[-1].messages[-1].content
    grounded_prompt = adapter.requests[-1].messages[0].content
    assert "atmosfera opcional" in atmospheric_prompt
    assert "sem afirmar novo fato" in atmospheric_prompt
    assert "reformulador de fatos selecionados" in grounded_prompt
    assert "Use somente os fatos fornecidos" in grounded_prompt
    assert '"entry_id":"brujah"' in grounded_request
    assert "Fatos selecionados e vinculantes" in grounded_request


def test_h4_unknown_query_returns_not_covered_without_calling_model() -> None:
    adapter = FakeLLMAdapter(capability_set=_capabilities(), text="não deve ser usado")

    answer = asyncio.run(
        answer_lore_query(
            "Quem governa a cidade perdida de Atlântida?",
            _player_sheet(),
            gateway=adapter,
            target=_target(),
        )
    )

    assert "não está coberta" in answer
    assert adapter.external_call_count == 0


def test_h4_configuration_failure_never_becomes_a_static_lore_success() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        text="unused",
        failure_category=ErrorCategory.AUTHENTICATION_FAILED,
    )
    diagnostics: list[object] = []

    with pytest.raises(LLMInvocationError):
        asyncio.run(
            generate_lore_context(
                "Investigo",
                None,
                _player_sheet(),
                static_lore="Lore estático preservado",
                gateway=adapter,
                target=_target(),
                diagnostics=diagnostics,
            )
        )
    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], NormalizedError)
    assert diagnostics[0].category is ErrorCategory.AUTHENTICATION_FAILED


def test_h4_action_enrichment_can_preserve_static_lore_without_external_call(
    monkeypatch,
) -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        text="Lore externo que não deve ser chamado.",
    )
    monkeypatch.setattr(
        h4_service.settings,
        "llm_h4_action_enrichment_enabled",
        False,
    )

    context = asyncio.run(
        generate_lore_context(
            "Investigo",
            None,
            _player_sheet(),
            static_lore="Lore estático preservado",
            gateway=adapter,
            target=_target(),
        )
    )

    assert context == "Lore estático preservado"
    assert adapter.external_call_count == 0


def test_partial_dependency_injection_never_mixes_with_the_runtime(monkeypatch) -> None:
    runtime_lookups = 0

    def forbidden_runtime_lookup():
        nonlocal runtime_lookups
        runtime_lookups += 1
        raise AssertionError("partial injection must fail before runtime composition")

    monkeypatch.setattr(h0_service, "get_llm_runtime", forbidden_runtime_lookup)
    monkeypatch.setattr(parser_service, "get_llm_runtime", forbidden_runtime_lookup)
    monkeypatch.setattr(h4_service, "get_llm_runtime", forbidden_runtime_lookup)
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload=_action_payload(),
        text="Lore que não deve ser chamado.",
    )

    triage = asyncio.run(triage_input("Observo a rua.", gateway=adapter))
    intent = asyncio.run(extract_intent("Observo a rua.", gateway=adapter))
    lore = asyncio.run(
        generate_lore_context(
            "Observo a rua.",
            None,
            _player_sheet(),
            static_lore="Lore estático",
            gateway=adapter,
        )
    )

    assert triage.route == "action"
    assert intent.intent == "Observo a rua."
    assert lore == "Lore estático"
    assert adapter.external_call_count == 0
    assert runtime_lookups == 0


@pytest.mark.parametrize(
    "text",
    (
        "Mara, me fale sobre este lugar.",
        'Pergunto a Mara: "O que é este lugar?"',
        "Digo ao Xerife que explique sua ordem.",
    ),
)
def test_h0_deterministic_triage_keeps_explicit_npc_dialogue_as_action(
    monkeypatch, text
) -> None:
    monkeypatch.setattr(h0_service.settings, "llm_h0_enabled", False)

    result = asyncio.run(triage_input(text))

    assert result.route == "action"
    assert result.is_lore_query is False


def test_h0_present_npc_question_bypasses_lore_route_even_when_model_would_choose_it() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={
            "route": "lore_query", "scene_notes": "", "lore_keywords": ["fundadora"],
        },
    )

    result = asyncio.run(triage_input(
        "Mara, quem é a fundadora deste lugar?",
        npc_aliases=("Mara",), gateway=adapter, target=_target(),
    ))

    assert result.route == "action"
    assert adapter.external_call_count == 0


def test_h0_npc_override_requires_the_named_actor_to_be_present() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={
            "route": "lore_query", "scene_notes": "", "lore_keywords": ["fundadora"],
        },
    )

    result = asyncio.run(triage_input(
        "Mara, quem é a fundadora deste lugar?",
        npc_aliases=("Xerife",), gateway=adapter, target=_target(),
    ))

    assert result.route == "lore_query"
    assert adapter.external_call_count == 1


def test_h0_general_lore_question_remains_lore_with_present_npc() -> None:
    adapter = FakeLLMAdapter(
        capability_set=_capabilities(),
        structured_payload={
            "route": "lore_query", "scene_notes": "", "lore_keywords": ["camarilla"],
        },
    )

    result = asyncio.run(triage_input(
        "O que é a Camarilla?",
        npc_aliases=("Mara",), gateway=adapter, target=_target(),
    ))

    assert result.route == "lore_query"
    assert adapter.external_call_count == 1
