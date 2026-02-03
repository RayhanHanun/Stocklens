from typing import List, Optional


def ema(values: List[float], period: int) -> List[Optional[float]]:
    """
    Exponential moving average.

    Returns a list the same length as input. Values before the first
    complete period are None. The first EMA value is seeded with SMA.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    count = len(values)
    if count < period:
        return [None] * count

    ema_values: List[Optional[float]] = [None] * count
    sma = sum(values[:period]) / period
    ema_values[period - 1] = sma

    multiplier = 2 / (period + 1)
    prev = sma
    for i in range(period, count):
        prev = (values[i] - prev) * multiplier + prev
        ema_values[i] = prev

    return ema_values
