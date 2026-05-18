import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the trailing patch that was wrongly added
content = content.replace("         patch('api.orchestrator_service.extract_intent'):\n", "")
content = content.replace(", \\\n         patch('api.orchestrator_service.extract_intent') as mock_intent2: # dummy to keep indent\n", ":\n")

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
