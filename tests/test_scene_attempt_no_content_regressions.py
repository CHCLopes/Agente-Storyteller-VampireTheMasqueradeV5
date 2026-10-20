"""L81: explicit failed recovery need not include conteudo algum."""
import pytest
from api.scene_director_service import SceneProposalError,validate_mechanical_narrative

TEXT='Você examina o registro sobre a bancada baixa no Arquivo, mas a tentativa não recupera conteúdo. A água já molhou suas páginas, deixando-as úmidas e frágeis. Mara se aproxima, observa as folhas encharcadas e diz: “Ainda pode haver algo legível, mas precisamos tirá-lo daqui com cuidado.”'
MARKER='A tentativa não recupera conteúdo.'

def test_explicit_no_recovery_honors_failure():
    validate_mechanical_narrative(TEXT,outcome='failure')

@pytest.mark.parametrize('text',[MARKER[:-1]+'?', 'Se '+MARKER.lower(),
    'Mara diz: “'+MARKER+'”', MARKER.replace('não recupera','recupera'),
    'Mara deseja que a tentativa não recupere conteúdo.'])
def test_nonassertions_not_failure(text):
    with pytest.raises(SceneProposalError,match='scene_failure_not_honored'):
        validate_mechanical_narrative(text,outcome='failure')

@pytest.mark.parametrize('extra',[' Você encontra uma pista.', ' Você recupera informações úteis.'])
def test_does_not_hide_later_goal(extra):
    with pytest.raises(SceneProposalError,match='scene_failure_granted_goal'):
        validate_mechanical_narrative(TEXT+extra,outcome='failure')
