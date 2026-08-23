def score_term(strokes: int, penalty_strokes: int, par: int) -> str:
    if strokes == 1 and penalty_strokes == 0:
        return "ace"

    diff = strokes + penalty_strokes - par
    if diff <= -2:
        return "eagle"
    if diff == -1:
        return "birdie"
    if diff == 0:
        return "par"
    if diff == 1:
        return "bogey"
    return "double_bogey_or_worse"
