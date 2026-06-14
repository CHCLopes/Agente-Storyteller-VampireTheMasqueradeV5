from enum import Enum
from pydantic import BaseModel, Field
import random

class V5Attribute(str, Enum):
    Strength = "Strength"
    Dexterity = "Dexterity"
    Stamina = "Stamina"
    Charisma = "Charisma"
    Manipulation = "Manipulation"
    Composure = "Composure"
    Intelligence = "Intelligence"
    Wits = "Wits"
    Resolve = "Resolve"

class V5Skill(str, Enum):
    ATHLETICS = "Athletics"
    BRAWL = "Brawl"
    CRAFT = "Craft"
    DRIVE = "Drive"
    FIREARMS = "Firearms"
    LARCENY = "Larceny"
    MELEE = "Melee"
    STEALTH = "Stealth"
    SURVIVAL = "Survival"
    ANIMAL_KEN = "AnimalKen"
    ETIQUETTE = "Etiquette"
    INSIGHT = "Insight"
    INTIMIDATION = "Intimidation"
    LEADERSHIP = "Leadership"
    PERFORMANCE = "Performance"
    PERSUASION = "Persuasion"
    STREETWISE = "Streetwise"
    SUBTERFUGE = "Subterfuge"
    ACADEMICS = "Academics"
    AWARENESS = "Awareness"
    FINANCE = "Finance"
    INVESTIGATION = "Investigation"
    MEDICINE = "Medicine"
    OCCULT = "Occult"
    POLITICS = "Politics"
    SCIENCE = "Science"
    TECHNOLOGY = "Technology"

class V5WeaponCategory(str, Enum):
    UNARMED = "unarmed"
    LIGHT_MELEE = "light_melee"
    HEAVY_MELEE = "heavy_melee"
    LIGHT_FIREARM = "light_firearm"
    HEAVY_FIREARM = "heavy_firearm"
    INCENDIARY = "incendiary"
    ELECTRICAL = "electrical"
    CHEMICAL = "chemical"
    HEAVY_MACHINERY = "heavy_machinery"
    HOLY_ARTIFACT = "holy_artifact"

class V5ActionTarget(str, Enum):
    UNOPPOSED = "UNOPPOSED"
    OPPOSED = "OPPOSED"

from typing import Dict

class TrackerModel(BaseModel):
    size: int
    superficial: int
    aggravated: int

class StatusModel(BaseModel):
    blood_potency: int
    current_hunger: int
    humanity: int
    health_tracker: TrackerModel
    willpower_tracker: TrackerModel
    stains: int = 0

class PredatorEngineData(BaseModel):
    hunting_pool: list[str]
    blood_resonance_preference: str

class PredatorNarrativeData(BaseModel):
    description: str
    hunting_method: str

class PredatorTypeModel(BaseModel):
    engine_data: PredatorEngineData
    narrative_data: PredatorNarrativeData

class BloodPotencyEngineData(BaseModel):
    blood_surge_bonus: int
    damage_healed_per_rouse: int
    bane_severity: int
    rouse_reroll_level: int

class BloodPotencyModel(BaseModel):
    engine_data: BloodPotencyEngineData

class PlayerSheetModel(BaseModel):
    nome: str = "Neófito"
    geracao: str = "13ª Geração"
    clan: str = "brujah"
    predator_type: str = "alleycat"
    attributes: Dict[str, int]
    skills: Dict[str, int]
    disciplines: Dict[str, int]
    status: StatusModel
    available_xp: int = 0
    spent_xp: int = 0

class V5ActionPayload(BaseModel):
    intent: str
    attribute: V5Attribute
    skill: V5Skill
    power_used: str | None = None
    weapon_category: V5WeaponCategory = V5WeaponCategory.UNARMED
    is_aggressive: bool
    is_feeding: bool = False
    is_healing: bool = False
    target_killed: bool = False
    is_bane_damage: bool = False
    is_blood_surge: bool = False
    is_willpower_reroll: bool = False
    is_compulsion_active: bool = False
    is_true_faith_active: bool = False
    action_target: V5ActionTarget = V5ActionTarget.UNOPPOSED
    inferred_difficulty: int = Field(default=3, ge=1, le=7)
    npc_threat_level: int = Field(default=2, ge=1, le=5)

class ResolutionResult(BaseModel):
    successes: int
    is_success: bool
    bestial_failure: bool
    messy_critical: bool
    summary: str
    normal_rolls: list[int]
    hunger_rolls: list[int]
    margin: int = 0

def _roll_v5_dice(dice_pool: int, hunger: int, difficulty: int = 0) -> ResolutionResult:
    """
    Motor matemático V5 estrito.
    """
    # 1. Definição das pilhas de dados
    hunger_dice_count = min(hunger, dice_pool)
    normal_dice_count = dice_pool - hunger_dice_count
    
    # 2. Rolagem (D10)
    normal_rolls = [random.randint(1, 10) for _ in range(normal_dice_count)]
    hunger_rolls = [random.randint(1, 10) for _ in range(hunger_dice_count)]
    
    # 3. Cálculo de sucessos base (>= 6)
    normal_successes = sum(1 for d in normal_rolls if d >= 6)
    hunger_successes = sum(1 for d in hunger_rolls if d >= 6)
    base_successes = normal_successes + hunger_successes
    
    # 4. Análise de Críticos (Pares de 10)
    normal_tens = normal_rolls.count(10)
    hunger_tens = hunger_rolls.count(10)
    total_tens = normal_tens + hunger_tens
    
    critical_pairs = total_tens // 2
    critical_bonus = critical_pairs * 2
    
    total_successes = base_successes + critical_bonus
    
    # 5. Filtro da Besta (Condições de Estado)
    is_messy_critical = critical_pairs > 0 and hunger_tens > 0
    is_failure = total_successes < difficulty
    is_bestial_failure = is_failure and (1 in hunger_rolls)

    if is_bestial_failure:
        summary = "A Besta ataca. Falha catastrófica movida pela fome."
    elif is_messy_critical:
        summary = "Sucesso extremo, mas brutal e descuidado. A Besta cobrou seu preço."
    elif not is_failure:
        summary = f"Ação executada com {total_successes} sucesso(s)."
    else:
        summary = f"Falha na ação. Apenas {total_successes} sucesso(s) obtido(s)."

    # 6. Retorno Estruturado Pydantic
    return ResolutionResult(
        successes=total_successes,
        is_success=not is_failure,
        bestial_failure=is_bestial_failure,
        messy_critical=is_messy_critical,
        summary=summary,
        normal_rolls=normal_rolls,
        hunger_rolls=hunger_rolls
    )

def calculate_resolution(payload: V5ActionPayload, current_hunger: int, dice_pool: int) -> ResolutionResult:
    normal_dice = max(0, dice_pool - current_hunger)
    hunger_dice = min(dice_pool, current_hunger)
    
    normal_rolls = [random.randint(1, 10) for _ in range(normal_dice)]
    hunger_rolls = [random.randint(1, 10) for _ in range(hunger_dice)]
    
    successes = sum(1 for d in normal_rolls if d >= 6) + sum(1 for d in hunger_rolls if d >= 6)
    
    hunger_10s = sum(1 for d in hunger_rolls if d == 10)
    normal_10s = sum(1 for d in normal_rolls if d == 10)
    total_10s = hunger_10s + normal_10s
    
    crit_pairs = total_10s // 2
    successes += crit_pairs * 2
    
    if payload.action_target == V5ActionTarget.UNOPPOSED:
        target = payload.inferred_difficulty
    else:
        target = payload.npc_threat_level
        
    margin = successes - target
    is_success = margin >= 0
    
    messy_critical = (crit_pairs > 0) and (hunger_10s > 0)
    bestial_failure = any(d == 1 for d in hunger_rolls) and not is_success
    
    summary = f"Rolagem Concluída. {successes} sucessos (Margem {margin})."
    if messy_critical:
        summary += " [Messy Critical]"
    if bestial_failure:
        summary += " [Bestial Failure]"
    
    return ResolutionResult(
        successes=successes,
        is_success=is_success,
        bestial_failure=bestial_failure,
        messy_critical=messy_critical,
        summary=summary,
        normal_rolls=normal_rolls,
        hunger_rolls=hunger_rolls,
        margin=margin
    )

def calculate_remorse(sheet: PlayerSheetModel) -> PlayerSheetModel:
    """
    Mecânica de Remorso e degeneração de Humanidade baseada em máculas (stains).
    """
    stains = sheet.status.stains
    if stains == 0:
        return sheet
        
    pool = max(10 - stains, 1)
    roll_res = _roll_v5_dice(dice_pool=pool, hunger=0, difficulty=1)
    
    if roll_res.successes == 0:
        sheet.status.humanity = max(0, sheet.status.humanity - 1)
        
    sheet.status.stains = 0
    return sheet
