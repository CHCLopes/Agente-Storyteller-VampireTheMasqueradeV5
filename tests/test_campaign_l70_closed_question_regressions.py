"""L70 closed question remains rejected; no guard relaxation."""
import pytest
from api.scene_director_service import _validate_player_prompt,SceneProposalError

def test_observed_yes_no_question_remains_rejected():
    with pytest.raises(SceneProposalError):
        _validate_player_prompt('Você quer levar o registro até a superfície seca na Galeria?',player_aliases=(),npc_aliases=('Mara',))

def test_existing_open_question_remains_valid():
    _validate_player_prompt('O que você faz agora?',player_aliases=(),npc_aliases=('Mara',))
