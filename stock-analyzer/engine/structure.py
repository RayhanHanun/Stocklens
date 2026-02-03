from typing import Dict, List, Optional


def _find_swings(values: List[float], lookback: int = 20, pivot: int = 2) -> List[Dict[str, int]]:
    """
    Identify swing points using a simple pivot method.
    A swing high is higher than `pivot` bars on both sides.
    A swing low is lower than `pivot` bars on both sides.
    """
    swings: List[Dict[str, int]] = []
    start = max(0, len(values) - lookback)
    end = len(values) - pivot

    for i in range(start + pivot, end):
        left = values[i - pivot:i]
        right = values[i + 1:i + 1 + pivot]
        if not right:
            continue
        if values[i] > max(left) and values[i] > max(right):
            swings.append({"index": i, "value": values[i], "type": "high"})
        if values[i] < min(left) and values[i] < min(right):
            swings.append({"index": i, "value": values[i], "type": "low"})

    return swings


def classify_structure(highs: List[float], lows: List[float], lookback: int = 20) -> Dict[str, Optional[float]]:
    """
    Determine market structure using recent swing highs/lows.
    Returns trend and the most recent swing levels.
    """
    swing_highs = [s for s in _find_swings(highs, lookback=lookback) if s["type"] == "high"]
    swing_lows = [s for s in _find_swings(lows, lookback=lookback) if s["type"] == "low"]

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "trend": "RANGE",
            "last_swing_high": None,
            "last_swing_low": None,
            "prev_swing_high": None,
            "prev_swing_low": None,
        }

    last_high = swing_highs[-1]["value"]
    prev_high = swing_highs[-2]["value"]
    last_low = swing_lows[-1]["value"]
    prev_low = swing_lows[-2]["value"]

    if last_high > prev_high and last_low > prev_low:
        trend = "BULLISH"
    elif last_high < prev_high and last_low < prev_low:
        trend = "BEARISH"
    else:
        trend = "RANGE"

    return {
        "trend": trend,
        "last_swing_high": last_high,
        "last_swing_low": last_low,
        "prev_swing_high": prev_high,
        "prev_swing_low": prev_low,
    }
