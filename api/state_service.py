import os
import json
import asyncio
import aiofiles

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

_session_locks: dict[str, asyncio.Lock] = {}

def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]

async def save_session_state(session_id: str, session_data: dict, chronicle_name: str, turn: int):
    save_data = {
        "session_id": session_id,
        "chronicle_name": chronicle_name,
        "turn": turn,
        "context": session_data
    }
    safe_filename = os.path.basename(f"{session_id}.json")
    path = os.path.join(SAVE_DIR, safe_filename)
    
    lock = get_session_lock(session_id)
    async with lock:
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(save_data, indent=4))

async def load_session_state(session_id: str) -> dict | None:
    safe_filename = os.path.basename(f"{session_id}.json")
    path = os.path.join(SAVE_DIR, safe_filename)
    
    lock = get_session_lock(session_id)
    async with lock:
        if not os.path.exists(path):
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
