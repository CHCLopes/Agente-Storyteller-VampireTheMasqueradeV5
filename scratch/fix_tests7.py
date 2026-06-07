import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Replace any:
#          patch('api.orchestrator_service.save_session_state'), \
#          
#         from api.rules_service import ResolutionResult
# with:
#          patch('api.orchestrator_service.save_session_state'):
#         from api.rules_service import ResolutionResult

content = re.sub(
    r"patch\('api\.orchestrator_service\.save_session_state'\), \\\s+from api\.rules_service",
    r"patch('api.orchestrator_service.save_session_state'):\n        from api.rules_service",
    content
)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
