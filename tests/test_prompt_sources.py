from api.h0_controller_service import _H0_SYSTEM_PROMPT
from api.h4_lore_expert_service import (
    _H4_ATMOSPHERIC_SYSTEM_PROMPT,
    _H4_GROUNDED_QA_SYSTEM_PROMPT,
)
from api.orchestrator_service import STORYTELLER_SYSTEM_PROMPT
from api.parser_service import H1_PROMPT
from api.prompt_service import load_versioned_prompt


def test_every_runtime_role_prompt_is_loaded_from_versioned_markdown() -> None:
    assert _H0_SYSTEM_PROMPT == load_versioned_prompt(
        "H0_vtm_orchestrator", section="triage", fallback="unexpected"
    )
    assert H1_PROMPT == load_versioned_prompt(
        "H1_vtm_rules_parser", fallback="unexpected"
    )
    assert _H4_GROUNDED_QA_SYSTEM_PROMPT == load_versioned_prompt(
        "H4_vtm_lore_expert", section="grounded_qa", fallback="unexpected"
    )
    assert _H4_ATMOSPHERIC_SYSTEM_PROMPT == load_versioned_prompt(
        "H4_vtm_lore_expert", section="atmospheric", fallback="unexpected"
    )
    assert STORYTELLER_SYSTEM_PROMPT == load_versioned_prompt(
        "H6_vtm_narrator", fallback="unexpected"
    )


def test_runtime_prompts_do_not_expose_markdown_frontmatter() -> None:
    for prompt in (
        _H0_SYSTEM_PROMPT,
        H1_PROMPT,
        _H4_GROUNDED_QA_SYSTEM_PROMPT,
        _H4_ATMOSPHERIC_SYSTEM_PROMPT,
        STORYTELLER_SYSTEM_PROMPT,
    ):
        assert not prompt.startswith("---")
        assert "description:" not in prompt
