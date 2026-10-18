"""Load versioned role prompts from the repository's editorial Markdown."""

from __future__ import annotations

from pathlib import Path
import re


_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


def load_versioned_prompt(
    role_name: str,
    *,
    section: str | None = None,
    fallback: str,
) -> str:
    try:
        content = (_SKILLS_ROOT / f"{role_name}.md").read_text(encoding="utf-8")
    except OSError:
        return fallback
    frontmatter = re.match(
        r"\A---\s*\r?\n.*?\r?\n---\s*(?:\r?\n|\Z)",
        content,
        flags=re.DOTALL,
    )
    if frontmatter is not None:
        content = content[frontmatter.end():]
    if section is not None:
        start = f"<!-- runtime:{section}:start -->"
        end = f"<!-- runtime:{section}:end -->"
        if start not in content or end not in content:
            return fallback
        content = content.split(start, 1)[1].split(end, 1)[0]
    normalized = content.strip()
    return normalized or fallback
