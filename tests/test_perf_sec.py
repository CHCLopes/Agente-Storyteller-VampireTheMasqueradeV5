import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from api.main import app
import time

client = TestClient(app)

def test_health_performance():
    """UX TÉCNICA: O endpoint root de healthcheck deve responder em menos de 50ms para garantir I/O assíncrono fluido."""
    start = time.perf_counter()
    response = client.get("/health")
    end = time.perf_counter()
    
    elapsed_ms = (end - start) * 1000
    assert response.status_code == 200
    assert elapsed_ms < 50, f"Falha de performance: /health demorou {elapsed_ms:.2f}ms (Budget restrito: 50ms)"
    print(f"\n[PERFORMANCE] /health validado em: {elapsed_ms:.2f}ms")

def test_chat_routing_performance():
    """APPSEC/PERFORMANCE: Validação do roteamento de strings pesadas para garantir O(1) no Regex primitivo."""
    payload = {"user_input": "Inicie uma nova crônica."}
    
    start = time.perf_counter()
    response = client.post("/chat", json=payload)
    end = time.perf_counter()
    
    elapsed_ms = (end - start) * 1000
    assert response.status_code == 200
    assert elapsed_ms < 100, f"Falha de performance: /chat demorou {elapsed_ms:.2f}ms (Budget restrito: 100ms)"
    print(f"\n[PERFORMANCE] /chat validado em: {elapsed_ms:.2f}ms")
