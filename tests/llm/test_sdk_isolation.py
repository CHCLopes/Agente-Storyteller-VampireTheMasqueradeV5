import ast
from pathlib import Path


_EXTERNAL_LLM_OR_TRANSPORT_ROOTS = {
    "anthropic",
    "google",
    "groq",
    "httpx",
    "mistralai",
    "openai",
}
_HTTP_ADAPTERS = {
    Path("api/llm/adapters/gemini.py"),
    Path("api/llm/adapters/groq.py"),
    Path("api/llm/adapters/openai_compatible.py"),
}


def _external_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".", 1)[0])
    return roots & _EXTERNAL_LLM_OR_TRANSPORT_ROOTS


def test_new_llm_boundary_isolates_transport_and_provider_sdks() -> None:
    violations: list[str] = []
    for path in sorted(Path("api/llm").rglob("*.py")):
        external = _external_imports(path)
        relative = path.as_posix()
        if path in _HTTP_ADAPTERS:
            unexpected = external - {"httpx"}
        else:
            unexpected = external
        if unexpected:
            violations.append(f"{relative}: {sorted(unexpected)}")

    assert not violations, "SDK/transport escaped its adapter: " + "; ".join(violations)


def test_settings_do_not_contain_http_protocol_or_authorization_details() -> None:
    source = Path("api/core/config.py").read_text(encoding="utf-8")

    assert "Authorization" not in source
    assert "Bearer " not in source
    assert "chat/completions" not in source
    assert "import httpx" not in source
