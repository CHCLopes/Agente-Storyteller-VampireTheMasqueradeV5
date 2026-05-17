import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app
from api.rules_service import V5ActionPayload, PlayerSheetModel
from api.combat_service import calculate_damage, apply_damage_to_tracker
from api.discipline_service import apply_power_modifiers
from api.orchestrator_service import SAVE_DIR

client = TestClient(app)

def test_health_performance():
    response = client.get("/health")
    assert response.status_code == 200

def test_playersheet_validation():
    valid_data = {
        "attributes": {"Strength": 3},
        "skills": {"Brawl": 2},
        "disciplines": {"awe": True},
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
        "weapon_category": "UNARMED",
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
         patch('api.orchestrator_service.calculate_resolution') as mock_calc_res:
         
        from api.rules_service import ResolutionResult
        mock_calc_res.return_value = ResolutionResult(successes=4, is_success=True, bestial_failure=False, messy_critical=False, summary="Roll Ok", normal_rolls=[], hunger_rolls=[])
        
        # O arquivo save será gerado aqui
        save_path = os.path.join(SAVE_DIR, "test_session.json")
        if os.path.exists(save_path): os.remove(save_path)
        
        response = client.post("/chat", json={"user_input": "Ataco com feral weapons", "session_id": "test_session"})
        
        assert response.status_code == 200
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
        "weapon_category": "UNARMED",
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
        "weapon_category": "UNARMED",
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
        MockResponse(h1_json_first), MockResponse("Narrativa 1"),
        MockResponse(h1_json_reroll), MockResponse("Narrativa 2")
    ]
    
    from api.main import active_sessions, SessionData, StateEnum
    session = SessionData()
    session.state = StateEnum.PLAYING
    active_sessions["test_wp"] = session
    
    with patch('api.orchestrator_service.calculate_resolution') as mock_calc_res, \
         patch('api.orchestrator_service.apply_willpower_reroll') as mock_reroll:
        
        from api.rules_service import ResolutionResult
        res_first = ResolutionResult(successes=4, is_success=True, bestial_failure=False, messy_critical=False, summary="Roll", normal_rolls=[6,6,6,6], hunger_rolls=[], margin=2)
        mock_calc_res.return_value = res_first
        
        # Turn 1: Attack
        resp1 = client.post("/chat", json={"user_input": "Atacar", "session_id": "test_wp"})
        assert resp1.status_code == 200
        
        sheet = PlayerSheetModel(**session.context["player_sheet"])
        # Margin 2, Unarmed (+0), Damage = ceil(2/2) = 1 Superficial
        assert sheet.status.health_tracker.superficial == 1
        
        # Turn 2: Willpower Reroll (Simulating a better roll)
        res_reroll = ResolutionResult(successes=6, is_success=True, bestial_failure=False, messy_critical=False, summary="Reroll", normal_rolls=[6,6,6,6,6,6], hunger_rolls=[], margin=4)
        mock_reroll.return_value = res_reroll
        
        resp2 = client.post("/chat", json={"user_input": "Rerrolar", "session_id": "test_wp"})
        assert resp2.status_code == 200
        
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
