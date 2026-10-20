"""L78: explicitly named drops advance, not the NPC's player interlocutor."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

TEXT='Você aguarda no Arquivo. A infiltração aumenta junto à bancada baixa, e Mara percebe o risco imediato antes que a água alcance o registro, que continua seco sobre a bancada. Ela se volta para você, com a atenção presa às gotas que avançam pela estrutura. “A água está se aproximando. O registro ainda está seco, mas não por muito tempo”, diz Mara, apontando para o objeto sem tocá-lo. O aviso pesa no ambiente enquanto a posição do registro permanece a mesma, sobre a bancada baixa no Arquivo.'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

def test_drops_not_player():
    assert check(TEXT).narrative==TEXT

@pytest.mark.parametrize('extra',[' Você avança pela estrutura.', ' Você abre a porta.',
    ' Você avança para Mara.', ' Você mente para Mara.'])
def test_later_player_actions_not_hidden(extra):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(TEXT+extra)
