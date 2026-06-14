import random
from .rules_service import ResolutionResult

def apply_willpower_reroll(last_resolution: ResolutionResult, target_successes: int) -> ResolutionResult:
    import random
    
    rerollable_dice = [d for d in last_resolution.normal_rolls if d < 10]
    reroll_count = min(3, len(rerollable_dice))
    
    kept_normal_rolls = last_resolution.normal_rolls.copy()
    for _ in range(reroll_count):
        if min(kept_normal_rolls) < 10:
            kept_normal_rolls.remove(min(kept_normal_rolls))
            
    new_rolls = [random.randint(1, 10) for _ in range(reroll_count)]
    final_normal_rolls = kept_normal_rolls + new_rolls
    
    successes = sum(1 for d in final_normal_rolls if d >= 6) + sum(1 for d in last_resolution.hunger_rolls if d >= 6)
    
    hunger_10s = sum(1 for d in last_resolution.hunger_rolls if d == 10)
    normal_10s = sum(1 for d in final_normal_rolls if d == 10)
    total_10s = hunger_10s + normal_10s
    
    crit_pairs = total_10s // 2
    successes += crit_pairs * 2
    
    margin = successes - target_successes
    is_success = margin >= 0
    
    messy_critical = (crit_pairs > 0) and (hunger_10s > 0)
    bestial_failure = any(d == 1 for d in last_resolution.hunger_rolls)
    
    summary = f"Rerrolagem (Força de Vontade). {successes} sucessos (Margem {margin})."
    if messy_critical: summary += " [Messy Critical]"
    if bestial_failure: summary += " [Bestial Failure]"
    
    return ResolutionResult(
        successes=successes,
        is_success=is_success,
        bestial_failure=bestial_failure,
        messy_critical=messy_critical,
        summary=summary,
        normal_rolls=final_normal_rolls,
        hunger_rolls=last_resolution.hunger_rolls,
        margin=margin
    )
