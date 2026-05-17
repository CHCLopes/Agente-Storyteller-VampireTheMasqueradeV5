import json
import httpx
import re
import os
from .rules_service import V5ActionPayload, calculate_resolution, ResolutionResult, PlayerSheetModel
from .economy_service import rouse_check, feed
from .combat_service import calculate_damage, apply_damage_to_tracker
from .discipline_service import get_power_cost, apply_power_modifiers
from .metagame_service import get_blood_surge_bonus, apply_willpower_reroll

LM_STUDIO_BASE_URL = "http://localhost:1234/v1"

def load_skill_prompt(skill_name: str) -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", f"{skill_name}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

H1_PROMPT = load_skill_prompt("H1_vtm_rules_parser")
STORYTELLER_SYSTEM_PROMPT = load_skill_prompt("H6_vtm_narrator")

async def extract_intent(user_input: str) -> V5ActionPayload:
    h1_payload = {
        "messages": [
            {"role": "system", "content": H1_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.1,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{LM_STUDIO_BASE_URL}/chat/completions", json=h1_payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        h1_reply = data["choices"][0]["message"]["content"]
        
        json_match = re.search(r'\{.*\}', h1_reply, re.DOTALL)
        raw_json = json_match.group(0) if json_match else h1_reply
        return V5ActionPayload(**json.loads(raw_json))

async def run_narrator(user_input: str, system_log: str) -> str:
    h6_payload = {
        "messages": [
            {"role": "system", "content": STORYTELLER_SYSTEM_PROMPT},
            {"role": "user", "content": f"{user_input}\n{system_log}"}
        ],
        "temperature": 0.7,
        "stream": False
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{LM_STUDIO_BASE_URL}/chat/completions", json=h6_payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "saves")
os.makedirs(SAVE_DIR, exist_ok=True)

def save_session_state(session_id: str, session_data: dict, chronicle_name: str, turn: int):
    save_data = {
        "session_id": session_id,
        "chronicle_name": chronicle_name,
        "turn": turn,
        "context": session_data
    }
    safe_filename = os.path.basename(f"{session_id}.json")
    with open(os.path.join(SAVE_DIR, safe_filename), "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=4)

async def process_turn_pipeline(user_input: str, session_id: str, context: dict, turn: int, chronicle_name: str) -> tuple[str, dict]:
    from .rules_service import V5ActionTarget
    
    try:
        action_payload = await extract_intent(user_input)
    except Exception as e:
        return f"[ERROR Parser H1] {str(e)}", context

    player_sheet_dict = context.get("player_sheet", {})
    try:
        player_sheet = PlayerSheetModel(**player_sheet_dict)
    except Exception as e:
        return f"[ERROR Player Sheet Validation] {str(e)}", context

    status = player_sheet.status
    current_hunger = status.current_hunger
    health = status.health_tracker
    willpower = status.willpower_tracker
    
    if action_payload.is_willpower_reroll:
        cache = context.get("last_action_cache")
        if not cache:
            return "[ERROR_404]: Nenhum cache para rerrolar.", context
        
        last_res = ResolutionResult(**cache["resolution"])
        payload_cache = V5ActionPayload(**cache["payload"])
        
        if payload_cache.action_target == V5ActionTarget.UNOPPOSED:
            target_successes = payload_cache.inferred_difficulty
        else:
            target_successes = payload_cache.npc_threat_level
            
        new_res = apply_willpower_reroll(last_res, target_successes)
        
        wp_res = apply_damage_to_tracker(
            tracker_size=willpower.size, superficial=willpower.superficial, aggravated=willpower.aggravated, incoming_damage=1, damage_type="superficial"
        )
        willpower.superficial = wp_res.superficial_damage
        willpower.aggravated = wp_res.aggravated_damage
        
        combat_log = ""
        if payload_cache.is_aggressive:
            snapshot = context.get("pre_roll_snapshot")
            if snapshot and "health_tracker" in snapshot:
                health.size = snapshot["health_tracker"]["size"]
                health.superficial = snapshot["health_tracker"]["superficial"]
                health.aggravated = snapshot["health_tracker"]["aggravated"]

            margin = max(0, new_res.margin)
            damage_res = calculate_damage(
                margin=margin, weapon_category=payload_cache.weapon_category.value, is_bane=cache["is_bane"], is_target_vampire=True, weapon_damage_bonus=cache["power_weapon_bonus"]
            )
            
            tracker_res = apply_damage_to_tracker(
                tracker_size=health.size, superficial=health.superficial, aggravated=health.aggravated, incoming_damage=damage_res.total_damage, damage_type=damage_res.damage_type
            )
            health.superficial = tracker_res.superficial_damage
            health.aggravated = tracker_res.aggravated_damage
            
            combat_log = f"Novo Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({payload_cache.weapon_category.value}). "
            
        context["last_action_cache"]["resolution"] = new_res.model_dump()
        
        h6_system_log = (
            f"[SYSTEM LOG]: Ação: Rerrolar Força de Vontade. "
            f"Resultado: {new_res.summary} "
            f"{combat_log}"
            f"Fome atual: {current_hunger}. "
            f"Dano de Vontade: 1 Superficial. "
            f"Willpower Reroll Aplicado: Sim."
        )
    else:
        context["pre_roll_snapshot"] = {
            "health_tracker": health.model_dump(),
            "willpower_tracker": willpower.model_dump()
        }
        
        attr_val = player_sheet.attributes.get(action_payload.attribute.value, 1)
        skill_val = player_sheet.skills.get(action_payload.skill.value, 0)
        base_pool = attr_val + skill_val
        
        power_weapon_bonus = 0
        current_is_bane = action_payload.is_bane_damage
        
        economy_log = ""
        power_log = ""
        combat_log = ""
        
        if action_payload.is_blood_surge:
            rouse_res = rouse_check(current_hunger, rouse_level=1)
            current_hunger = rouse_res.new_hunger
            surge_bonus = get_blood_surge_bonus(status.blood_potency)
            base_pool += surge_bonus
            economy_log += f"(Surto: +{surge_bonus} dados. {rouse_res.summary}) "
            
        if action_payload.power_used:
            cost = get_power_cost(action_payload.power_used)
            if cost > 0:
                rouse_res = rouse_check(current_hunger, rouse_level=cost)
                current_hunger = rouse_res.new_hunger
                power_log += f"(Poder: {action_payload.power_used}. {rouse_res.summary}) "
            
            modifiers = apply_power_modifiers(action_payload.power_used, current_is_bane, player_sheet_dict)
            base_pool += modifiers.dice_bonus
            power_weapon_bonus = modifiers.weapon_damage_bonus
            current_is_bane = modifiers.is_bane
            
        if action_payload.is_feeding:
            feed_res = feed(current_hunger, slake_amount=2, target_killed=action_payload.target_killed)
            current_hunger = feed_res.new_hunger
            economy_log += f"(Alimentação: {feed_res.summary}) "

        resolution = calculate_resolution(action_payload, current_hunger, dice_pool=base_pool)
        
        context["last_action_cache"] = {
            "resolution": resolution.model_dump(),
            "payload": action_payload.model_dump(),
            "is_bane": current_is_bane,
            "power_weapon_bonus": power_weapon_bonus
        }
        
        if action_payload.is_aggressive:
            margin = max(0, resolution.margin)
            damage_res = calculate_damage(
                margin=margin, weapon_category=action_payload.weapon_category.value, is_bane=current_is_bane, is_target_vampire=True, weapon_damage_bonus=power_weapon_bonus
            )
            tracker_res = apply_damage_to_tracker(
                tracker_size=health.size, superficial=health.superficial, aggravated=health.aggravated, incoming_damage=damage_res.total_damage, damage_type=damage_res.damage_type
            )
            health.superficial = tracker_res.superficial_damage
            health.aggravated = tracker_res.aggravated_damage
            
            weapon_desc = action_payload.power_used if action_payload.power_used else action_payload.weapon_category.value
            combat_log = f"Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({weapon_desc}). "
            
        status.current_hunger = current_hunger
        
        h6_system_log = (
            f"[SYSTEM LOG]: Ação: {action_payload.intent}. "
            f"Resultado: {resolution.summary} "
            f"{combat_log}"
            f"Fome atual: {current_hunger}. "
            f"{power_log}{economy_log}"
            f"Willpower Reroll Aplicado: Não."
        )

    context["player_sheet"] = player_sheet.model_dump()
    save_session_state(session_id, context, chronicle_name, turn)
    
    try:
        reply = await run_narrator(user_input, h6_system_log)
        return reply, context
    except Exception as e:
        return f"[H6 Error] {str(e)}", context
