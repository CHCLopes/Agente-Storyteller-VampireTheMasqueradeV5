import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api.main import app
from api.rules_service import V5ActionPayload, PlayerSheetModel
from api.combat_service import calculate_damage, apply_damage_to_tracker
from api.discipline_service import apply_power_modifiers
from api.state_service import SAVE_DIR

client = TestClient(app)

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

@patch('httpx.AsyncClient.post')
@patch('api.orchestrator_service.rouse_check')
def test_pipeline_integration_feral_weapons(mock_rouse_check, mock_httpx_post):
    from api.economy_service import RouseResult
    from api.orchestrator_service import calculate_damage
    mock_rouse_check.return_value = RouseResult(new_hunger=2, rouse_failures=1, frenzy_warning=False, summary="Mocked Rouse Check")
    
    class MockResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": self.content}}]}

    h1_json = """{
        "intent": "Atacar",
        "attribute": "Strength",
        "skill": "Brawl",
        "power_used": "feral_weapons",
        "weapon_category": "unarmed",
        "is_aggressive": true,
        "is_feeding": false,
        "target_killed": false,
        "is_bane_damage": false,
        "is_blood_surge": false,
        "is_willpower_reroll": false
    }"""
    mock_httpx_post.side_effect = [MockResponse(h1_json), MockResponse("Narrativa do Mestre")]
    
    from api.main import active_sessions, SessionData, StateEnum
    active_sessions["test_session"] = SessionData()
    active_sessions["test_session"].state = StateEnum.PLAYING
    
    with patch('api.orchestrator_service.calculate_damage', wraps=calculate_damage) as spy_dmg, \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc_res, \
         patch('api.main.run_narrator_stream') as mock_narrator_stream:
         
        from api.rules_service import ResolutionResult
        mock_calc_res.return_value = ResolutionResult(successes=4, is_success=True, bestial_failure=False, messy_critical=False, summary="Roll Ok", normal_rolls=[], hunger_rolls=[])
        
        async def dummy_generator(*args, **kwargs):
            yield "Narrativa"
        mock_narrator_stream.side_effect = dummy_generator
        
        # O arquivo save será gerado aqui
        save_path = os.path.join(SAVE_DIR, "test_session.json")
        if os.path.exists(save_path): os.remove(save_path)
        
        with client.websocket_connect("/ws/session/test_session") as websocket:
            websocket.send_text("Ataco com feral weapons")
            data = websocket.receive_json() # receive state_update
            assert data["action"] == "state_update"
            
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break
        mock_rouse_check.assert_called_once()
        # Strength 3 + Brawl 2 = 5
        assert mock_calc_res.call_args[1]['dice_pool'] == 5
        assert spy_dmg.call_args[1]['weapon_damage_bonus'] == 2
        
        # Testar se o Snapshot pré-rolagem e autosave ocorreram
        context = active_sessions["test_session"].context
        assert context["pre_roll_snapshot"] is not None
        assert context["pre_roll_snapshot"]["health_tracker"]["aggravated"] == 0
        
        # Testar se o save sintético foi criado em disco
        assert os.path.exists(save_path)
        with open(save_path, "r", encoding="utf-8") as f:
            save_data = json.load(f)
            assert save_data["session_id"] == "test_session"

@patch('httpx.AsyncClient.post')
def test_pipeline_willpower_reroll(mock_httpx_post):
    class MockResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": self.content}}]}

    h1_json_first = """{
        "intent": "Atacar",
        "attribute": "Strength",
        "skill": "Brawl",
        "power_used": null,
        "weapon_category": "unarmed",
        "is_aggressive": true,
        "is_feeding": false,
        "target_killed": false,
        "is_bane_damage": false,
        "is_blood_surge": false,
        "is_willpower_reroll": false,
        "action_target": "OPPOSED",
        "inferred_difficulty": 3,
        "npc_threat_level": 2
    }"""
    
    h1_json_reroll = """{
        "intent": "Rerrolar",
        "attribute": "Strength",
        "skill": "Brawl",
        "power_used": null,
        "weapon_category": "unarmed",
        "is_aggressive": false,
        "is_feeding": false,
        "target_killed": false,
        "is_bane_damage": false,
        "is_blood_surge": false,
        "is_willpower_reroll": true,
        "action_target": "OPPOSED",
        "inferred_difficulty": 3,
        "npc_threat_level": 2
    }"""
    
    class MockResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": self.content}}]}

    mock_httpx_post.side_effect = [
        MockResponse(h1_json_first),
        MockResponse(h1_json_reroll)
    ]
    
    from api.main import active_sessions, SessionData, StateEnum
    session = SessionData()
    session.state = StateEnum.PLAYING
    active_sessions["test_wp"] = session
    
    with patch('api.orchestrator_service.calculate_resolution') as mock_calc_res, \
         patch('api.orchestrator_service.apply_willpower_reroll') as mock_reroll, \
         patch('api.main.run_narrator_stream') as mock_narrator_stream:
        
        from api.rules_service import ResolutionResult
        res_first = ResolutionResult(successes=4, is_success=True, bestial_failure=False, messy_critical=False, summary="Roll", normal_rolls=[6,6,6,6], hunger_rolls=[], margin=2)
        mock_calc_res.return_value = res_first
        
        async def dummy_generator(*args, **kwargs):
            yield "Narrativa"
        mock_narrator_stream.side_effect = dummy_generator
        
        # Turn 1: Attack
        with client.websocket_connect("/ws/session/test_wp") as websocket:
            websocket.send_text("Atacar")
            data = websocket.receive_json() # state_update
            assert data["action"] == "state_update"
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break
        
        sheet = PlayerSheetModel(**session.context["player_sheet"])
        # Margin 2, Unarmed (+0), Damage = ceil(2/2) = 1 Superficial
        assert sheet.status.health_tracker.superficial == 1
        
        # Turn 2: Willpower Reroll (Simulating a better roll)
        res_reroll = ResolutionResult(successes=6, is_success=True, bestial_failure=False, messy_critical=False, summary="Reroll", normal_rolls=[6,6,6,6,6,6], hunger_rolls=[], margin=4)
        mock_reroll.return_value = res_reroll
        
        with client.websocket_connect("/ws/session/test_wp") as websocket:
            websocket.send_text("Rerrolar")
            data = websocket.receive_json() # state_update
            assert data["action"] == "state_update"
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break
        
        sheet = PlayerSheetModel(**session.context["player_sheet"])
        # It should rollback to 0, and then apply Margin 4 damage: ceil(4/2) = 2 Superficial
        assert sheet.status.health_tracker.superficial == 2
        assert sheet.status.health_tracker.aggravated == 0
        assert sheet.status.willpower_tracker.superficial == 1

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
    
    start_time = time.time()
    lore_text = get_contextual_lore("Eu ataco o prince e o sheriff", payload, sheet)
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 50, f"Lore extraction too slow: {latency_ms}ms"
    
    assert "Clã (brujah)" in lore_text
    assert "Disciplina (feral_weapons)" in lore_text
    assert "Arma (heavy_firearm)" in lore_text
    assert "NPC (prince)" not in lore_text

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
    
    blocks = lore_text.strip().split("\\n")
    assert len(blocks) <= 4
    
    assert "NPC (prince)" in lore_text
    assert "NPC (sheriff)" not in lore_text

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
        intent = "Subornar politician"
        def model_dump(self): return {}
    
    dummy_payload = DummyPayload()
    
    with patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=dummy_payload), \
         patch('api.orchestrator_service.calculate_resolution') as mock_calc, \
         patch('api.orchestrator_service.save_session_state'):
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("eu tento subornar o politician", session_id, context, 1, "chronicle")
        
        # politician corruption_index is 5.
        # Reduction is 5 - 1 = 4.
        # Base difficulty 5 - 4 = 1.
        mock_calc.assert_called_once()
        assert mock_calc.call_args[0][0].inferred_difficulty == 1

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
         patch('api.orchestrator_service.calculate_resolution') as mock_calc, \
         patch('api.orchestrator_service.save_session_state'):
         
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        result, ctx = await process_turn_pipeline("uso scorpion touch", session_id, context, 1, "chronicle")
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
                "blood_potency": 3, "current_hunger": 1, "humanity": 7,
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
         patch('api.orchestrator_service.calculate_resolution') as mock_calc, \
         patch('api.orchestrator_service.save_session_state'):
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("surto de sangue", session_id, context, 1, "chronicle")
        
        mock_calc.assert_called_once()
        # Strength (3) + Brawl (2) + Surge (2 for Potency 3) = 7
        assert mock_calc.call_args[1]["dice_pool"] == 7

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
                "blood_potency": 4, "current_hunger": 1, "humanity": 7,
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
         patch('api.orchestrator_service.calculate_resolution') as mock_calc, \
         patch('api.orchestrator_service.save_session_state') as mock_save:
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("curar ferimento", session_id, context, 1, "chronicle")
        
        # Superifical was 5. Potency 4 heals 3. New superficial should be 2.
        saved_context = mock_save.call_args[0][1]
        assert saved_context["player_sheet"]["status"]["health_tracker"]["superficial"] == 2
        
@pytest.mark.anyio
async def test_clan_compulsion_engine_math():
    from api.orchestrator_service import process_turn_pipeline
    from api.main import SessionData
    
    session_id = "test_compulsion"
    context = {
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
         patch('api.orchestrator_service.calculate_resolution') as mock_calc, \
         patch('api.orchestrator_service.save_session_state'):
        from api.rules_service import ResolutionResult
        mock_calc.return_value = ResolutionResult(successes=1, is_success=True, bestial_failure=False, messy_critical=False, summary="ok", normal_rolls=[], hunger_rolls=[], margin=0)
        
        await process_turn_pipeline("user input", session_id, context, 1, "chronicle")
        
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
