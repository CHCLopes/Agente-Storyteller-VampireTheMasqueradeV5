"""Material in a conditional offer is not the verb matar."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

TEXT='Mara aponta para a bancada baixa no Arquivo, onde o registro continua ameaçado. “O registro ainda corre risco. Há uma superfície seca na Galeria, caso você precise proteger o material.” O registro permanece sobre a madeira, sem mudar de posição.'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Qual é a tarefa?',npc_aliases=('Mara',))

def test_material_noun_not_killing():
    assert check(TEXT).narrative==TEXT

@pytest.mark.parametrize('extra',[' Você mata Mara.',' Você abre a porta.',' Você matou Mara.'])
def test_material_noun_does_not_hide_later_action(extra):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(TEXT+extra)
