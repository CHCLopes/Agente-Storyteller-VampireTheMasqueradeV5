"""Exact E admission receipts, separate from the frozen A2 database format.

This boundary accepts only C's six strings. It retains raw input before A2's
input claim/RNG and passes an existing canonical phrase to the unchanged core.
Receipts are not effects, saves, or authority for adding new equivalences.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import sqlite3

from api.campaign_progression_catalog import CampaignIntentKind, classify_campaign_intent
from api.experiments.intent_interpretation_catalog import VERSION, approved_intent

CANONICAL_INPUTS = {
    CampaignIntentKind.TASK: "Como posso ajudar?",
    CampaignIntentKind.WAIT: "Aguardo",
    CampaignIntentKind.RESCUE: "Retiro o registro",
    CampaignIntentKind.INSPECT: "Examino o registro",
    CampaignIntentKind.WITHDRAW: "Desisto",
}
APPLICATION_ID = 0x45504331


class ExactParaphraseBoundary:
    def __init__(self, path: Path, *, create: bool):
        self.path = Path(path)
        if create:
            # Exclusive creation prevents adopting an unrelated receipt database.
            with self.path.open("xb"):
                pass
            db = sqlite3.connect(self.path)
            try:
                db.executescript(f"""
                    PRAGMA application_id={APPLICATION_ID};
                    CREATE TABLE receipts(
                        session_id TEXT NOT NULL, operation_id TEXT NOT NULL,
                        raw_input TEXT NOT NULL, canonical_input TEXT NOT NULL,
                        catalog_version TEXT NOT NULL,
                        PRIMARY KEY(session_id,operation_id));
                """)
                db.commit()
            finally:
                db.close()
        if not self.path.is_file():
            raise ValueError("paraphrase_receipts_missing")
        with self._connection():
            pass

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or tables != {"receipts"}:
                raise ValueError("paraphrase_receipts_not_experimental")
            with db:
                yield db
        finally:
            db.close()

    def _validate(self, row):
        intent = approved_intent(row["raw_input"])
        if (intent is None or row["catalog_version"] != VERSION
                or row["canonical_input"] != CANONICAL_INPUTS[intent]
                or classify_campaign_intent(row["canonical_input"]) is not intent):
            raise ValueError("paraphrase_receipt_invalid")
        return row

    def admit(self, session_id: str, operation_id: str, raw_input: str) -> str:
        intent = approved_intent(raw_input)
        if intent is None:
            raise ValueError("paraphrase_not_approved")
        if not operation_id or operation_id != operation_id.strip() or len(operation_id) > 160:
            raise ValueError("paraphrase_operation_id")
        canonical = CANONICAL_INPUTS[intent]
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM receipts WHERE session_id=? AND operation_id=?",
                             (session_id, operation_id)).fetchone()
            if row is not None:
                self._validate(row)
                if row["raw_input"] != raw_input:
                    raise ValueError("paraphrase_operation_reuse")
            else:
                db.execute("INSERT INTO receipts VALUES(?,?,?,?,?)",
                           (session_id, operation_id, raw_input, canonical, VERSION))
        return canonical

    def raw_input(self, session_id: str, operation_id: str, canonical_input: str) -> str:
        with self._connection() as db:
            row = db.execute("SELECT * FROM receipts WHERE session_id=? AND operation_id=?",
                             (session_id, operation_id)).fetchone()
            if row is None:
                raise ValueError("paraphrase_receipt_missing")
            self._validate(row)
            if row["canonical_input"] != canonical_input:
                raise ValueError("paraphrase_receipt_binding")
            return row["raw_input"]
