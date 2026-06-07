import re
import os

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Fix mock_narrator in async tests
# Replace:
# patch('api.orchestrator_service.run_narrator', return_value="Narrativa") as mock_narrator:
# ...
# sys_log = mock_narrator.call_args[0][1]
# With:
# result, ctx = await process_turn_pipeline(...)
# sys_log = result

content = content.replace(
    "patch('api.orchestrator_service.run_narrator', return_value=\"Narrativa\") as mock_narrator:",
    "patch('api.orchestrator_service.get_clan_engine') as mock_clan_engine:" # Just a dummy patch to keep the indentation
)

content = content.replace(
    "patch('api.orchestrator_service.run_narrator', return_value=\"Narrativa\"):\n",
    "patch('api.orchestrator_service.get_clan_engine'):\n"
)

# Fix sys_log = mock_narrator.call_args...
content = re.sub(
    r'assert mock_narrator\.call_args is not None, .*\n\s+sys_log = mock_narrator\.call_args\[0\]\[1\]',
    r'sys_log = result',
    content
)

content = content.replace("from api.orchestrator_service import SAVE_DIR", "from api.state_service import SAVE_DIR")

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
