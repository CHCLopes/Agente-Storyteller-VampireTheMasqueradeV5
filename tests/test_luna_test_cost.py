from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import report_luna_test_cost as cost


def row(input_tokens=1000, output_tokens=100, **extra):
    return {"call_made": True, "evidence": {
        "provenance": {"requested_target": {"model": cost.MODEL}},
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }, **extra}


def test_estimate_includes_failed_generations_and_counts_reasoning_once():
    report = cost.summarize([row(), {"record": row(outcome="failed")}], settled=True)
    assert report["estimated_total_usd"] == "0.00064"
    assert report["priced_calls"] == 2
    assert report["billing_confirmed"] is False


@pytest.mark.parametrize("value", [None, -1, True, "100", 1.5])
def test_missing_or_invalid_usage_is_not_zero(value):
    report = cost.summarize([row(), row(input_tokens=value)], settled=True)
    assert report["estimated_total_usd"] is None
    assert report["observed_subtotal_usd"] == "0.00032"
    assert report["calls_without_usage"] == 1


def test_unsettled_process_keeps_total_unknown_even_with_some_usage():
    assert cost.summarize([row()], settled=False)["estimated_total_usd"] is None
    assert cost.summarize([], settled=False)["estimated_total_usd"] is None


def test_no_dispatch_is_the_only_explicit_preflight_zero():
    assert cost.summarize([], no_dispatch=True)["estimated_total_usd"] == "0"
    with pytest.raises(ValueError):
        cost.summarize([row()], no_dispatch=True)


def test_skipped_calls_do_not_count_and_wrong_model_has_no_price():
    wrong = row()
    wrong["evidence"]["provenance"]["requested_target"]["model"] = "other"
    report = cost.summarize([{"call_made": False}, wrong], settled=True)
    assert report["recorded_calls"] == 1
    assert report["estimated_total_usd"] is None


def test_long_context_uses_documented_multipliers():
    assert cost.summarize([row(300000, 1000)], settled=True)["estimated_total_usd"] == "0.1218"


def test_cli_uses_only_records_and_does_not_rewrite_them(tmp_path, capsys):
    path = tmp_path / "records.jsonl"
    path.write_text(json.dumps(row()) + "\n", encoding="utf-8")
    original = path.read_bytes()
    assert cost.main(["--run-directory", str(tmp_path), "--settled"]) == 0
    output = capsys.readouterr().out
    assert "CUSTO FINAL LUNA ESTIMADO: USD 0.00032" in output
    assert path.read_bytes() == original
    path.write_text("invalid PRIVATE-DATA", encoding="utf-8")
    cost.main(["--run-directory", str(tmp_path), "--settled"])
    output = capsys.readouterr().out
    assert "indisponivel" in output and "PRIVATE-DATA" not in output


def test_both_supported_launchers_report_from_finally():
    root = Path(__file__).resolve().parent.parent
    for name in ("run_openai_luna_low_live.ps1", "run_openai_luna_source_local_trial.ps1"):
        text = (root / "scripts" / name).read_text(encoding="utf-8")
        assert "report_luna_test_cost.py" in text[text.rfind("finally {"):]
        assert "CUSTO FINAL LUNA: indisponivel" in text
