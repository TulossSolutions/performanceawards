from apps.football.models import Position

BROAD={"GOALKEEPER":Position.GK,"GK":Position.GK,"G":Position.GK,"DEFENDER":Position.DEF,"DEF":Position.DEF,"D":Position.DEF,"MIDFIELDER":Position.MID,"MID":Position.MID,"M":Position.MID,"FORWARD":Position.FWD,"ATTACKER":Position.FWD,"FWD":Position.FWD,"F":Position.FWD}
DETAIL={"CB":Position.DEF,"LB":Position.DEF,"RB":Position.DEF,"LWB":Position.DEF,"RWB":Position.DEF,"DM":Position.MID,"CM":Position.MID,"AM":Position.MID,"LM":Position.MID,"RM":Position.MID,"LW":Position.FWD,"RW":Position.FWD,"CF":Position.FWD,"ST":Position.FWD}
def normalize_position(broad=None,detailed=None,existing=None):
    if broad and broad.upper() in BROAD: return BROAD[broad.upper()]
    if detailed and detailed.upper() in DETAIL: return DETAIL[detailed.upper()]
    return existing if existing in Position.values and existing != Position.UNKNOWN else Position.UNKNOWN
