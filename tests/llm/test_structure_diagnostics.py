"""Validation diagnostics disclose schema coordinates, never generated content."""

from __future__ import annotations

import json
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model, model_validator
from pydantic_core import PydanticCustomError

from api.llm.structure_diagnostics import (
    build_structure_validation_evidence,
    sanitize_structure_validation_evidence,
)


_PRIVATE = "syntheticSecretUnknownField123"


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    summary: str = Field(alias="s", min_length=3)


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    narrative: str = Field(alias="n", min_length=5)
    facts: list[_Item] = Field(alias="f")
    values: dict[str, int] = Field(default_factory=dict)
    outcome: Literal["success"] = "success"


class _Node(BaseModel):
    value: int
    child: _Node | None = None


def _evidence(value, model: type[BaseModel] = _Payload):
    with pytest.raises(ValidationError) as caught:
        model.model_validate(value)
    result = build_structure_validation_evidence(caught.value, model, "schema_validation")
    serialized = result.model_dump_json()
    assert _PRIVATE not in serialized
    assert '"msg"' not in serialized
    assert '"input"' not in serialized
    assert '"ctx"' not in serialized
    return result


def _saved(path, *, code="string_type", **overrides):
    return {
        "stage": "schema_validation",
        "issues": [{"path": path, "code": code}],
        **overrides,
    }


def test_json_parse_failure_reports_only_stage_and_known_code() -> None:
    with pytest.raises(json.JSONDecodeError) as caught:
        json.loads(_PRIVATE)

    evidence = build_structure_validation_evidence(caught.value, _Payload, "json_parse")

    assert evidence.stage == "json_parse"
    assert [(issue.path, issue.code) for issue in evidence.issues] == [((), "json_invalid")]
    assert evidence.truncated is False
    assert _PRIVATE not in evidence.model_dump_json()


def test_multiple_failures_keep_schema_fields_and_codes_only() -> None:
    evidence = _evidence({"n": 15, "f": [], "outcome": _PRIVATE})

    assert evidence.stage == "schema_validation"
    assert {(issue.path, issue.code) for issue in evidence.issues} == {
        (("n",), "string_type"),
        (("outcome",), "literal_error"),
    }


def test_missing_fields_are_safe_schema_coordinates() -> None:
    evidence = _evidence({})

    assert {(issue.path, issue.code) for issue in evidence.issues} == {
        (("n",), "missing"), (("f",), "missing")
    }


@pytest.mark.parametrize(
    ("payload", "path"),
    [
        ({"n": "valid narrative", "f": [{"s": 4}]}, ("f", 0, "s")),
        ({"narrative": "valid narrative", "facts": [{"summary": 4}]}, ("facts", 0, "summary")),
        ({"n": "valid narrative", "f": [{"summary": 4}]}, ("f", 0, "summary")),
        ({"narrative": "valid narrative", "facts": [{"s": 4}]}, ("facts", 0, "s")),
    ],
)
def test_aliases_and_field_names_work_through_nested_array_references(payload, path) -> None:
    evidence = _evidence(payload)

    assert [(issue.path, issue.code) for issue in evidence.issues] == [(path, "string_type")]


@pytest.mark.parametrize(
    ("payload", "path"),
    [
        ({"n": "valid narrative", "f": [], _PRIVATE: 1}, ("?",)),
        ({"n": "valid narrative", "f": [{"s": "valid summary", _PRIVATE: 1}]}, ("f", 0, "?")),
    ],
)
def test_extra_keys_are_replaced_even_when_they_look_like_identifiers(payload, path) -> None:
    evidence = _evidence(payload)

    assert [(issue.path, issue.code) for issue in evidence.issues] == [(path, "extra_forbidden")]


def test_dynamic_dictionary_key_never_becomes_a_schema_coordinate() -> None:
    evidence = _evidence({"n": "valid narrative", "f": [], "values": {_PRIVATE: "bad-int"}})

    assert evidence.issues[0].path == ("values", "?")
    assert evidence.issues[0].code == "int_parsing"


def test_model_validator_failure_does_not_infer_its_business_rule() -> None:
    class Invariant(BaseModel):
        value: int

        @model_validator(mode="after")
        def reject(self):
            raise ValueError(_PRIVATE)

    evidence = _evidence({"value": 1}, Invariant)

    assert [(issue.path, issue.code) for issue in evidence.issues] == [((), "value_error")]


def test_arbitrary_pydantic_custom_error_code_and_message_are_not_exposed() -> None:
    class CustomError(BaseModel):
        value: int

        @model_validator(mode="after")
        def reject(self):
            raise PydanticCustomError(_PRIVATE, _PRIVATE, {"secret": _PRIVATE})

    evidence = _evidence({"value": 1}, CustomError)

    assert [(issue.path, issue.code) for issue in evidence.issues] == [((), "validation_error")]


def test_non_pydantic_exception_remains_generic_without_exception_text() -> None:
    evidence = build_structure_validation_evidence(ValueError(_PRIVATE), _Payload, "schema_validation")

    assert [(issue.path, issue.code) for issue in evidence.issues] == [((), "validation_error")]
    assert _PRIVATE not in evidence.model_dump_json()


def test_evidence_is_bounded_to_eight_issues_with_truncation_flag() -> None:
    model = create_model("ManyFields", **{f"field_{index}": (int, ...) for index in range(12)})
    evidence = _evidence({}, model)

    assert len(evidence.issues) == 8
    assert evidence.truncated is True
    assert all(issue.code == "missing" for issue in evidence.issues)


@pytest.mark.parametrize("index", [-1, 10001, True, "1", _PRIVATE])
def test_replay_rejects_invalid_array_indices(index) -> None:
    evidence = sanitize_structure_validation_evidence(_saved(["f", index, "s"]), _Payload)

    assert evidence is not None
    assert evidence.issues[0].path == ("f", "?")
    assert _PRIVATE not in evidence.model_dump_json()


def test_replay_accepts_bounded_index_only_at_array_node() -> None:
    array = sanitize_structure_validation_evidence(_saved(["f", 10000, "s"]), _Payload)
    dictionary = sanitize_structure_validation_evidence(_saved(["values", 1]), _Payload)

    assert array.issues[0].path == ("f", 10000, "s")
    assert dictionary.issues[0].path == ("values", "?")


def test_replay_preserves_unknown_marker_and_discards_its_suffix() -> None:
    evidence = sanitize_structure_validation_evidence(_saved(["f", 0, "?", _PRIVATE]), _Payload)

    assert evidence.issues[0].path == ("f", 0, "?")
    assert _PRIVATE not in evidence.model_dump_json()


def test_replay_discards_unknown_types_and_untrusted_extra_fields() -> None:
    raw = _saved(["n"], code=_PRIVATE, input=_PRIVATE, msg=_PRIVATE)
    raw["issues"][0].update({"ctx": {"secret": _PRIVATE}, "msg": _PRIVATE})
    evidence = sanitize_structure_validation_evidence(raw, _Payload)

    assert evidence.issues[0].code == "validation_error"
    assert _PRIVATE not in evidence.model_dump_json()


@pytest.mark.parametrize("raw", [None, {}, {"stage": []}, {"stage": _PRIVATE}, {"stage": "schema_validation", "issues": []}])
def test_replay_without_valid_stage_and_issues_is_absent(raw) -> None:
    assert sanitize_structure_validation_evidence(raw, _Payload) is None


def test_recursive_model_paths_are_bounded_to_eight_segments() -> None:
    evidence = sanitize_structure_validation_evidence(_saved(["child"] * 9 + ["value"]), _Node)

    assert evidence.issues[0].path == ("child",) * 8
    assert evidence.truncated is True


def test_long_declared_alias_is_redacted() -> None:
    long_alias = "a" * 65

    class LongAlias(BaseModel):
        value: int = Field(alias=long_alias)

    evidence = _evidence({long_alias: "bad-int"}, LongAlias)

    assert evidence.issues[0].path == ("?",)
    assert long_alias not in evidence.model_dump_json()


@pytest.mark.parametrize("reference", ["#/$defs/Loop", "https://example.invalid/schema"])
def test_cycles_and_external_schema_references_fail_closed(monkeypatch, reference) -> None:
    schema = {"$ref": reference, "$defs": {"Loop": {"$ref": "#/$defs/Loop"}}}
    monkeypatch.setattr(_Payload, "model_json_schema", lambda **kwargs: schema)

    evidence = sanitize_structure_validation_evidence(_saved(["n", _PRIVATE]), _Payload)

    assert evidence.issues[0].path == ("?",)
    assert _PRIVATE not in evidence.model_dump_json()


def test_schema_generation_failure_never_replaces_original_error(monkeypatch) -> None:
    def broken_schema(**kwargs):
        raise RuntimeError(_PRIVATE)

    monkeypatch.setattr(_Payload, "model_json_schema", broken_schema)

    evidence = _evidence({})

    assert [(issue.path, issue.code) for issue in evidence.issues] == [((), "validation_error")]
