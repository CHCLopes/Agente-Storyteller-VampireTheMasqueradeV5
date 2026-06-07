import os

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Fix feral_weapons test
feral_weapons_old = """        # O arquivo save será gerado aqui
        save_path = os.path.join(SAVE_DIR, "test_session.json")
        if os.path.exists(save_path): os.remove(save_path)
        
        response = client.post("/chat", json={"user_input": "Ataco com feral weapons", "session_id": "test_session"})
        
        assert response.status_code == 200"""

feral_weapons_new = """        # O arquivo save será gerado aqui
        save_path = os.path.join(SAVE_DIR, "test_session.json")
        if os.path.exists(save_path): os.remove(save_path)
        
        with client.websocket_connect("/ws/session/test_session") as websocket:
            websocket.send_text("Ataco com feral weapons")
            data = websocket.receive_json() # receive state_update
            assert data["action"] == "state_update"
            
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break"""

content = content.replace(feral_weapons_old, feral_weapons_new)


# Fix willpower_reroll test
willpower_old_1 = """        # Turn 1: Attack
        resp1 = client.post("/chat", json={"user_input": "Atacar", "session_id": "test_wp"})
        assert resp1.status_code == 200"""

willpower_new_1 = """        # Turn 1: Attack
        with client.websocket_connect("/ws/session/test_wp") as websocket:
            websocket.send_text("Atacar")
            data = websocket.receive_json() # state_update
            assert data["action"] == "state_update"
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break"""
content = content.replace(willpower_old_1, willpower_new_1)

willpower_old_2 = """        resp2 = client.post("/chat", json={"user_input": "Rerrolar", "session_id": "test_wp"})
        assert resp2.status_code == 200"""

willpower_new_2 = """        with client.websocket_connect("/ws/session/test_wp") as websocket:
            websocket.send_text("Rerrolar")
            data = websocket.receive_json() # state_update
            assert data["action"] == "state_update"
            while True:
                msg = websocket.receive_json()
                if msg.get("action") == "stream_end" or msg.get("action") == "error":
                    break"""
content = content.replace(willpower_old_2, willpower_new_2)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
