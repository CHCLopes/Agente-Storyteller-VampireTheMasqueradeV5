import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
"""         patch('api.orchestrator_service.save_session_state') as mock_save, \\
         
        from api.rules_service import ResolutionResult""",
"""         patch('api.orchestrator_service.save_session_state') as mock_save:
        from api.rules_service import ResolutionResult"""
)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
