import httpx
import json
import re
import os
from pydantic import ValidationError
from .rules_service import V5ActionPayload
from .core.config import Settings

settings = Settings()

def load_skill_prompt(skill_name: str) -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", f"{skill_name}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

H1_PROMPT = load_skill_prompt("H1_vtm_rules_parser")

async def extract_intent(user_input: str) -> V5ActionPayload:
    messages = [
        {"role": "system", "content": H1_PROMPT},
        {"role": "user", "content": user_input}
    ]
    
    # 1ª Tentativa
    try:
        return await _call_h1(messages)
    except ValidationError as e:
        # Retry logic
        error_msg = f"Invalid JSON generated: {str(e)}. Please correct your response and output only valid JSON."
        messages.append({"role": "assistant", "content": "Failed. ValidationError."})
        messages.append({"role": "user", "content": error_msg})
        
        # 2ª Tentativa (Limite Máximo de 1 Retentativa)
        try:
            return await _call_h1(messages)
        except Exception:
            return _create_fallback_payload()
    except Exception:
        return _create_fallback_payload()

async def _call_h1(messages: list) -> V5ActionPayload:
    h1_payload = {
        "model": settings.LMSTUDIO_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{settings.lm_studio_base_url}/chat/completions", json=h1_payload, timeout=float(settings.LMSTUDIO_TIMEOUT))
        resp.raise_for_status()
        data = resp.json()
        h1_reply = data["choices"][0]["message"]["content"]
        
        json_match = re.search(r'\{.*\}', h1_reply, re.DOTALL)
        raw_json = json_match.group(0) if json_match else h1_reply
        return V5ActionPayload(**json.loads(raw_json))

def _create_fallback_payload() -> V5ActionPayload:
    # Fallback null/seguro para abortar a matemática e avisar a engine
    from .rules_service import V5Attribute, V5Skill
    return V5ActionPayload(
        intent="[FALLBACK] Não compreendi a intenção do jogador",
        attribute=V5Attribute.Strength,
        skill=V5Skill.BRAWL,
        is_aggressive=False,
        action_target="UNOPPOSED"
    )
