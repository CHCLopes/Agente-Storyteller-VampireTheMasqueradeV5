"""Keyless A2 rehearsal; no credential or inference."""
import asyncio
import json
from scripts.evaluate_hybrid_campaign_luna_l86_live import preflight
if __name__=='__main__':print(json.dumps(asyncio.run(preflight()),ensure_ascii=False))
