"""Independent HYP-004 replication over the frozen HYP-002 live protocol."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import evaluate_closed_world_render_live as base


VERSION = "closed-world-render-replication-live-v1"
HYPOTHESIS_ID = "HYP-004-QWEN-GPT-OSS-REPLICATION-L1"
OPTION = "HYP-004-REPLICATION-L1"
GATE = ROOT / "evals/narrator/reports/closed-world-render-replication-live-gate-2026-09-26.json"
OUTPUT_PREFIX = "closed-world-render-replication-"

_BASE_PREPARE_LIVE = base.prepare_live
_BASE_PACER = base.shared._CallPacer


def run_path(batch_id: str) -> Path:
    return base.OUTPUT_ROOT / f"{OUTPUT_PREFIX}{base._batch(batch_id)}"


class ReplicationPacer(_BASE_PACER):
    """Keep the frozen pacing while exposing the new hypothesis identity."""

    async def before_call(self, label: str) -> None:
        await super().before_call(label.replace("HYP-002", "HYP-004"))


def prepare_live() -> base.PreparedLive:
    prepared = _BASE_PREPARE_LIVE()
    metadata = deepcopy(prepared.metadata)
    metadata.update(
        purpose="closed_world_render_between_run_replication",
        version=VERSION,
        hypothesis_id=HYPOTHESIS_ID,
        option=OPTION,
    )
    metadata["replication"] = {
        "source_hypothesis": "HYP-002-L2",
        "same_cases": True,
        "same_targets": True,
        "same_parameters": True,
        "aggregate_for_admission": False,
        "best_of_selection": False,
        "comparison_requires_independent_human_review": True,
    }
    metadata["inputs"]["implementation"].append(
        {
            "file": "scripts/evaluate_closed_world_render_replication_live.py",
            "sha256": base._sha_file(Path(__file__)),
        }
    )
    return base.PreparedLive(
        prepared.candidates,
        prepared.targets,
        prepared.corpus,
        prepared.system_prompt,
        metadata,
    )


def configure() -> None:
    base.VERSION = VERSION
    base.LIVE_GATE = GATE
    base.run_path = run_path
    base.prepare_live = prepare_live
    base.shared._CallPacer = ReplicationPacer


def main(argv: list[str] | None = None) -> int:
    configure()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
