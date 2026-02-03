from typing import List, Optional


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
    """
    Average True Range (ATR) using Wilder's smoothing.
    Returns a list the same length as input. Values before the first
    complete period are None.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    count = len(closes)
    if count == 0 or len(highs) != count or len(lows) != count:
        raise ValueError("highs, lows, closes must be same length")

    true_ranges: List[float] = []
    for i in range(count):
        if i == 0:
            tr = highs[i] - lows[i]
        else:
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            tr = max(high_low, high_close, low_close)
        true_ranges.append(tr)

    atr_values: List[Optional[float]] = [None] * count
    if count < period:
        return atr_values

    first_atr = sum(true_ranges[:period]) / period
    atr_values[period - 1] = first_atr

    prev = first_atr
    for i in range(period, count):
        prev = (prev * (period - 1) + true_ranges[i]) / period
        atr_values[i] = prev

    return atr_values
