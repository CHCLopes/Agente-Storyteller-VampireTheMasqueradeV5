import os
import httpx
import json
from .rules_service import V5ActionPayload, calculate_resolution, ResolutionResult, PlayerSheetModel
from .economy_service import rouse_check, feed
from .combat_service import calculate_damage, apply_damage_to_tracker
from .discipline_service import get_power_cost, apply_power_modifiers
from .metagame_service import apply_willpower_reroll
from .physiology_service import get_blood_surge_bonus, get_healing_amount
from .parser_service import extract_intent
from .core.config import Settings

settings = Settings()

def load_skill_prompt(skill_name: str) -> str:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills", f"{skill_name}.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

STORYTELLER_SYSTEM_PROMPT = load_skill_prompt("H6_vtm_narrator")

class SystemLogBuilder:
    def __init__(self):
        self.action = ""
        self.result = ""
        self.combat_log = ""
        self.hunger = 0
        self.power_log = ""
        self.economy_log = ""
        self.willpower_reroll = "Não"
        self.lore_context = ""
        self.memory_context = ""
        self.relationship_context = ""
        
    def build(self) -> str:
        log = (
            f"[SYSTEM LOG]: Ação: {self.action}. "
            f"Resultado: {self.result} "
            f"{self.combat_log}"
            f"Fome atual: {self.hunger}. "
            f"{self.power_log}{self.economy_log}"
            f"Willpower Reroll Aplicado: {self.willpower_reroll}."
        )
        if self.lore_context:
            log += f"\n{self.lore_context}"
        if self.memory_context:
            log += f"\n{self.memory_context}"
        if self.relationship_context:
            log += f"\n{self.relationship_context}"
        return log

async def run_narrator_stream(user_input: str, system_log: str, player_sheet: dict | None = None):
    system_content = STORYTELLER_SYSTEM_PROMPT
    if player_sheet:
        status = player_sheet.get("status", {})
        health = status.get("health_tracker", {})
        willpower = status.get("willpower_tracker", {})
        
        char_context = (
            f"\n\n## FICHA ATUAL DO PERSONAGEM (CONTEXTO DE REGRAS):\n"
            f"- Clã: {player_sheet.get('clan', 'Desconhecido')}\n"
            f"- Tipo de Predador: {player_sheet.get('predator_type', 'Desconhecido')}\n"
            f"- Fome: {status.get('current_hunger', 0)}\n"
            f"- Humanidade: {status.get('humanity', 7)}\n"
            f"- Vida (Tracker): Superficial {health.get('superficial', 0)}, Agravado {health.get('aggravated', 0)} (Tamanho Máximo: {health.get('size', 7)})\n"
            f"- Força de Vontade (Tracker): Superficial {willpower.get('superficial', 0)}, Agravado {willpower.get('aggravated', 0)} (Tamanho Máximo: {willpower.get('size', 5)})\n"
        )
        system_content += char_context

    h6_payload = {
        "model": settings.LMSTUDIO_MODEL,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{user_input}\n{system_log}"}
        ],
        "temperature": 0.7,
        "stream": True
    }
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{settings.lm_studio_base_url}/chat/completions", json=h6_payload, timeout=float(settings.LMSTUDIO_TIMEOUT)) as response:
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    data_str = chunk[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "content" in data["choices"][0]["delta"]:
                            yield data["choices"][0]["delta"]["content"]
                    except Exception:
                        pass

async def process_turn_pipeline(user_input: str, session_id: str, context: dict, turn: int, chronicle_name: str) -> tuple[str, dict]:
    from .rules_service import V5ActionTarget
    import re
    
    try:
        action_payload = await extract_intent(user_input)
        if action_payload.intent.startswith("[FALLBACK]"):
            return f"[ERROR Parser H1] {action_payload.intent}", context
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
    
    log_builder = SystemLogBuilder()
    
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
        
        willpower.superficial += 1
        
        if payload_cache.is_aggressive:
            snapshot = context.get("pre_roll_snapshot")
            if snapshot and "health_tracker" in snapshot:
                health.size = snapshot["health_tracker"]["size"]
                health.superficial = snapshot["health_tracker"]["superficial"]
                health.aggravated = snapshot["health_tracker"]["aggravated"]

            margin = max(0, new_res.margin)
            damage_res = calculate_damage(
                margin=margin, weapon_category=payload_cache.weapon_category.value, is_bane=cache["is_bane"], is_supernatural_target=cache.get("is_supernatural_target", True), weapon_damage_bonus=cache["power_weapon_bonus"], is_true_faith_active=payload_cache.is_true_faith_active
            )
            
            tracker_res = apply_damage_to_tracker(
                tracker_size=health.size, superficial=health.superficial, aggravated=health.aggravated, incoming_damage=damage_res.total_damage, damage_type=damage_res.damage_type
            )
            health.superficial = tracker_res.superficial_damage
            health.aggravated = tracker_res.aggravated_damage
            
            log_builder.combat_log = f"Novo Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({payload_cache.weapon_category.value}). "
            
        context["last_action_cache"]["resolution"] = new_res.model_dump()
        
        log_builder.action = "Rerrolar Força de Vontade"
        log_builder.result = new_res.summary
        log_builder.economy_log = "Dano de Vontade: 1 Superficial. "
        log_builder.willpower_reroll = "Sim"

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
        
        if action_payload.is_blood_surge:
            rouse_res = rouse_check(current_hunger, rouse_level=1)
            current_hunger = rouse_res.new_hunger
            surge_bonus = get_blood_surge_bonus(status.blood_potency)
            base_pool += surge_bonus
            log_builder.economy_log += f"(Surto: +{surge_bonus} dados. {rouse_res.summary}) "
            
        if action_payload.is_healing:
            heal_amount = get_healing_amount(status.blood_potency)
            rouse_res = rouse_check(current_hunger, rouse_level=1)
            current_hunger = rouse_res.new_hunger
            healed = min(heal_amount, health.superficial)
            health.superficial -= healed
            log_builder.economy_log += f"(Cura Mending: {healed} Superficial curado. {rouse_res.summary}) "
            
        if action_payload.power_used:
            cost = get_power_cost(action_payload.power_used)
            if cost > 0 and current_hunger >= 5:
                log_builder.power_log += f"(Poder falhou: {action_payload.power_used}. Fome muito alta para Rouse Check.) "
            else:
                if cost > 0:
                    rouse_res = rouse_check(current_hunger, rouse_level=cost)
                    current_hunger = rouse_res.new_hunger
                    log_builder.power_log += f"(Poder: {action_payload.power_used}. {rouse_res.summary}) "
                
                modifiers = apply_power_modifiers(action_payload.power_used, current_is_bane, player_sheet_dict)
                base_pool += modifiers.dice_bonus
                power_weapon_bonus = modifiers.weapon_damage_bonus
                current_is_bane = modifiers.is_bane
            
        if action_payload.is_feeding:
            feed_res = feed(current_hunger, slake_amount=2, target_killed=action_payload.target_killed)
            current_hunger = feed_res.new_hunger
            log_builder.economy_log += f"(Alimentação: {feed_res.summary}) "

        from .clan_service import get_clan_engine
        compulsion_penalty = 0
        if action_payload.is_compulsion_active:
            engine = get_clan_engine(player_sheet.clan)
            if engine:
                compulsion_penalty = engine.compulsion_dice_penalty
                base_pool -= compulsion_penalty
                base_pool = max(0, base_pool)
                log_builder.economy_log += f"(Compulsão Ativa: -{compulsion_penalty} dados) "

        from .npc_service import get_all_npcs
        npcs = get_all_npcs()
        normalized_input = user_input.lower().replace('í', 'i').replace('ç', 'c')
        active_npc = None
        for npc_key in npcs.keys():
            if re.search(r'\b' + re.escape(npc_key) + r'\b', normalized_input):
                active_npc = npcs[npc_key]
                break

        if active_npc and action_payload.skill.value in ["Persuasion", "Subterfuge", "Intimidation"]:
            reduction = active_npc.engine_data.corruption_index - 1
            if action_payload.action_target == V5ActionTarget.UNOPPOSED:
                action_payload.inferred_difficulty = max(1, action_payload.inferred_difficulty - reduction)
            else:
                action_payload.npc_threat_level = max(1, action_payload.npc_threat_level - reduction)
            log_builder.economy_log += f"(Corrupção do Alvo: Dificuldade reduzida em {reduction}) "

        resolution = calculate_resolution(action_payload, current_hunger, dice_pool=base_pool)
        
        context["last_action_cache"] = {
            "resolution": resolution.model_dump(),
            "payload": action_payload.model_dump(),
            "is_bane": current_is_bane,
            "power_weapon_bonus": power_weapon_bonus,
            "is_supernatural_target": active_npc.engine_data.is_supernatural if active_npc else True
        }
        
        if action_payload.is_aggressive:
            margin = max(0, resolution.margin)
            damage_res = calculate_damage(
                margin=margin, weapon_category=action_payload.weapon_category.value, is_bane=current_is_bane, is_supernatural_target=context["last_action_cache"]["is_supernatural_target"], weapon_damage_bonus=power_weapon_bonus, is_true_faith_active=action_payload.is_true_faith_active
            )
            tracker_res = apply_damage_to_tracker(
                tracker_size=health.size, superficial=health.superficial, aggravated=health.aggravated, incoming_damage=damage_res.total_damage, damage_type=damage_res.damage_type
            )
            health.superficial = tracker_res.superficial_damage
            health.aggravated = tracker_res.aggravated_damage
            
            weapon_desc = action_payload.power_used if action_payload.power_used else action_payload.weapon_category.value
            log_builder.combat_log = f"Dano causado: {damage_res.total_damage} {damage_res.damage_type} ({weapon_desc}). "
            
        log_builder.action = action_payload.intent
        log_builder.result = resolution.summary

    status.current_hunger = current_hunger
    log_builder.hunger = current_hunger
    
    context["player_sheet"] = player_sheet.model_dump()
    
    from .lore_service import get_contextual_lore
    lore_context = get_contextual_lore(user_input, action_payload, player_sheet)
    if lore_context:
        log_builder.lore_context = lore_context

    # --- Camada de Memória (E-02/E-03) ---
    from .memory_service import load_memory, save_memory, update_scene_memory, build_memory_prompt_fragment
    session_memory = await load_memory(session_id)
    partial_log = log_builder.build()
    session_memory = update_scene_memory(session_memory, partial_log, user_input, turn)
    memory_fragment = build_memory_prompt_fragment(session_memory)
    if memory_fragment:
        log_builder.memory_context = memory_fragment
    await save_memory(session_memory)

    # --- Motor Relacional — Camada 2 (E-01) ---
    from .relationship_service import (
        load_relationships, save_relationships,
        update_relationships_from_action, build_relationship_prompt_fragment,
        get_relationships_for_frontend
    )
    rel_state = await load_relationships(session_id)
    is_aggressive = action_payload.is_aggressive if action_payload else False
    rel_state = update_relationships_from_action(rel_state, user_input, partial_log, is_aggressive, turn)
    rel_fragment = build_relationship_prompt_fragment(rel_state)
    if rel_fragment:
        log_builder.relationship_context = rel_fragment
    await save_relationships(rel_state)
    relationships_for_frontend = get_relationships_for_frontend(rel_state)

    return log_builder.build(), context, relationships_for_frontend
