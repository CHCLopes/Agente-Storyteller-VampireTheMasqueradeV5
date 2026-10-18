import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.core.config import settings
from api.main import app
from api.rules_service import V5ActionPayload, PlayerSheetModel
from api.combat_service import calculate_damage, apply_damage_to_tracker
from api.discipline_service import apply_power_modifiers
from api.llm import (
    CAPABILITY_STREAMING,
    CAPABILITY_STRUCTURED_GENERATION,
    CAPABILITY_TEXT_GENERATION,
    CapabilityDescriptor,
    CapabilitySet,
    CapabilitySupport,
    LLMTarget,
)
from api.llm.testing import FakeLLMAdapter
from api.persistence import SQLitePersistence
from api.state_service import configure_persistence_for_tests, get_persistence

client = TestClient(app, base_url='http://127.0.0.1:8000')


@pytest.fixture
def isolated_persistence(tmp_path):
    previous = get_persistence()
    store = SQLitePersistence(tmp_path / "storyteller-tests.sqlite3")
    configure_persistence_for_tests(store)
    try:
        yield store
    finally:
        configure_persistence_for_tests(previous)


def _offline_target() -> LLMTarget:
    return LLMTarget(
        profile="perf-offline",
        provider="synthetic",
        model="fake-model",
    )


def _offline_capabilities() -> CapabilitySet:
    return CapabilitySet(
        target=_offline_target(),
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


class _SequencedOfflineLLM(FakeLLMAdapter):
    def __init__(
        self,
        structured_payloads: list[object],
        *,
        text: str = "Contexto sintético de lore.",
        stream_deltas: tuple[str, ...] = ("Narrativa sintética.",),
    ) -> None:
        super().__init__(
            capability_set=_offline_capabilities(),
            text=text,
            structured_payload=None,
            stream_deltas=stream_deltas,
        )
        self._structured_payloads = iter(structured_payloads)

    async def generate_structured(self, request):
        self.structured_payload = next(self._structured_payloads)
        return await super().generate_structured(request)


def _scene_proposal_payload() -> dict:
    return {
        "narrative": (
            "A corrida rompe o silêncio da rua quando uma porta metálica bate "
            "adiante e passos apressados desaparecem na esquina, deixando uma "
            "trilha fresca sob a luz instável dos postes."
        ),
        "outcome": "unresolved",
        "location": "Rua industrial",
        "scene_summary": "Uma presença fugiu pela esquina e deixou uma trilha recente.",
        "npcs_present": [],
        "new_facts": [
            {
                "kind": "hook",
                "summary": "Uma trilha recente segue pela esquina.",
                "visibility": "player",
                "importance": 0.7,
                "pending": True,
            }
        ],
        "open_threads": ["Descobrir quem fugiu pela esquina"],
        "player_prompt": "A trilha ainda está fresca; o que você faz?",
    }


def _pipeline_context() -> dict:
    return {
        "player_sheet": {
            "nome": "Karl",
            "clan": "brujah",
            "predator_type": "alleycat",
            "attributes": {"Strength": 3, "Composure": 3, "Resolve": 3},
            "skills": {"Brawl": 2},
            "disciplines": {"feral_weapons": 2},
            "status": {
                "blood_potency": 1,
                "current_hunger": 1,
                "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0},
            },
        },
        "last_action_cache": None,
        "pre_roll_snapshot": None,
    }

def test_health_performance():
    response = client.get("/health")
    assert response.status_code == 200

def test_playersheet_validation():
    valid_data = {
        "attributes": {"Strength": 3},
        "skills": {"Brawl": 2},
        "disciplines": {"awe": 1},
        "status": {
            "blood_potency": 1,
            "current_hunger": 1,
            "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        }
    }
    model = PlayerSheetModel(**valid_data)
    assert model.attributes["Strength"] == 3
    assert model.status.health_tracker.size == 7

def test_combat_tracker_incapacitated():
    res = apply_damage_to_tracker(tracker_size=7, superficial=0, aggravated=7, incoming_damage=1, damage_type="superficial")
    assert res.is_incapacitated is True


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        ("Não vou me alimentar; apenas observo.", "is_feeding"),
        ("Se ele me atacar, eu fujo.", "is_aggressive"),
        ("Não vou curar meu ferimento agora.", "is_healing"),
        ("Não quero rerrolar força de vontade.", "is_willpower_reroll"),
    ],
)
def test_negated_or_conditional_text_never_authorizes_mechanical_flag(text, flag):
    from api.orchestrator_service import _authorized_intent_flags

    assert _authorized_intent_flags(text)[flag] is False

def test_pipeline_integration_feral_weapons(isolated_persistence, monkeypatch):
    from api.economy_service import RouseResult
    from api.orchestrator_service import prepare_turn_pipeline
    from api.rules_service import ResolutionResult

    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", True)

    adapter = _SequencedOfflineLLM(
        [
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            {
                "intent": "Atacar",
                "attribute": "Strength",
                "skill": "Brawl",
                "power_used": "feral_weapons",
                "weapon_category": "unarmed",
                "is_aggressive": True,
                "is_feeding": False,
                "target_killed": False,
                "is_bane_damage": False,
                "is_blood_surge": False,
                "is_willpower_reroll": False,
            },
        ]
    )

    mocked_rouse = RouseResult(
        new_hunger=2,
        rouse_failures=1,
        frenzy_warning=False,
        summary="Mocked Rouse Check",
    )
    mocked_resolution = ResolutionResult(
        successes=4,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="Roll Ok",
        normal_rolls=[],
        hunger_rolls=[],
        margin=2,
    )

    with patch("api.orchestrator_service.rouse_check", return_value=mocked_rouse) as mock_rouse_check, \
         patch("api.orchestrator_service.calculate_damage", wraps=calculate_damage) as spy_dmg, \
         patch("api.orchestrator_service.calculate_resolution", return_value=mocked_resolution) as mock_calc_res:
        prepared = asyncio.run(
            prepare_turn_pipeline(
                user_input="Ataco com feral weapons",
                session_id="test-feral-weapons",
                context=_pipeline_context(),
                turn=1,
                chronicle_name="Teste",
                operation_id="op-feral-weapons",
                gateway=adapter,
                target=_offline_target(),
            )
        )

    assert prepared.kind == "action"
    assert prepared.draft is not None
    mock_rouse_check.assert_called_once()
    assert mock_calc_res.call_args.kwargs["dice_pool"] == 5
    assert spy_dmg.call_args.kwargs["weapon_damage_bonus"] == 2
    assert prepared.updated_context["pre_roll_snapshot"] is not None
    assert (
        prepared.updated_context["pre_roll_snapshot"]["health_tracker"]["aggravated"]
        == 0
    )
    # Contexto de ação usa apenas fatos determinísticos e lore estático; H4 não
    # pode introduzir detalhes livres no estado narrativo canônico.
    assert adapter.external_call_count == 2  # H0 e H1.


def test_pipeline_rechecks_gate_immediately_before_rng(isolated_persistence, monkeypatch):
    from api.narration_resume_service import NarratorGateBlockedError
    from api.orchestrator_service import prepare_turn_pipeline

    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", True)
    adapter = _SequencedOfflineLLM([
        {"route": "action", "scene_notes": "", "lore_keywords": []},
        {
            "intent": "Atacar", "attribute": "Strength", "skill": "Brawl",
            "power_used": None, "weapon_category": "unarmed",
            "is_aggressive": True, "is_feeding": False,
            "target_killed": False, "is_bane_damage": False,
            "is_blood_surge": False, "is_willpower_reroll": False,
        },
    ])
    context = _pipeline_context()
    guard_calls: list[int] = []

    async def block_before_rng():
        guard_calls.append(1)
        raise NarratorGateBlockedError("blocked before RNG")

    with patch("api.orchestrator_service.calculate_resolution") as resolution:
        with pytest.raises(NarratorGateBlockedError):
            asyncio.run(prepare_turn_pipeline(
                user_input="Ataco o alvo",
                session_id="test-gate-before-rng",
                context=context,
                turn=1,
                chronicle_name="Teste",
                operation_id="op-gate-before-rng",
                gateway=adapter,
                target=_offline_target(),
                before_rng=block_before_rng,
            ))

    assert guard_calls == [1]
    resolution.assert_not_called()
    assert context["pre_roll_snapshot"] is None
    assert context["player_sheet"]["status"]["current_hunger"] == 1

def test_pipeline_willpower_reroll(isolated_persistence, monkeypatch):
    from api.orchestrator_service import prepare_turn_pipeline
    from api.rules_service import ResolutionResult

    monkeypatch.setattr(settings, "llm_h0_enabled", True)
    monkeypatch.setattr(settings, "llm_h1_enabled", True)

    action_payload = {
        "intent": "Atacar",
        "attribute": "Strength",
        "skill": "Brawl",
        "power_used": None,
        "weapon_category": "unarmed",
        "is_aggressive": True,
        "is_feeding": False,
        "target_killed": False,
        "is_bane_damage": False,
        "is_blood_surge": False,
        "is_willpower_reroll": False,
        "action_target": "OPPOSED",
        "inferred_difficulty": 3,
        "npc_threat_level": 2,
    }
    reroll_payload = {
        **action_payload,
        "intent": "Rerrolar",
        "is_aggressive": False,
        "is_willpower_reroll": True,
    }
    adapter = _SequencedOfflineLLM(
        [
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            action_payload,
            {"route": "action", "scene_notes": "", "lore_keywords": []},
            reroll_payload,
        ]
    )
    first_resolution = ResolutionResult(
        successes=4,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="Roll",
        normal_rolls=[6, 6, 6, 6],
        hunger_rolls=[],
        margin=2,
    )
    reroll_resolution = ResolutionResult(
        successes=6,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="Reroll",
        normal_rolls=[6, 6, 6, 6, 6, 6],
        hunger_rolls=[],
        margin=4,
    )

    async def prepare_both_turns():
        first = await prepare_turn_pipeline(
            user_input="Atacar",
            session_id="test-willpower",
            context=_pipeline_context(),
            turn=1,
            chronicle_name="Teste",
            operation_id="op-first-roll",
            gateway=adapter,
            target=_offline_target(),
        )
        second = await prepare_turn_pipeline(
            user_input="Rerrolar",
            session_id="test-willpower",
            context=json.loads(json.dumps(first.updated_context)),
            turn=2,
            chronicle_name="Teste",
            operation_id="op-willpower-reroll",
            gateway=adapter,
            target=_offline_target(),
        )
        return first, second

    with patch(
        "api.orchestrator_service.calculate_resolution",
        return_value=first_resolution,
    ) as mock_calc_res, patch(
        "api.orchestrator_service.apply_willpower_reroll",
        return_value=reroll_resolution,
    ) as mock_reroll:
        first, second = asyncio.run(prepare_both_turns())

    first_sheet = PlayerSheetModel(**first.updated_context["player_sheet"])
    second_sheet = PlayerSheetModel(**second.updated_context["player_sheet"])
    # Dano causado ao alvo não pode ser aplicado ao tracker do jogador.
    assert first_sheet.status.health_tracker.superficial == 0
    assert second_sheet.status.health_tracker.superficial == 0
    assert second_sheet.status.health_tracker.aggravated == 0
    assert second_sheet.status.willpower_tracker.superficial == 1
    mock_calc_res.assert_called_once()
    mock_reroll.assert_called_once()
    assert adapter.external_call_count == 4  # H0 e H1 para cada preparação.

def test_dynamic_difficulty():
    from api.rules_service import calculate_resolution, V5ActionPayload, V5ActionTarget
    payload = V5ActionPayload(
        intent="Pular", attribute="Dexterity", skill="Athletics",
        action_target=V5ActionTarget.UNOPPOSED, inferred_difficulty=5,
        is_aggressive=False, is_feeding=False, target_killed=False
    )
    with patch('random.randint', return_value=6):
        res = calculate_resolution(payload, current_hunger=0, dice_pool=4)
        assert res.successes == 4
        assert res.margin == -1
        assert res.is_success is False
        
    payload_combat = V5ActionPayload(
        intent="Atacar", attribute="Strength", skill="Brawl",
        action_target=V5ActionTarget.OPPOSED, npc_threat_level=2,
        is_aggressive=True, is_feeding=False, target_killed=False
    )
    with patch('random.randint', return_value=6):
        res = calculate_resolution(payload_combat, current_hunger=0, dice_pool=4)
        assert res.successes == 4
        assert res.margin == 2
        assert res.is_success is True

def test_lore_extraction_latency():
    import time
    from api.lore_service import get_contextual_lore
    from api.rules_service import V5ActionPayload, PlayerSheetModel, V5ActionTarget
    
    payload = V5ActionPayload(
        intent="Atacar o carniçal do príncipe com garras",
        attribute="Strength", skill="Brawl",
        power_used="feral_weapons",
        weapon_category="heavy_firearm",
        action_target=V5ActionTarget.OPPOSED,
        is_aggressive=True, is_feeding=False, target_killed=False
    )
    
    sheet = PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 3},
        skills={"Brawl": 2},
        disciplines={"feral_weapons": True},
        status={
            "blood_potency": 1, "current_hunger": 1, "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        }
    )
    
    # A medição cobre somente a extração em cache, não o I/O frio dos catálogos.
    get_contextual_lore("Eu ataco o prince e o sheriff", payload, sheet)
    start_time = time.perf_counter()
    lore_text = get_contextual_lore("Eu ataco o prince e o sheriff", payload, sheet)
    end_time = time.perf_counter()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 50, f"Lore extraction too slow: {latency_ms}ms"
    
    assert "Clã (brujah)" in lore_text
    assert "Disciplina (feral_weapons)" in lore_text
    assert "Arma (heavy_firearm)" in lore_text
    assert "NPC (prince)" in lore_text
    assert "NPC (sheriff)" in lore_text

def test_contextual_injection_limits():
    from api.lore_service import get_contextual_lore
    from api.rules_service import V5ActionPayload, PlayerSheetModel, V5ActionTarget
    
    payload = V5ActionPayload(
        intent="Falar", attribute="Charisma", skill="Persuasion",
        action_target=V5ActionTarget.UNOPPOSED,
        is_aggressive=False, is_feeding=False, target_killed=False
    )
    
    sheet = PlayerSheetModel(
        clan="tremere",
        attributes={"Charisma": 3},
        skills={"Persuasion": 2},
        disciplines={},
        status={
            "blood_potency": 1, "current_hunger": 1, "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        }
    )
    
    user_input = "O prince falou com o sheriff e o ghoul do sangue-ralo"
    lore_text = get_contextual_lore(user_input, payload, sheet)
    
    assert "NPC (prince)" in lore_text
    assert "NPC (sheriff)" in lore_text
    assert "NPC (ghoul)" in lore_text

def test_clan_catalog_validation():
    from pydantic import ValidationError
    from api.clan_service import ClanModel
    
    invalid_data = {
        "engine_data": {
            "bane_severity_multiplier": 1,
            "compulsion_dice_penalty": "INVALID_STRING_INSTEAD_OF_INT",
            "favored_disciplines": ["celerity"]
        },
        "narrative_data": {
            "faction_loyalty": "Camarilla",
            "bane_description": "...",
            "compulsion_description": "...",
            "lore_summary": "...",
            "narrator_enforcement": "...",
            "behavioral_penalty": "..."
        }
    }
    
    try:
        ClanModel(**invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "compulsion_dice_penalty" in str(e)

def test_weapon_catalog_validation():
    from pydantic import ValidationError
    from api.combat_service import WeaponModel
    
    invalid_data = {
        "engine_data": {
            "damage_modifier": 2,
            "is_concealable": True,
            "weapon_type": "MAGIC_WAND", # Invalid enum
            "is_aggravated_to_vampires": False
        },
        "narrative_data": {
            "description": "...",
            "impact_flavor": "...",
            "masquerade_threat": "..."
        }
    }
    
    try:
        WeaponModel(**invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "weapon_type" in str(e)

def test_weapon_incendiary_aggravated_math():
    from api.combat_service import calculate_damage
    # margin 0, incendiary (damage 2, is_aggravated_to_vampires=True)
    res = calculate_damage(margin=0, weapon_category="incendiary", is_bane=False, is_supernatural_target=True, weapon_damage_bonus=0)
    assert res.damage_type == "aggravated"
    assert res.total_damage == 2  # Not halved!

def test_weapon_true_faith_mechanic():
    from api.combat_service import calculate_damage
    # margin 0, holy_artifact (damage 0), is_true_faith_active=True
    res = calculate_damage(margin=0, weapon_category="holy_artifact", is_bane=False, is_supernatural_target=True, weapon_damage_bonus=0, is_true_faith_active=True)
    assert res.damage_type == "aggravated"
    assert res.total_damage == 2  # Base + 2 bonus!

def test_npc_catalog_validation():
    from pydantic import ValidationError
    from api.npc_service import NpcModel
    
    invalid_data = {
        "engine_data": {
            "base_dice_pool": 5,
            "threat_level": 6, # Invalid, max is 5
            "is_supernatural": False,
            "has_true_faith": False,
            "corruption_index": 1
        },
        "narrative_data": {
            "description": "...",
            "combat_tactics": "...",
            "social_standing": "..."
        }
    }
    
    try:
        NpcModel(**invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "threat_level" in str(e)

def test_npc_mortal_damage_math():
    from api.combat_service import calculate_damage
    # Attack on civilian (is_supernatural_target=False). Margin 4, unarmed (0)
    res_civilian = calculate_damage(margin=4, weapon_category="unarmed", is_bane=False, is_supernatural_target=False)
    assert res_civilian.total_damage == 4  # Total damage applied
    
    # Attack on sheriff (is_supernatural_target=True). Margin 4, unarmed (0)
    res_sheriff = calculate_damage(margin=4, weapon_category="unarmed", is_bane=False, is_supernatural_target=True)
    assert res_sheriff.total_damage == 2  # Halved

@pytest.mark.anyio
async def test_corruption_index_modifier():
    from api.orchestrator_service import process_turn_pipeline
    
    session_id = "test_corruption"
    context = {
        "deterministic_mechanics": {"action_target": "UNOPPOSED"},
        "player_sheet": {
            "clan": "brujah",
            "attributes": {"Charisma": 3},
            "skills": {"Persuasion": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            }
        }
    }
    
    class DummyPayload:
        is_willpower_reroll = False
        is_blood_surge = False
        power_used = None
        weapon_category = None
        is_feeding = False
        is_healing = False
        is_aggressive = False
        is_compulsion_active = False
        is_true_faith_active = False
        from api.rules_service import V5ActionTarget
        action_target = V5ActionTarget.UNOPPOSED
        inferred_difficulty = 5 # base difficulty
        npc_threat_level = 2
        attribute = type("Attr", (), {"value": "Charisma"})
        skill = type("Skill", (), {"value": "Persuasion"})
        is_bane_damage = False
        intent = "Subornar prince"
        def model_dump(self): return {}
    
    dummy_payload = DummyPayload()
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=dummy_payload), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc:
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("eu tento subornar o prince", session_id, context, 1, "chronicle")
        
        # The trusted default difficulty is 3; Prince corruption 2 reduces it by 1.
        mock_calc.assert_called_once()
        assert mock_calc.call_args[0][0].inferred_difficulty == 2

def test_discipline_catalog_validation():
    from pydantic import ValidationError
    from api.discipline_service import DisciplineModel
    
    invalid_data = {
        "engine_data": {
            "rouse_cost": 4, # Invalid, max is 3
            "scaling_stat": None,
            "dice_bonus_stat": None,
            "is_aggravated": False,
            "amalgam_req": []
        },
        "narrative_data": {
            "visual_manifestation": "...",
            "masquerade_threat": "..."
        }
    }
    
    try:
        DisciplineModel(**invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "rouse_cost" in str(e)

def test_discipline_amalgam_requirement():
    from api.discipline_service import apply_power_modifiers
    
    # fleshcrafting requires dominate. Let's not have it.
    player_sheet = {
        "disciplines": {
            "protean": 3,
            "fortitude": 1
        }
    }
    
    # Test fleshcrafting
    modifiers = apply_power_modifiers("fleshcrafting", False, player_sheet)
    
    # Should have been aborted
    assert modifiers.dice_bonus == 0
    assert modifiers.weapon_damage_bonus == 0
    assert modifiers.is_bane == False

@pytest.mark.anyio
async def test_discipline_hunger_block():
    from api.orchestrator_service import process_turn_pipeline
    
    session_id = "test_hunger_block"
    context = {
        "deterministic_mechanics": {"allowed_power_ids": ["scorpion_touch"]},
        "player_sheet": {
            "clan": "tremere",
            "attributes": {"Strength": 3},
            "skills": {"Brawl": 2},
            "disciplines": {"blood_sorcery": 2},
            "status": {
                "blood_potency": 1, "current_hunger": 5, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            }
        }
    }
    
    class DummyPayload:
        is_willpower_reroll = False
        is_blood_surge = False
        power_used = "scorpion_touch"
        weapon_category = type("WCat", (), {"value": "unarmed"})()
        is_feeding = False
        is_healing = False
        is_aggressive = True
        is_compulsion_active = False
        is_true_faith_active = False
        from api.rules_service import V5ActionTarget
        action_target = V5ActionTarget.UNOPPOSED
        inferred_difficulty = 3
        attribute = type("Attr", (), {"value": "Strength"})
        skill = type("Skill", (), {"value": "Brawl"})
        is_bane_damage = False
        intent = "Atacar"
        def model_dump(self): return {}
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=DummyPayload()), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc:
         
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        result, ctx, _ = await process_turn_pipeline(
            "uso scorpion touch", session_id, context, 1, "chronicle"
        )
        if result.startswith("[ERROR"):
            assert False, f"Pipeline Error: {result}"
        
        # Check system log
        sys_log = result
        assert "Poder falhou: scorpion_touch. Fome muito alta para Rouse Check." in sys_log

def test_potency_catalog_validation():
    from pydantic import ValidationError
    from api.rules_service import BloodPotencyModel
    
    invalid_data = {
        "engine_data": {
            "blood_surge_bonus": "A", # Invalid, must be int
            "damage_healed_per_rouse": 1,
            "bane_severity": 0,
            "rouse_reroll_level": 0
        }
    }
    
    try:
        BloodPotencyModel(**invalid_data)
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "blood_surge_bonus" in str(e)

@pytest.mark.anyio
async def test_blood_surge_potency_scaling():
    from api.orchestrator_service import process_turn_pipeline
    
    session_id = "test_surge"
    context = {
        "player_sheet": {
            "clan": "brujah",
            "predator_type": "alleycat",
            "attributes": {"Strength": 3},
            "skills": {"Brawl": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            }
        }
    }
    
    class DummyPayload:
        is_willpower_reroll = False
        is_blood_surge = True
        power_used = None
        weapon_category = type("WCat", (), {"value": "unarmed"})()
        is_feeding = False
        is_healing = False
        is_aggressive = False
        is_compulsion_active = False
        is_true_faith_active = False
        action_target = type("Target", (), {"value": "UNOPPOSED"})()
        inferred_difficulty = 3
        npc_threat_level = 2
        attribute = type("Attr", (), {"value": "Strength"})
        skill = type("Skill", (), {"value": "Brawl"})
        is_bane_damage = False
        intent = "Atacar"
        def model_dump(self): return {}
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=DummyPayload()), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc:
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("surto de sangue", session_id, context, 1, "chronicle")
        
        mock_calc.assert_called_once()
        # Strength (3) + Brawl (2) + Surge (1 for Potency 1) = 6
        assert mock_calc.call_args[1]["dice_pool"] == 6

@pytest.mark.anyio
async def test_healing_potency_scaling():
    from api.orchestrator_service import process_turn_pipeline
    
    session_id = "test_healing"
    context = {
        "player_sheet": {
            "clan": "brujah",
            "predator_type": "alleycat",
            "attributes": {"Strength": 3},
            "skills": {"Brawl": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 5, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            }
        }
    }
    
    class DummyPayload:
        is_willpower_reroll = False
        is_blood_surge = False
        power_used = None
        weapon_category = type("WCat", (), {"value": "unarmed"})()
        is_feeding = False
        is_healing = True
        is_aggressive = False
        is_compulsion_active = False
        is_true_faith_active = False
        action_target = type("Target", (), {"value": "UNOPPOSED"})()
        inferred_difficulty = 3
        npc_threat_level = 2
        attribute = type("Attr", (), {"value": "Strength"})
        skill = type("Skill", (), {"value": "Brawl"})
        is_bane_damage = False
        intent = "Curar"
        def model_dump(self): return {}
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=DummyPayload()), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc:
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        _, saved_context, _ = await process_turn_pipeline(
            "curar ferimento", session_id, context, 1, "chronicle"
        )
        
        # Superficial was 5. Potency 1 heals 1. New superficial is 4.
        assert saved_context["player_sheet"]["status"]["health_tracker"]["superficial"] == 4
        
@pytest.mark.anyio
async def test_clan_compulsion_engine_math():
    from api.orchestrator_service import process_turn_pipeline
    from api.main import SessionData
    
    session_id = "test_compulsion"
    context = {
        "deterministic_mechanics": {"is_compulsion_active": True},
        "player_sheet": {
            "clan": "brujah",
            "attributes": {"Strength": 3},
            "skills": {"Brawl": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1, "current_hunger": 1, "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            }
        }
    }
    
    class DummyPayload:
        is_willpower_reroll = False
        is_blood_surge = False
        power_used = None
        weapon_category = None
        is_feeding = False
        is_healing = False
        is_aggressive = False
        is_compulsion_active = True
        attribute = type("Attr", (), {"value": "Strength"})
        skill = type("Skill", (), {"value": "Brawl"})
        is_bane_damage = False
        intent = "Atacar"
        def model_dump(self): return {}
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=DummyPayload()), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc:
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline(
            "Fazer teste de Força + Briga",
            session_id,
            context,
            1,
            "chronicle",
        )
        
        # Strength (3) + Brawl (2) = 5
        # Compulsion Penalty = -2
        # Final Pool should be 3
        mock_calc.assert_called_once()
        assert mock_calc.call_args[1]["dice_pool"] == 3

def test_xp_award_logic():
    from api.progression_service import award_session_xp
    from api.rules_service import PlayerSheetModel
    
    sheet = PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 3},
        skills={"Brawl": 2},
        disciplines={},
        status={
            "blood_potency": 1, "current_hunger": 1, "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        },
        available_xp=5
    )
    
    award_session_xp(sheet, 2)
    assert sheet.available_xp == 7

def test_upgrade_math_calculation():
    from api.progression_service import calculate_upgrade_cost
    
    # Atributo indo para o nível 3 = 3 * 5 = 15 XP
    attr_cost = calculate_upgrade_cost("attribute", 3)
    assert attr_cost == 15
    
    # out_of_clan_discipline para o nível 2 = 2 * 7 = 14 XP
    disc_cost = calculate_upgrade_cost("out_of_clan_discipline", 2)
    assert disc_cost == 14

def test_insufficient_xp_block():
    from api.progression_service import purchase_upgrade
    from api.rules_service import PlayerSheetModel
    
    sheet = PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 2},
        skills={"Brawl": 2},
        disciplines={},
        status={
            "blood_potency": 1, "current_hunger": 1, "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        },
        available_xp=10
    )
    
    # Try to purchase Attribute to 3. Cost is 15. We have 10.
    success, result_sheet = purchase_upgrade(sheet, "attribute", "Strength", 3)
    
    assert success is False
    assert result_sheet.available_xp == 10
    assert result_sheet.attributes["Strength"] == 2


@pytest.mark.parametrize(
    ("category", "trait", "level", "code"),
    (
        ("unknown", "Strength", 3, "unknown_category"),
        ("attribute", "Unknown", 3, "unknown_trait"),
        ("attribute", "Strength", 4, "invalid_transition"),
        ("clan_discipline", "unknown_power", 1, "unknown_trait"),
        ("specialty", "Ambush", 1, "unsupported_category"),
    ),
)
def test_invalid_upgrade_is_typed_and_preserves_original(
    category, trait, level, code
):
    from api.progression_service import ProgressionValidationError, purchase_upgrade
    from api.rules_service import PlayerSheetModel

    sheet = PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 2},
        skills={"Brawl": 2},
        disciplines={},
        status={
            "blood_potency": 1,
            "current_hunger": 1,
            "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0},
        },
        available_xp=100,
    )
    before = sheet.model_dump()

    with pytest.raises(ProgressionValidationError) as captured:
        purchase_upgrade(sheet, category, trait, level)

    assert captured.value.code == code
    assert sheet.model_dump() == before


def test_successful_upgrade_returns_copy_and_preserves_input():
    from api.progression_service import purchase_upgrade
    from api.rules_service import PlayerSheetModel

    sheet = PlayerSheetModel(
        attributes={"Strength": 2},
        skills={"Brawl": 2},
        disciplines={},
        status={
            "blood_potency": 1,
            "current_hunger": 1,
            "humanity": 7,
            "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0},
        },
        available_xp=20,
    )

    success, updated = purchase_upgrade(sheet, "attribute", "Strength", 3)

    assert success is True
    assert sheet.attributes["Strength"] == 2
    assert sheet.available_xp == 20
    assert updated.attributes["Strength"] == 3
    assert updated.available_xp == 5


def test_endpoint_xp_award(isolated_persistence):
    from api.state_service import sync_event_from_context, save_session_state
    session_id = "test_xp_award"
    
    # Prepara estado em disco
    initial_context = {
        "player_sheet": {
            "clan": "brujah",
            "attributes": {"Strength": 3},
            "skills": {"Brawl": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1,
                "current_hunger": 1,
                "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            },
            "available_xp": 5
        }
    }
    event_data = sync_event_from_context(session_id, initial_context)
    
    # Persiste estado de teste de forma síncrona/segura
    async def prep():
        await save_session_state(session_id, event_data)
    asyncio.run(prep())
    
    response = client.post(f"/session/{session_id}/xp/award?amount=3")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["player_sheet"]["player_sheet"]["available_xp"] == 8

def test_endpoint_xp_upgrade(isolated_persistence):
    from api.state_service import sync_event_from_context, save_session_state
    session_id = "test_xp_upgrade"
    
    initial_context = {
        "player_sheet": {
            "clan": "brujah",
            "attributes": {"Strength": 2},
            "skills": {"Brawl": 2},
            "disciplines": {},
            "status": {
                "blood_potency": 1,
                "current_hunger": 1,
                "humanity": 7,
                "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
            },
            "available_xp": 20
        }
    }
    event_data = sync_event_from_context(session_id, initial_context)
    
    async def prep():
        await save_session_state(session_id, event_data)
    asyncio.run(prep())
    
    # Tenta melhorar Força para 3 (custo 15). Temos 20.
    response = client.post(f"/session/{session_id}/xp/upgrade", json={
        "trait_category": "attribute",
        "trait_name": "Strength",
        "new_level": 3
    })
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["state"]["player_sheet"]["player_sheet"]["available_xp"] == 5
    assert res_data["state"]["player_sheet"]["player_sheet"]["attributes"]["Strength"] == 3


@pytest.mark.anyio
async def test_narrator_uses_compact_projection_instead_of_full_sheet(
    isolated_persistence,
):
    from api.orchestrator_service import run_narrator_stream

    proposal = _scene_proposal_payload()
    adapter = _SequencedOfflineLLM([proposal])
    player_sheet = {
        "clan": "gangrel",
        "predator_type": "alleycat",
        "status": {
            "current_hunger": 3,
            "humanity": 6,
            "health_tracker": {"size": 7, "superficial": 1, "aggravated": 0},
            "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}
        }
    }

    chunks = [
        chunk
        async for chunk in run_narrator_stream(
            "Eu corro",
            "Sucesso",
            player_sheet=player_sheet,
            gateway=adapter,
            target=_offline_target(),
        )
    ]

    assert chunks == [f"{proposal['narrative']}\n\n{proposal['player_prompt']}"]
    assert adapter.external_call_count == 1
    request = adapter.requests[0]
    system_prompt = request.messages[0].content
    assert "Clã: gangrel" not in system_prompt
    assert "Tipo de Predador: alleycat" not in system_prompt
    assert "Fome: 3" not in system_prompt
    assert "Humanidade: 6" not in system_prompt
    assert "improviso coerente" in system_prompt
    assert "nunca escolha ação" in system_prompt
    assert "CONFIDENCIAIS" in system_prompt
    assert "35 a 70 palavras" in system_prompt
    assert request.messages[1].content == "Sucesso"

@pytest.mark.anyio
async def test_llm_scene_direction_latency():
    import time

    proposal = _scene_proposal_payload()
    adapter = _SequencedOfflineLLM([proposal])
    from api.orchestrator_service import run_narrator_stream

    start = time.perf_counter()
    async for chunk in run_narrator_stream(
        "Olá",
        "Ação comum",
        gateway=adapter,
        target=_offline_target(),
    ):
        latency = (time.perf_counter() - start) * 1000
        assert chunk == f"{proposal['narrative']}\n\n{proposal['player_prompt']}"
        assert latency < 500, f"Latência sintética muito alta: {latency}ms"
        break
