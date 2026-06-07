import pytest
from unittest.mock import patch
from api.rules_service import PlayerSheetModel, calculate_remorse, TrackerModel, StatusModel, ResolutionResult

def create_dummy_sheet(humanity: int = 7, stains: int = 0) -> PlayerSheetModel:
    return PlayerSheetModel(
        clan="brujah",
        attributes={"Strength": 3},
        skills={"Brawl": 2},
        disciplines={},
        status=StatusModel(
            blood_potency=1,
            current_hunger=1,
            humanity=humanity,
            stains=stains,
            health_tracker=TrackerModel(size=7, superficial=0, aggravated=0),
            willpower_tracker=TrackerModel(size=5, superficial=0, aggravated=0)
        )
    )

def test_remorse_no_stains():
    # stains == 0: nenhuma rolagem, estado inalterado
    sheet = create_dummy_sheet(humanity=7, stains=0)
    with patch('api.rules_service._roll_v5_dice') as mock_roll:
        result = calculate_remorse(sheet)
        mock_roll.assert_not_called()
        assert result.status.humanity == 7
        assert result.status.stains == 0

def test_remorse_failure():
    # stains > 0 com falha (0 sucessos): humanity decrementado, stains zerado
    sheet = create_dummy_sheet(humanity=7, stains=3)
    
    mock_roll_res = ResolutionResult(
        successes=0,
        is_success=False,
        bestial_failure=False,
        messy_critical=False,
        summary="Falha",
        normal_rolls=[1, 2, 3],
        hunger_rolls=[]
    )
    
    with patch('api.rules_service._roll_v5_dice', return_value=mock_roll_res) as mock_roll:
        result = calculate_remorse(sheet)
        mock_roll.assert_called_once_with(dice_pool=7, hunger=0, difficulty=1) # 10 - 3 = 7 dados
        assert result.status.humanity == 6
        assert result.status.stains == 0

def test_remorse_success():
    # stains > 0 com sucesso (>= 1 sucessos): humanity mantido, stains zerado
    sheet = create_dummy_sheet(humanity=7, stains=3)
    
    mock_roll_res = ResolutionResult(
        successes=1,
        is_success=True,
        bestial_failure=False,
        messy_critical=False,
        summary="Sucesso",
        normal_rolls=[6, 2, 3],
        hunger_rolls=[]
    )
    
    with patch('api.rules_service._roll_v5_dice', return_value=mock_roll_res) as mock_roll:
        result = calculate_remorse(sheet)
        mock_roll.assert_called_once_with(dice_pool=7, hunger=0, difficulty=1) # 10 - 3 = 7 dados
        assert result.status.humanity == 7
        assert result.status.stains == 0
