"""
api/h0_controller_service.py
H0 — Controller LLM. Pré-processador de triagem e enriquecimento de contexto.
Decide se o input é ação de jogo (roteada para H1) ou consulta de lore (roteada para H4).
Operação graceful: se a chamada LLM falhar, assume ação de jogo (fallback seguro).
"""
import httpx
import json
import re
from .core.config import Settings

settings = Settings()

_H0_SYSTEM_PROMPT = """Você é o Roteador do sistema. Analise a mensagem do jogador e responda APENAS com JSON.

## Regras de Triagem
1. Se a mensagem descreve uma AÇÃO do personagem (atacar, investigar, falar com NPC, usar disciplina, se alimentar, esquivar), classifique como "action".
2. Se a mensagem é uma PERGUNTA sobre o mundo, regras, lore, história ou cenário, classifique como "lore_query".
3. Se a mensagem pede para INICIAR algo, CONSULTAR a ficha, ou é um COMANDO do sistema, classifique como "action".

## Formato de Saída (JSON estrito)
{
  "route": "action" | "lore_query",
  "scene_notes": "Breve nota de contexto cinematográfico para o narrador (1 frase). Apenas para route=action.",
  "lore_keywords": ["keyword1", "keyword2"]
}

Exemplos:
- "Quero atacar o xerife com minha espada" → {"route": "action", "scene_notes": "Tensão extrema no Elysium, a Besta exige sangue.", "lore_keywords": ["xerife", "combate"]}
- "O que é a Camarilla?" → {"route": "lore_query", "scene_notes": "", "lore_keywords": ["camarilla", "seita", "política"]}
- "Investigo o galpão abandonado" → {"route": "action", "scene_notes": "Silêncio opressivo no galpão, cheiro de ferrugem e sangue seco.", "lore_keywords": ["investigação"]}
"""


class H0TriageResult:
    """Resultado da triagem do H0."""
    def __init__(self, route: str = "action", scene_notes: str = "", lore_keywords: list[str] | None = None):
        self.route = route
        self.scene_notes = scene_notes
        self.lore_keywords = lore_keywords or []

    @property
    def is_lore_query(self) -> bool:
        return self.route == "lore_query"


async def triage_input(user_input: str) -> H0TriageResult:
    """
    Chama o LLM para classificar e enriquecer o input do jogador.
    Retorna H0TriageResult com rota, notas de cena e keywords de lore.
    Em caso de falha, retorna fallback seguro (route=action).
    """
    try:
        h0_payload = {
            "model": settings.LMSTUDIO_MODEL,
            "messages": [
                {"role": "system", "content": _H0_SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.1,
            "stream": False
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.lm_studio_base_url}/chat/completions",
                json=h0_payload,
                timeout=float(min(settings.LMSTUDIO_TIMEOUT, 15))  # Timeout curto para não bloquear
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]

            # Extrai JSON da resposta
            json_match = re.search(r'\{.*\}', reply, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return H0TriageResult(
                    route=parsed.get("route", "action"),
                    scene_notes=parsed.get("scene_notes", ""),
                    lore_keywords=parsed.get("lore_keywords", [])
                )

    except Exception:
        pass

    # Fallback determinístico
    return _deterministic_triage(user_input)


def _deterministic_triage(user_input: str) -> H0TriageResult:
    """Triagem determinística como fallback se o LLM falhar."""
    lore_patterns = [
        r'\bo que [ée]\b', r'\bquem [ée]\b', r'\bcomo funciona\b',
        r'\bexplique\b', r'\bqual\b.*\bsignificado\b', r'\bhistória d[aeo]\b',
        r'\bconte.me sobre\b', r'\bme fale sobre\b', r'\bdefina\b'
    ]
    normalized = user_input.lower()
    for pattern in lore_patterns:
        if re.search(pattern, normalized):
            # Extrai keywords simples
            stop_words = {"o", "a", "os", "as", "de", "da", "do", "em", "que", "é", "um", "uma", "me", "sobre"}
            words = [w for w in re.findall(r'\w+', normalized) if w not in stop_words and len(w) > 2]
            return H0TriageResult(route="lore_query", lore_keywords=words[:3])

    return H0TriageResult(route="action")
