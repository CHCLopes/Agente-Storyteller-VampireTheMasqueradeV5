"""Content-free diagnostics for parsing and validating structured responses."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, get_args

from pydantic import BaseModel, ValidationError

from .contract import StructureValidationEvidence, StructureValidationIssue


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")
_MAX_ISSUES = 8
_MAX_PATH = 8
_MAX_INDEX = 10000
_KNOWN_CODES = frozenset(get_args(StructureValidationIssue.model_fields["code"].annotation))


def _path_schema(response_model: type[BaseModel]) -> dict[str, Any]:
    """Combine declared field names and aliases without copying schema prose.

    Pydantic emits fields in model declaration order for either alias mode.
    Pairing those property entries permits mixed names/aliases in nested input.
    Local references remain references; they are resolved with a separate bound.
    """

    aliases = response_model.model_json_schema(by_alias=True)
    names = response_model.model_json_schema(by_alias=False)

    def merge(alias: Any, name: Any, depth: int = 0) -> dict[str, Any]:
        if depth > 32 or not isinstance(alias, dict):
            return {}
        name = name if isinstance(name, dict) else {}
        result = {
            key: alias[key] for key in ("type", "$ref") if key in alias
        }
        properties = alias.get("properties")
        if isinstance(properties, dict):
            named_properties = name.get("properties", {})
            named_rows = (
                list(named_properties.items())
                if isinstance(named_properties, dict) else []
            )
            result["properties"] = {}
            for index, (key, value) in enumerate(list(properties.items())[:128]):
                named_key, named_value = (
                    named_rows[index]
                    if len(named_rows) == len(properties)
                    else (key, {})
                )
                child = merge(value, named_value, depth + 1)
                result["properties"][key] = child
                result["properties"].setdefault(named_key, child)
        definitions = alias.get("$defs")
        if isinstance(definitions, dict):
            named_definitions = name.get("$defs", {})
            result["$defs"] = {
                key: merge(value, named_definitions.get(key, {}), depth + 1)
                for key, value in list(definitions.items())[:128]
            }
        if isinstance(alias.get("items"), dict):
            result["items"] = merge(alias["items"], name.get("items"), depth + 1)
        for key in ("prefixItems", "anyOf", "oneOf", "allOf"):
            rows = alias.get(key)
            if isinstance(rows, list):
                named_rows = name.get(key, [])
                result[key] = [
                    merge(value, named_rows[index] if index < len(named_rows) else {}, depth + 1)
                    for index, value in enumerate(rows[:16])
                ]
        return result

    return merge(aliases, names)


def _expanded_nodes(node: Any, root: dict[str, Any]) -> list[dict[str, Any]]:
    pending = [node]
    visited: set[int] = set()
    result = []
    for _ in range(64):
        if not pending:
            break
        current = pending.pop()
        if not isinstance(current, dict) or id(current) in visited:
            continue
        visited.add(id(current))
        reference = current.get("$ref")
        if isinstance(reference, str):
            if not reference.startswith("#/") or len(reference) > 1024:
                continue
            parts = reference[2:].split("/")
            if len(parts) > 32:
                continue
            resolved: Any = root
            for part in parts:
                if not isinstance(resolved, dict):
                    resolved = None
                    break
                resolved = resolved.get(part.replace("~1", "/").replace("~0", "~"))
            if resolved is not None:
                pending.append(resolved)
            continue
        result.append(current)
        for key in ("anyOf", "oneOf", "allOf"):
            branches = current.get(key)
            if isinstance(branches, list):
                pending.extend(branches[:16])
    return result


def _safe_path(path: Any, root: dict[str, Any]) -> tuple[tuple[str | int, ...], bool]:
    if not isinstance(path, (tuple, list)):
        return ("?",), False
    nodes = [root]
    safe: list[str | int] = []
    for part in path[:_MAX_PATH]:
        if part == "?":
            safe.append("?")
            break
        next_nodes = []
        for node in nodes:
            for current in _expanded_nodes(node, root):
                if isinstance(part, str) and _IDENTIFIER.fullmatch(part):
                    properties = current.get("properties", {})
                    if isinstance(properties, dict) and part in properties:
                        next_nodes.append(properties[part])
                elif type(part) is int and 0 <= part <= _MAX_INDEX:
                    if current.get("type") != "array":
                        continue
                    prefix = current.get("prefixItems", [])
                    if isinstance(prefix, list) and part < len(prefix):
                        next_nodes.append(prefix[part])
                    elif isinstance(current.get("items"), dict):
                        next_nodes.append(current["items"])
        if not next_nodes:
            safe.append("?")
            break
        safe.append(part)
        nodes = next_nodes[:32]
    return tuple(safe), len(path) > _MAX_PATH


def _safe_code(code: Any) -> str:
    return code if isinstance(code, str) and code in _KNOWN_CODES else "validation_error"


def sanitize_structure_validation_evidence(
    value: Any, response_model: type[BaseModel]
) -> StructureValidationEvidence | None:
    """Recheck persisted diagnostics; unknown paths cannot become log content."""

    try:
        raw = value.model_dump() if isinstance(value, StructureValidationEvidence) else value
        if not isinstance(raw, Mapping):
            return None
        stage = raw.get("stage")
        if not isinstance(stage, str) or stage not in {"json_parse", "schema_validation"}:
            return None
        rows = raw.get("issues")
        if not isinstance(rows, (tuple, list)) or not rows:
            return None
        root = _path_schema(response_model)
        issues = []
        truncated = raw.get("truncated") is True or len(rows) > _MAX_ISSUES
        for row in rows[:_MAX_ISSUES]:
            if not isinstance(row, Mapping):
                continue
            path, shortened = _safe_path(row.get("path", ()), root)
            truncated = truncated or shortened
            issues.append(StructureValidationIssue(path=path, code=_safe_code(row.get("code"))))
        if not issues:
            return None
        return StructureValidationEvidence(stage=stage, issues=tuple(issues), truncated=truncated)
    except Exception:
        # A diagnostic must never replace the original, normalized LLM failure.
        return None


def build_structure_validation_evidence(
    exc: Exception, response_model: type[BaseModel], stage: str
) -> StructureValidationEvidence:
    """Extract bounded structural facts, never exception prose or input values."""

    selected_stage = "json_parse" if stage == "json_parse" else "schema_validation"
    default_code = "json_invalid" if selected_stage == "json_parse" else "validation_error"
    fallback = StructureValidationEvidence(
        stage=selected_stage,
        issues=(StructureValidationIssue(path=(), code=default_code),),
    )
    if selected_stage == "json_parse" or not isinstance(exc, ValidationError):
        return fallback
    try:
        errors = exc.errors(include_input=False, include_context=False, include_url=False)
        rows = [{"code": row.get("type"), "path": row.get("loc", ())} for row in errors[:_MAX_ISSUES]]
        return sanitize_structure_validation_evidence(
            {"stage": selected_stage, "issues": rows, "truncated": len(errors) > _MAX_ISSUES},
            response_model,
        ) or fallback
    except Exception:
        return fallback
