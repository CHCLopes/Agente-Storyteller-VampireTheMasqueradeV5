import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Fix the bad mock
content = content.replace(
    "patch('api.orchestrator_service.get_clan_engine') as mock_clan_engine:",
    "patch('api.orchestrator_service.extract_intent') as mock_intent2: # dummy to keep indent"
)

content = content.replace(
    "patch('api.orchestrator_service.get_clan_engine'):",
    "patch('api.orchestrator_service.extract_intent'):"
)

# test_pipeline_willpower_reroll uses client.websocket_connect
# But it relies on httpx mock. The websocket might be returning an error instead of state_update.
# Let's change the test back to using await process_turn_pipeline instead of websocket, it's easier.
# Actually, the feral_weapons test also uses websocket, let's see if it passed. 
# "tests/test_perf_sec.py::test_pipeline_integration_feral_weapons PASSED" - It passed!
# So httpx mock worked for feral_weapons. Why did willpower fail? 
# Because willpower used mock_httpx_post.side_effect = [MockResponse(h1), MockResponse("H6"), MockResponse(h1_reroll), MockResponse("H6")]
# But now H6 is NOT called. So the side effect throws StopIteration or gives wrong mock to the next call.
# Let's remove the "H6" mock responses from the side_effect!

willpower_mock_old = """    mock_httpx_post.side_effect = [
        MockResponse(h1_json_first), MockResponse("Narrativa 1"),
        MockResponse(h1_json_reroll), MockResponse("Narrativa 2")
    ]"""

willpower_mock_new = """    mock_httpx_post.side_effect = [
        MockResponse(h1_json_first),
        MockResponse(h1_json_reroll)
    ]"""
content = content.replace(willpower_mock_old, willpower_mock_new)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
