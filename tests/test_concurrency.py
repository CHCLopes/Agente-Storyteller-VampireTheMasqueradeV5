import asyncio
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH para poder importar a api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.state_service import (
    save_session_state,
    load_session_state,
    StateUpdateEvent,
    CharacterModel,
    TrackersModel,
    TrackerDetail,
    CharacterAttributes,
    ContextModel
)

async def writer_task(task_id: int, session_id: str):
    # Cria uma variação no estado de fome
    fome_valor = task_id % 6  # 0 a 5
    
    event = StateUpdateEvent(
        session_id=session_id,
        character=CharacterModel(
            id="karl_test",
            trackers=TrackersModel(
                health=TrackerDetail(superficial=0, aggravated=0, max=7),
                willpower=TrackerDetail(superficial=0, aggravated=0, max=6)
            ),
            attributes=CharacterAttributes(self_control=3, resolve=3),
            fome=fome_valor,
            status="ACTIVE"
        ),
        context=ContextModel(
            current_state="ACTIVE",
            blocking=False
        )
    )
    
    print(f"[Task {task_id}] Iniciando gravação de save com fome={fome_valor}...")
    await save_session_state(session_id, event)
    print(f"[Task {task_id}] Gravação concluída com sucesso.")

async def main():
    session_id = "concurrency_test_session"
    
    # Executa 5 escritas concorrentes usando asyncio.gather
    print("Iniciando simulação de 5 escritas simultâneas concorrentes...")
    tasks = [writer_task(i, session_id) for i in range(1, 6)]
    await asyncio.gather(*tasks)
    
    # Carrega o estado resultante para validar a integridade do JSON salvo
    print("\nCarregando estado final do save para validação...")
    loaded_event = await load_session_state(session_id)
    if loaded_event is not None:
        print("Validação Pydantic Concluída com Sucesso!")
        print(f"Session ID carregado: {loaded_event.session_id}")
        print(f"Última fome registrada: {loaded_event.character.fome}")
        print(f"Status do Personagem: {loaded_event.character.status}")
    else:
        print("ERRO: O arquivo final está corrompido ou não foi carregado corretamente.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
