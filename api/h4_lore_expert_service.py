"""
api/h4_lore_expert_service.py
H4 — Lore Expert LLM. Gera contexto de lore rico via LLM, complementando o lookup estático.
Operação híbrida: LLM enriquece os dados estáticos dos catálogos. Se falhar, fallback ao lore_service estático.
"""
import httpx
import json
import re
from .core.config import Settings
from .rules_service import V5ActionPayload, PlayerSheetModel

settings = Settings()

_H4_SYSTEM_PROMPT = """Você é um Especialista de Lore do Mundo das Trevas (V5). Sua função é fornecer contexto lore rico e relevante.

## Regras
- Responda em português brasileiro.
- Máximo de 3-4 frases. Seja conciso e atmosférico.
- Inclua detalhes específicos do V5: Tradições, política Camarilla/Anarchs, Segunda Inquisição, Gehenna.
- Se mencionarem um clã, inclua a Perdição (Bane) e Compulsão relevantes.
- Se mencionarem combate, inclua as regras sociais da Máscara (consequências de violência pública).
- Se mencionarem alimentação, inclua o tipo de Predador e ressonâncias de sangue.
- NÃO invente regras mecânicas. Limite-se ao universo narrativo.

## Formato de Saída
Texto livre em português. Não use JSON. Apenas prosa informativa curta.
"""


async def generate_lore_context(
    user_input: str,
    action_payload: V5ActionPayload | None,
    player_sheet: PlayerSheetModel,
    lore_keywords: list[str] | None = None,
    static_lore: str = ""
) -> str:
    """
    Gera contexto de lore via LLM, enriquecendo os dados estáticos.
    Se LLM falhar, retorna o static_lore sem modificação.
    """
    # Monta o contexto para o LLM
    context_parts = [f"Clã do jogador: {player_sheet.clan}"]
    context_parts.append(f"Tipo de predador: {player_sheet.predator_type}")

    if action_payload:
        context_parts.append(f"Ação: {action_payload.intent}")
        if action_payload.power_used:
            context_parts.append(f"Disciplina usada: {action_payload.power_used}")
        if action_payload.is_feeding:
            context_parts.append("O jogador está se alimentando")
        if action_payload.is_aggressive:
            context_parts.append("Ação agressiva/combate")

    if lore_keywords:
        context_parts.append(f"Keywords de lore: {', '.join(lore_keywords)}")

    if static_lore:
        context_parts.append(f"Dados estáticos disponíveis:\n{static_lore}")

    context_text = "\n".join(context_parts)

    try:
        h4_payload = {
            "model": settings.LMSTUDIO_MODEL,
            "messages": [
                {"role": "system", "content": _H4_SYSTEM_PROMPT},
                {"role": "user", "content": f"Contexto da ação:\n{context_text}\n\nInput do jogador: {user_input}\n\nForneça o contexto de lore relevante."}
            ],
            "temperature": 0.4,
            "stream": False
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.lm_studio_base_url}/chat/completions",
                json=h4_payload,
                timeout=float(min(settings.LMSTUDIO_TIMEOUT, 20))
            )
            resp.raise_for_status()
            data = resp.json()
            lore_text = data["choices"][0]["message"]["content"].strip()

            if lore_text and len(lore_text) > 10:
                return f"[CONTEXTO DE MUNDO (H4)]:\n{lore_text}"

    except Exception:
        pass

    # Fallback: retorna o lore estático se disponível
    return static_lore


async def answer_lore_query(user_input: str, player_sheet: PlayerSheetModel) -> str:
    """
    Responde diretamente a consultas de lore do jogador (route=lore_query do H0).
    Retorna texto narrativo sobre o universo V5.
    """
    context_parts = [f"Clã do jogador: {player_sheet.clan}"]
    context_parts.append(f"Geração: {player_sheet.geracao}")

    context_text = "\n".join(context_parts)

    try:
        h4_payload = {
            "model": settings.LMSTUDIO_MODEL,
            "messages": [
                {"role": "system", "content": _H4_SYSTEM_PROMPT},
                {"role": "user", "content": f"O jogador fez a seguinte pergunta sobre o Mundo das Trevas:\n\n\"{user_input}\"\n\nContexto: {context_text}\n\nResponda de forma informativa e atmosférica."}
            ],
            "temperature": 0.5,
            "stream": False
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.lm_studio_base_url}/chat/completions",
                json=h4_payload,
                timeout=float(min(settings.LMSTUDIO_TIMEOUT, 20))
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    except Exception:
        return "O conhecimento dos mortos está além do véu neste momento. Tente novamente."
