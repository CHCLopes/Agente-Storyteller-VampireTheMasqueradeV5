import re

test_file = r"c:\Users\skate\Desktop\WorkSpace\Antigravity\.antigravity\SandBox\AgenteStoryteller\tests\test_perf_sec.py"

with open(test_file, "r", encoding="utf-8") as f:
    content = f.read()

# Add mock for run_narrator_stream in feral_weapons and willpower_reroll
patch_str = "patch('api.orchestrator_service.calculate_resolution') as mock_calc_res:"
patch_str_new = "patch('api.orchestrator_service.calculate_resolution') as mock_calc_res, \\\n         patch('api.main.run_narrator_stream') as mock_narrator_stream:"

content = content.replace(patch_str, patch_str_new)

# Setup mock_narrator_stream generator
generator_setup = """        async def dummy_generator(*args, **kwargs):
            yield "Narrativa"
        mock_narrator_stream.side_effect = dummy_generator
        
        # O arquivo save será gerado aqui"""

content = content.replace("        # O arquivo save será gerado aqui", generator_setup)

willpower_patch = "patch('api.orchestrator_service.apply_willpower_reroll') as mock_reroll:"
willpower_patch_new = "patch('api.orchestrator_service.apply_willpower_reroll') as mock_reroll, \\\n         patch('api.main.run_narrator_stream') as mock_narrator_stream:"
content = content.replace(willpower_patch, willpower_patch_new)

willpower_gen = """        async def dummy_generator(*args, **kwargs):
            yield "Narrativa"
        mock_narrator_stream.side_effect = dummy_generator
        
        # Turn 1: Attack"""
content = content.replace("        # Turn 1: Attack", willpower_gen)

with open(test_file, "w", encoding="utf-8") as f:
    f.write(content)
