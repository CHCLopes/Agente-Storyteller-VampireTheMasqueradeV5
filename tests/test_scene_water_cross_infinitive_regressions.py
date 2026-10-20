"""L79: explicit water crossing the record is damage, not player travel."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

TEXT='Você aguarda no Arquivo, e a água continua sobre a bancada baixa até atravessar completamente o registro. As páginas se desfazem sob a umidade, e o texto se torna irrecuperável. Mara observa o volume perdido, com as mãos afastadas do papel encharcado. “Está perdido. A água apagou o conteúdo do registro”, ela diz, enquanto o gotejamento prossegue pelas frestas.'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Aguardo',npc_aliases=('Mara',))

def test_water_crosses_not_player():
    assert check(TEXT).narrative==TEXT

@pytest.mark.parametrize('text',[TEXT+' Você atravessa a Galeria.',
    TEXT+' Você abre a porta.',TEXT.replace('a água continua','você continua'),
    TEXT.replace('atravessar completamente o registro.','atravessar completamente o registro e você abre a porta.')])
def test_player_actions_not_masked(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)
