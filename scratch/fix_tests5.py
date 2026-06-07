import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Replace return_value=dummy_payload with AsyncMock return value
import_async_mock = "from unittest.mock import patch, AsyncMock\n"
content = content.replace("from unittest.mock import patch\n", import_async_mock)

content = content.replace(
    "patch('api.orchestrator_service.extract_intent', return_value=dummy_payload)",
    "patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=dummy_payload)"
)

content = content.replace(
    "patch('api.orchestrator_service.extract_intent', return_value=DummyPayload())",
    "patch('api.orchestrator_service.extract_intent', new_callable=AsyncMock, return_value=DummyPayload())"
)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
