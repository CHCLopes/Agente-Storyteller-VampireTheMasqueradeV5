"""Local regressions found during the isolated manual game; no provider calls."""
from copy import deepcopy

import pytest

from api.core.config import settings
from api.llm.contract import CapabilitySet, LLMTarget
from api.llm.testing import FakeLLMAdapter
import api.orchestrator_service as orchestrator
from api.scene_service import SceneState, scene_fact_text
from api.state_service import get_persistence


LONG_SCENE = SceneState(
    location="Elysium", npcs_present=("Príncipe", "Xerife"),
    summary="A luz atravessa o salão e alcança os bancos de madeira junto à parede. " * 7,
    details=(
        "O Príncipe permanece junto à mesa diante da janela fechada, sob uma faixa de luz pálida.",
        "O Xerife aguarda ao lado da porta de madeira; o silêncio permite ouvir a chuva no pátio.",
    ),
    open_threads=("Resposta ao Príncipe", "Reação do Xerife"),
)


def _context():
    return {
        "player_sheet": {
            "nome": "Pessoa sintética", "attributes": {"Wits": 3, "Composure": 3, "Resolve": 3},
            "skills": {"Investigation": 2}, "disciplines": {},
            "status": {"blood_potency": 1, "current_hunger": 1, "humanity": 7,
                       "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                       "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}},
        },
        "last_action_cache": None, "pre_roll_snapshot": None,
        "scene": LONG_SCENE.model_dump(mode="json"),
    }


@pytest.fixture
def local_gateway(monkeypatch):
    for field in ("llm_h0_enabled", "llm_h1_enabled", "llm_h4_action_enrichment_enabled"):
        monkeypatch.setattr(settings, field, False)
    monkeypatch.setattr(orchestrator, "calculate_resolution", lambda *a, **k: pytest.fail("unexpected RNG"))
    target = LLMTarget(profile="local-regression", provider="fake", model="synthetic")
    return target, FakeLLMAdapter(capability_set=CapabilitySet(target=target, descriptors=()))


@pytest.mark.anyio
@pytest.mark.parametrize("user_input", ["Fazer teste de raciocínio", "teste de Força.", "Fazer teste de Wits"])
async def test_attribute_only_test_request_clarifies_without_llm_roll_or_state(user_input, local_gateway):
    target, gateway = local_gateway
    context = _context(); original = deepcopy(context)
    assert orchestrator.turn_requires_llm_runtime(user_input, context) is False
    prepared = await orchestrator.prepare_turn_pipeline(
        user_input=user_input, session_id="partial-roll", context=context, turn=1,
        chronicle_name="Teste", operation_id="partial-roll-operation", gateway=gateway, target=target,
    )
    assert prepared.kind == "clarification" and prepared.code == "roll_pool_required"
    assert prepared.draft is None and prepared.updated_context == original
    assert gateway.requests == []
    assert await get_persistence().list_turns("partial-roll") == []


@pytest.mark.parametrize("user_input", [
    "Fazer teste de raciocínio + investigação", "Fazer teste de Investigação",
    "Reflito sobre meu raciocínio.", "Ele pede para fazer teste de raciocínio.",
])
def test_complete_pools_and_narrative_mentions_keep_existing_runtime_route(user_input):
    assert orchestrator.turn_requires_llm_runtime(user_input, _context()) is True


def test_server_supplied_complete_pool_can_resolve_attribute_only_request():
    context = _context()
    context["deterministic_mechanics"] = {"attribute": "Wits", "skill": "Investigation"}
    assert orchestrator.turn_requires_llm_runtime("Fazer teste de raciocínio", context) is True


@pytest.mark.anyio
@pytest.mark.parametrize("budget", [192, 768])
async def test_long_social_scene_has_closed_budget_failure_or_complete_required_context(budget, monkeypatch, local_gateway):
    target, gateway = local_gateway
    monkeypatch.setattr(settings, "narrator_context_token_budget", budget)
    context = _context()
    async def prepare():
        return await orchestrator.prepare_turn_pipeline(
            user_input="Cumprimento o príncipe", session_id="long-social", context=context,
            turn=1, chronicle_name="Teste", operation_id="long-social-operation", gateway=gateway, target=target,
        )
    if budget == 192:
        with pytest.raises(ValueError) as caught:
            await prepare()
        assert type(caught.value).__name__ == "NarratorContextBudgetError"
        assert caught.value.code == "narrator_context_budget_exceeded"
        assert LONG_SCENE.summary not in str(caught.value)
    else:
        prepared = await prepare()
        assert prepared.kind == "action" and prepared.draft is not None
        required = [item for item in prepared.context_packet.selected if item.item.required]
        assert len(required) == 4
        assert scene_fact_text(LONG_SCENE) in [item.item.content for item in required]
        assert all(item.item.content for item in required)
        assert sum(item.estimated_tokens for item in required) <= budget
        assert prepared.draft.facts[0].fact_type == "action.declaration"
        assert context["scene"] == LONG_SCENE.model_dump(mode="json")
    assert gateway.requests == []
    assert await get_persistence().list_turns("long-social") == []


@pytest.mark.anyio
async def test_other_context_errors_are_not_mislabeled_as_budget(monkeypatch, local_gateway):
    target, gateway = local_gateway
    def fail(*args, **kwargs):
        raise ValueError("visible context item_id values must be unique")
    monkeypatch.setattr(orchestrator, "assemble_context", fail)
    with pytest.raises(ValueError, match="visible context item_id values must be unique") as caught:
        await orchestrator.prepare_turn_pipeline(
            user_input="Cumprimento o príncipe", session_id="other-context-error", context=_context(),
            turn=1, chronicle_name="Teste", operation_id="other-context-operation", gateway=gateway, target=target,
        )
    assert type(caught.value) is ValueError
    assert gateway.requests == []
