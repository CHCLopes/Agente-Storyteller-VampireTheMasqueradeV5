"""Offline checks for one isolated manual launch; no provider request."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys

os.environ["STORYTELLER_DISABLE_DOTENV"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main() -> int:
    from api.core.config import settings
    from api.llm.runtime import build_llm_runtime
    from api.llm.adapters.groq import GroqAdapter
    from api.persistence import SQLitePersistence
    from api.main import app
    root = Path(__file__).resolve().parents[1]
    runtime = build_llm_runtime(settings)
    if not settings.llm_is_configured or type(runtime.gateway) is not GroqAdapter:
        raise ValueError("manual_test_target_invalid")
    db = Path(settings.storyteller_db_path).resolve()
    temp = Path(os.environ["TEMP"]).resolve()
    if not db.is_relative_to(temp) or not db.parent.name.startswith("storyteller-manual-game-"):
        raise ValueError("manual_test_database_not_isolated")
    resume_session = os.environ.get("STORYTELLER_MANUAL_RESUME_SESSION")
    if resume_session:
        import sqlite3
        expected_session = "local." + db.parent.name.removeprefix("storyteller-manual-game-")
        if resume_session != expected_session:
            raise ValueError("manual_test_resume_identity_invalid")
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
            connection.execute("PRAGMA query_only=ON")
            if connection.execute(
                "SELECT count(*) FROM campaigns WHERE session_id=?", (resume_session,)
            ).fetchone()[0] != 1:
                raise ValueError("manual_test_resume_session_missing")
    if not (root / "client/dist/index.html").is_file():
        raise ValueError("manual_test_frontend_missing")
    if not (root / "data/sheets/base_player.json").is_file():
        raise ValueError("manual_test_base_sheet_missing")
    assert SQLitePersistence and app
    print(json.dumps({"status":"passed", "provider_calls":0,
        "target":runtime.target.model_dump(mode="json"), "adapter":"GroqAdapter",
        "database":str(db), "dotenv_disabled":True, "frontend_ready":True,
        "source_bridge_activated":False, "resumed_session_verified":bool(resume_session),
        "narrator_context_token_budget":settings.narrator_context_token_budget}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print('{"status":"failed","code":"manual_test_preflight_failed"}')
        raise SystemExit(2) from None
