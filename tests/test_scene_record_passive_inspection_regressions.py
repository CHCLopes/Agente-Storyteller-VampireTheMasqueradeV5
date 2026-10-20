"""Future passive record examination does not execute a player action."""
import pytest
from api.narrative_source_profile import validate_source_proposal
from api.scene_director_service import SceneProposalError
from api.scene_service import SceneState

TEXT='Mara aponta para o registro ameaçado sobre a bancada baixa do Arquivo. “A tarefa é impedir que ele se danifique mais e tentar recuperar o conteúdo antes que a água o alcance.” Ela indica a passagem para a Galeria. “Há uma superfície seca lá; se você conseguir levá-lo até ela, o registro ficará em melhores condições para ser examinado.”'

def check(text):
    return validate_source_proposal({'n':text,'q':'O que você faz agora?'},facts=(),
        current_scene=SceneState(location='Arquivo',npcs_present=('Mara',)),
        player_input='Qual é a tarefa?',npc_aliases=('Mara',))

def test_record_future_passive_does_not_execute_inspection():
    assert check(TEXT).narrative==TEXT

@pytest.mark.parametrize('text',[
    TEXT+' Você examina o registro.',
    TEXT+' Você abre a porta.',
    TEXT.replace('o registro ficará em melhores condições para ser examinado','você examina o registro'),
    TEXT.replace('ser examinado','ser examinado e você abre a porta'),
])
def test_future_passive_never_hides_executed_action(text):
    with pytest.raises(SceneProposalError,match='scene_player_agency_violation'):
        check(text)


@pytest.mark.asyncio
async def test_passive_task_dialogue_commit_restart_replay(tmp_path,monkeypatch):
    import test_campaign_natural_refusal_regressions as sequence
    monkeypatch.setattr(sequence,'TASK',TEXT)
    await sequence.test_natural_refusal_help_rescue_without_secrecy_recap(tmp_path,monkeypatch)
