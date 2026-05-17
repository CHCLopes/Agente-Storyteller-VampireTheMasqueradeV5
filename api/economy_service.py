from pydantic import BaseModel
import random

class RouseResult(BaseModel):
    new_hunger: int
    rouse_failures: int
    frenzy_warning: bool
    summary: str

class FeedResult(BaseModel):
    new_hunger: int
    slaked: int
    summary: str

def rouse_check(current_hunger: int, rouse_level: int = 1) -> RouseResult:
    failures = sum(1 for _ in range(rouse_level) if random.randint(1, 10) <= 5)
    
    new_hunger = current_hunger + failures
    frenzy_warning = False
    
    if new_hunger > 5:
        frenzy_warning = True
        new_hunger = 5
        
    summary = f"Rouse Check (nv. {rouse_level}): {failures} falha(s). Fome atualizada para {new_hunger}."
    if frenzy_warning:
        summary += " [ALERTA: FOME MÁXIMA ATINGIDA - RISCO DE FRENESI/TORPOR!]"
        
    return RouseResult(
        new_hunger=new_hunger,
        rouse_failures=failures,
        frenzy_warning=frenzy_warning,
        summary=summary
    )

def feed(current_hunger: int, slake_amount: int, target_killed: bool) -> FeedResult:
    new_hunger = current_hunger - slake_amount
    
    if target_killed:
        new_hunger = max(0, new_hunger)
        summary = f"Alimentação fatal (+{slake_amount}). Fome atualizada para {new_hunger}."
    else:
        new_hunger = max(1, new_hunger)
        summary = f"Alimentação contida (+{slake_amount}). Fome atualizada para {new_hunger}."
        
    return FeedResult(
        new_hunger=new_hunger,
        slaked=current_hunger - new_hunger,
        summary=summary
    )
