from decimal import Decimal

def clamp(value,low,high): return max(Decimal(str(low)),min(Decimal(str(high)),Decimal(str(value))))
def opponent_factor(rating): return clamp(Decimal("1")+(Decimal(str(rating))-Decimal("1500"))/Decimal("4000"),"0.90","1.10")
def league_factor(league_median,global_median): return clamp(Decimal("1")+(Decimal(str(league_median))-Decimal(str(global_median)))/Decimal("4000"),"0.95","1.05")
def stage_factor(name):
    value=(name or "").lower()
    for terms,factor in [(("final",),"1.10"),(("semi",),"1.08"),(("quarter",),"1.07"),(("round of 16","last 16"),"1.06")]:
        if any(term in value for term in terms): return Decimal(factor)
    return Decimal("1.05")
def match_context(opponent_elo,league="1",competition="1"): return clamp(opponent_factor(opponent_elo)*Decimal(str(league))*Decimal(str(competition)),"0.85","1.20")
