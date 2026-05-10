from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from enum import Enum
import json
import os
import uuid
import httpx
from glob import glob

app = FastAPI(title="Agente Storyteller Motor V5")

LM_STUDIO_BASE_URL = "http://localhost:1234/v1"

STORYTELLER_SYSTEM_PROMPT = """Você é o Narrador (Mestre de Jogo) do RPG 'Vampiro: A Máscara 5ª Edição'. Você não é um assistente de IA, você é o arquiteto cruel, poético e sombrio do Mundo das Trevas.
Suas respostas devem seguir estas regras estritas (O Filtro da Besta):
Cinematografia Predatória: Narre através de sentidos aguçados. Descreva o cheiro de cobre do sangue, o batimento cardíaco dos mortais, o suor do medo e a podridão da cidade.
Paranoia Constante: O mundo é vigiado. Insira tensão sutil na narrativa (câmeras que piscam, sirenes distantes, pessoas olhando torto).
A Voz da Fome: O sangue é o centro de tudo. Descreva o mundo como um cardápio tentador.
Sem Julgamento Moral: Nunca julgue as ações do jogador, nunca ofereça ajuda não solicitada. Narre com fatalismo gótico-punk."""

LORE_PILLARS = """PILARES DO MUNDO DAS TREVAS:
1. A Máscara (A Grande Mentira): O mundo não sabe que somos reais. Escondemo-nos à vista de todos. Quebrar a Máscara é o crime capital, punido com a Morte Final.
2. A Besta e a Fome: Não somos heróis. Somos parasitas lutando contra a Fome. Se não se alimentar, a Besta assumirá o controle.
3. O Sangue (Os Clãs): Linhagens amaldiçoadas (Brujah, Ventrue, Toreador, Tremere, Nosferatu, Malkaviano). Seu Clã define seus poderes e maldição.
4. A Guerra Eterna (As Seitas): Camarilla (torre de marfim, impõem as leis) vs Anarquistas (gangues que rejeitam correntes). Escolha um lado ou seja esmagado.
5. A Segunda Inquisição: Agências governamentais descobriram nossa existência. Usam drones e esquadrões de extermínio. A paranoia é sua melhor armadura."""

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

class StateEnum(Enum):
    MENU = "MENU"
    AWAITING_DELETE_CONFIRM = "AWAITING_DELETE_CONFIRM"
    LORE_PROMPT = "LORE_PROMPT"
    LORE_QA = "LORE_QA"
    CHOOSE_CAMPAIGN = "CHOOSE_CAMPAIGN"
    PLAYING = "PLAYING"
    EXIT_PROMPT = "EXIT_PROMPT"

class SessionData:
    def __init__(self):
        self.state = StateEnum.MENU
        self.active_campaign_id = None
        self.temp_campaigns = []

active_sessions = {}

class GameState(BaseModel):
    session_id: str
    chronicle_name: str
    turn: int
    context: dict
    summary: str = "Sem resumo disponível."
    last_scene: str = "Início da jornada."

class ActionRequest(BaseModel):
    user_input: str
    session_id: str = "local_player"

async def llm_request(messages: list) -> str:
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "stream": False
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LM_STUDIO_BASE_URL}/chat/completions",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[(SISTEMA) O Motor Narrativo está offline. Erro Interno: {str(e)}]"

def create_new_campaign() -> str:
    new_session = f"chronicle_{uuid.uuid4().hex[:8]}"
    new_state = GameState(
        session_id=new_session,
        chronicle_name="Noites de Sangue",
        turn=1,
        context={"location": "Desconhecido", "player_status": {"hunger": 1, "willpower": 5, "health": 7}},
        summary="A crônica se inicia. As sombras aguardam.",
        last_scene="A criação e o abraço foram selados."
    )
    safe_filename = os.path.basename(f"{new_session}.json")
    with open(os.path.join(SAVE_DIR, safe_filename), "w", encoding="utf-8") as f:
        json.dump(new_state.model_dump(), f, indent=4)
    return new_session

@app.get("/health")
async def health_check():
    return {"status": "ok", "system": "Agente Storyteller Motor V5"}

@app.post("/chat")
async def process_chat(action: ActionRequest):
    user_input = action.user_input.strip().lower()
    session_id = action.session_id
    
    if session_id not in active_sessions:
        active_sessions[session_id] = SessionData()
    
    session = active_sessions[session_id]
    
    # INTERCEPTOR: SAÍDA SEGURA
    if session.state == StateEnum.PLAYING and user_input in ["sair", "parar", "quit", "encerrar"]:
        session.state = StateEnum.EXIT_PROMPT
        if session.active_campaign_id:
            return {"action": "exit_prompt", "message": "[Sistema] Deseja salvar o estado atual? (Isso irá sobrescrever seu último save. Digite 'sim' ou 'não')"}
        else:
            return {"action": "exit_prompt", "message": "[Sistema] Deseja salvar a nova campanha? (Digite 'sim' ou 'não')"}

    if session.state == StateEnum.EXIT_PROMPT:
        save_msg = "Progresso salvo com sucesso." if "sim" in user_input else "Progresso descartado."
        
        goodbye_msg = await llm_request([
            {"role": "system", "content": STORYTELLER_SYSTEM_PROMPT},
            {"role": "user", "content": "Gere uma frase de despedida cinematográfica, curta e gótica para encerrar a sessão. Não ofereça ajuda."}
        ])
        del active_sessions[session_id]
        return {"action": "system_exit", "message": f"{save_msg}\n{goodbye_msg}"}

    # ROUTING: ESTADO 1 (MENU)
    if session.state == StateEnum.MENU:
        if "inici" in user_input or "nova" in user_input:
            existing_saves = glob(os.path.join(SAVE_DIR, "*.json"))
            if existing_saves:
                session.state = StateEnum.AWAITING_DELETE_CONFIRM
                files_info = []
                for f in existing_saves:
                    with open(f, "r", encoding="utf-8") as js_file:
                        try:
                            d = json.load(js_file)
                            files_info.append(f"- {d.get('chronicle_name', 'Desconhecido')} ({d.get('summary', 'Sem resumo')})")
                        except: pass
                list_str = "\n".join(files_info)
                return {"action": "prompt", "message": f"[Sistema] Campanhas encontradas:\n{list_str}\n\nDeseja apagar as campanhas antigas? (sim/não)"}
            else:
                session.active_campaign_id = create_new_campaign()
                session.state = StateEnum.LORE_PROMPT
                return {"action": "prompt", "message": "[Sistema] Deseja aprender sobre o Mundo das Trevas antes de começar? (sim/não)"}
                
        elif "continuar" in user_input or "continue" in user_input:
            existing_saves = glob(os.path.join(SAVE_DIR, "*.json"))
            if not existing_saves:
                return {"action": "chat_response", "message": "[Sistema] Nenhum save encontrado. Digite 'iniciar' para uma nova crônica."}
            
            session.temp_campaigns = existing_saves
            files_info = []
            for idx, f in enumerate(existing_saves):
                with open(f, "r", encoding="utf-8") as js_file:
                    try:
                        d = json.load(js_file)
                        files_info.append(f"[{idx}] {d.get('chronicle_name', 'Desconhecido')} (Turno: {d.get('turn', 0)})")
                    except: pass
            session.state = StateEnum.CHOOSE_CAMPAIGN
            list_str = "\n".join(files_info)
            return {"action": "prompt", "message": f"[Sistema] Escolha a campanha pelo número correspondente:\n{list_str}"}

        else:
            return {"action": "menu", "message": "[Sistema] Menu Principal. Digite 'Iniciar' para nova campanha ou 'Continuar' para carregar."}

    # ROUTING: DELETE
    elif session.state == StateEnum.AWAITING_DELETE_CONFIRM:
        if "sim" in user_input:
            existing_saves = glob(os.path.join(SAVE_DIR, "*.json"))
            for f in existing_saves:
                try: os.remove(f)
                except: pass
        session.active_campaign_id = create_new_campaign()
        session.state = StateEnum.LORE_PROMPT
        return {"action": "prompt", "message": "[Sistema] Deseja aprender sobre o Mundo das Trevas antes de começar? (sim/não)"}

    # ROUTING: LORE
    elif session.state == StateEnum.LORE_PROMPT:
        if "sim" in user_input:
            session.state = StateEnum.LORE_QA
            return {"action": "chat_response", "message": f"{LORE_PILLARS}\n\n[Sistema] Você pode fazer perguntas curtas sobre o cenário. Digite 'começar' para iniciar o jogo."}
        else:
            session.state = StateEnum.PLAYING
            return {"action": "chat_response", "message": "[Sistema] Adentrando as sombras. A campanha começou. (Pode narrar sua primeira ação)."}

    elif session.state == StateEnum.LORE_QA:
        if "começar" in user_input or "iniciar" in user_input:
            session.state = StateEnum.PLAYING
            return {"action": "chat_response", "message": "[Sistema] A campanha começou. (Pode narrar sua primeira ação)."}
        else:
            reply = await llm_request([
                {"role": "system", "content": f"{STORYTELLER_SYSTEM_PROMPT}\nResponda estritamente sobre o Lore do Mundo das Trevas, seja conciso.\n{LORE_PILLARS}"},
                {"role": "user", "content": action.user_input}
            ])
            return {"action": "chat_response", "message": reply}

    # ROUTING: CHOOSE CAMPAIGN
    elif session.state == StateEnum.CHOOSE_CAMPAIGN:
        try:
            choice = int(user_input)
            chosen_file = session.temp_campaigns[choice]
            with open(chosen_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            session.active_campaign_id = data.get("session_id")
            last_scene = data.get("last_scene", "Cena desconhecida.")
            
            session.state = StateEnum.PLAYING
            
            reply = await llm_request([
                {"role": "system", "content": STORYTELLER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Resuma este evento passado e coloque o jogador de volta na ação. Última cena: {last_scene}"}
            ])
            return {"action": "chat_response", "message": f"[Sistema] Campanha Carregada.\n{reply}"}
        except Exception:
            return {"action": "prompt", "message": "[Sistema] Escolha inválida. Digite apenas o número correspondente à campanha."}

    # ROUTING: PLAYING
    elif session.state == StateEnum.PLAYING:
        reply = await llm_request([
            {"role": "system", "content": STORYTELLER_SYSTEM_PROMPT},
            {"role": "user", "content": action.user_input}
        ])
        return {"action": "chat_response", "message": reply}

    return {"action": "error", "message": "[Sistema] Estado não catalogado na máquina de estados."}
