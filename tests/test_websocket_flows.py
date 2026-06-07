import sys
import os
import json
import asyncio
from fastapi.testclient import TestClient

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from api.state_service import SAVE_DIR

def setup_save_file(session_id: str, fome: int, status: str, aggravated_health: int = 0):
    """
    Cria um arquivo de save com os valores fornecidos para teste.
    """
    path = os.path.join(SAVE_DIR, f"{session_id}.json")
    save_data = {
        "event": "state_update",
        "action": "state_update",
        "session_id": session_id,
        "timestamp": 1717531603,
        "character": {
            "id": "karl_brujah",
            "trackers": {
                "health": { "superficial": 0, "aggravated": aggravated_health, "max": 7 },
                "willpower": { "superficial": 0, "aggravated": 0, "max": 5 }
            },
            "attributes": { "self_control": 3, "resolve": 3 },
            "fome": fome,
            "status": status
        },
        "context": {
            "current_state": status,
            "blocking": status != "ACTIVE",
            "pending_roll": {
                "type": "FRENZY_RESISTANCE",
                "pool": ["self_control", "resolve"],
                "difficulty": 3
            } if status == "FRENZY_CHECK" else None
        },
        "player_sheet": {
            "player_sheet": {
                "clan": "brujah",
                "predator_type": "alleycat",
                "attributes": { "Strength": 3, "Composure": 3, "Resolve": 3 },
                "skills": {},
                "disciplines": {},
                "status": {
                    "blood_potency": 1,
                    "current_hunger": fome,
                    "humanity": 7,
                    "health_tracker": { "size": 7, "superficial": 0, "aggravated": aggravated_health },
                    "willpower_tracker": { "size": 5, "superficial": 0, "aggravated": 0 }
                }
            },
            "last_action_cache": None,
            "pre_roll_snapshot": None
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=4)

def teardown_save_file(session_id: str):
    path = os.path.join(SAVE_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)

def test_torpor_block():
    """
    Passo 2: Testa se um personagem em status TORPOR é bloqueado imediatamente.
    """
    session_id = "test_session_torpor"
    setup_save_file(session_id, fome=1, status="TORPOR", aggravated_health=7)
    
    client = TestClient(app)
    try:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            # Consome o payload inicial enviado na conexão
            websocket.receive_json()
            websocket.receive_json() # chat_response "Iniciado."
            
            # Envia mensagem do jogador
            websocket.send_text("Tento socar o inimigo.")
            
            # Recebe resposta
            response = websocket.receive_json()
            assert response["action"] == "error"
            assert "[BLOQUEIO DE FLUXO] O personagem está em TORPOR" in response["message"]
            print("[Passo 2 - Torpor Block] Teste passou com sucesso!")
            
    finally:
        teardown_save_file(session_id)

def test_frenzy_trigger_and_resolution():
    """
    Passo 3: Testa se a fome crítica >= 5 força FRENZY_CHECK e bloqueia,
    e testa a posterior tentativa de resolução.
    """
    session_id = "test_session_frenzy"
    setup_save_file(session_id, fome=5, status="ACTIVE")
    
    client = TestClient(app)
    try:
        with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
            # Consome payload inicial
            websocket.receive_json()
            websocket.receive_json()
            
            # Envia uma ação comum. Como fome está em 5, o pipeline deve processar
            # e re-sincronizar forçando o status para FRENZY_CHECK.
            websocket.send_text("Olho ao meu redor.")
            
            # Recebe o state_update
            state_update = websocket.receive_json()
            assert state_update["event"] == "state_update"
            assert state_update["character"]["status"] == "FRENZY_CHECK"
            assert state_update["context"]["current_state"] == "FRENZY_CHECK"
            assert state_update["context"]["blocking"] is True
            assert state_update["context"]["pending_roll"]["type"] == "FRENZY_RESISTANCE"
            
            # Consome a mensagem de erro do parser que é enviada logo em seguida no fallback (pela falta de LLM ativo)
            error_msg = websocket.receive_json()
            assert error_msg["action"] == "error"
            
            print("[Passo 3 - Frenzy Trigger] Status FRENZY_CHECK ativado com sucesso após turno crítico!")
            
            # Agora envia o comando para realizar o teste de Frenesi pendente.
            websocket.send_text("Tento resistir ao frenesi.")
            
            # Recebe a resposta do teste de Frenesi
            res_chat = websocket.receive_json()
            assert res_chat["action"] == "chat_response"
            assert "[TESTE DE FRENESI]" in res_chat["message"]
            
            res_state = websocket.receive_json()
            assert res_state["event"] == "state_update"
            
            print(f"[Passo 3 - Frenzy Resolution] Resposta do teste: {res_chat['message']}")
            print(f"[Passo 3 - Frenzy Resolution] Novo status resultante: {res_state['character']['status']}")
            print("[Passo 3 - Frenzy Flow] Teste de integração do fluxo de Frenesi concluído com sucesso!")
            
    finally:
        teardown_save_file(session_id)

if __name__ == "__main__":
    print("Iniciando testes de integração de WebSocket (Torpor e Frenesi)...")
    test_torpor_block()
    test_frenzy_trigger_and_resolution()
    print("Todos os testes passaram!")
