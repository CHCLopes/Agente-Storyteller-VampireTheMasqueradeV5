"""L77: das partes ainda legiveis is a nominal complement, not departure."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

TEXT='Você examina o registro sobre a bancada baixa no Arquivo e consegue recuperar informação útil das partes ainda legíveis. O conteúdo não é restaurado por inteiro; páginas danificadas continuam incompletas. Mara acompanha o resultado e diz: “Conseguimos extrair algo importante, mas o registro ainda está parcial.”'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Examino o registro',npc_aliases=('Mara',))

def test_fragment_noun():
    assert check(TEXT).narrative==TEXT

@pytest.mark.parametrize('extra',[' Você parte para a Galeria.',' Você partes para a Galeria.',
    ' Você abre a porta.', ' Você mente para Mara.'])
def test_departure_or_later_action_not_masked(extra):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(TEXT+extra)
