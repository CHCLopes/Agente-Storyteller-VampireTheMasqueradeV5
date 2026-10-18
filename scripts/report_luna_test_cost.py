"""Local, read-only cost display for Luna test launchers. Never reads credentials."""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

MODEL = "gpt-5.6-luna"
PRICING = {
    "model": MODEL, "observed_at": "2026-09-29",
    "source": "https://developers.openai.com/api/docs/models/gpt-5.6-luna",
    "input_usd_per_million_tokens": "0.20",
    "output_usd_per_million_tokens": "1.20",
}
MAX_BYTES = 16 * 1024 * 1024


def summarize(rows, *, settled=False, no_dispatch=False):
    calls = priced = inputs = outputs = 0
    subtotal = Decimal(0)
    if no_dispatch and rows:
        raise ValueError("inconsistent_no_dispatch")
    for envelope in rows:
        row = envelope.get("record", envelope)
        if row.get("call_made") is False:
            continue
        # Unknown dispatch status cannot be turned into zero spend.
        calls += 1
        evidence = row.get("evidence") or {}
        target = evidence.get("provenance", {}).get("requested_target", {})
        usage = evidence.get("usage") or {}
        incoming, outgoing = usage.get("input_tokens"), usage.get("output_tokens")
        if (row.get("call_made") is not True or target.get("model") != MODEL
                or any(type(n) is not int or n < 0 for n in (incoming, outgoing))):
            continue
        priced += 1
        inputs += incoming
        outputs += outgoing
        # No double counting of reasoning: already included in output_tokens.
        long_context = incoming > 272_000
        subtotal += (
            Decimal(incoming) * Decimal(PRICING["input_usd_per_million_tokens"]) * (2 if long_context else 1)
            + Decimal(outgoing) * Decimal(PRICING["output_usd_per_million_tokens"])
            * (Decimal("1.5") if long_context else 1)
        ) / Decimal(1_000_000)
    complete = no_dispatch or (settled and calls == priced)
    return {
        "status": "no_dispatch" if no_dispatch else "estimated" if complete else "unavailable",
        "currency": "USD", "billing_confirmed": False,
        "estimated_total_usd": str(subtotal) if complete else None,
        "observed_subtotal_usd": str(subtotal) if priced else None,
        "recorded_calls": calls, "priced_calls": priced,
        "calls_without_usage": calls - priced,
        "input_tokens_observed": inputs, "output_tokens_observed": outputs,
        "records_settled": settled or no_dispatch,
        "pricing": dict(PRICING),
        "limitations": "Estimativa por tokens; nao confirma cobranca. Sem ajustes de cache, tarifas de servico ou impostos.",
    }


def read_records(directory: Path):
    path = directory / "records.jsonl"
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("records_unavailable")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def display(report):
    amount = report["estimated_total_usd"]
    if amount is None:
        print("CUSTO FINAL LUNA: indisponivel (uso ou encerramento incompleto).")
        if report["observed_subtotal_usd"] is not None:
            print("Subtotal observado estimado: USD " + report["observed_subtotal_usd"] + "; nao e o total.")
    elif report["status"] == "no_dispatch":
        print("CUSTO FINAL LUNA: USD 0 (nenhuma chamada iniciada).")
    else:
        print("CUSTO FINAL LUNA ESTIMADO: USD " + amount + " (nao e cobranca confirmada).")
    print(report["limitations"])
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-directory", type=Path)
    parser.add_argument("--settled", action="store_true")
    parser.add_argument("--no-dispatch", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.no_dispatch:
            report = summarize([], no_dispatch=True)
        else:
            report = summarize(read_records(args.run_directory), settled=args.settled)
    except (OSError, ValueError, TypeError, AttributeError):
        # Do not print raw JSON, paths or exceptions from retained artifacts.
        report = summarize([], settled=False)
    display(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
