from typing import List, Optional


def sma(values: List[float], period: int) -> List[Optional[float]]:
    if period <= 0:
        raise ValueError("period must be > 0")

    count = len(values)
    if count < period:
        return [None] * count

    sma_values: List[Optional[float]] = [None] * count
    window_sum = sum(values[:period])
    sma_values[period - 1] = window_sum / period

    for i in range(period, count):
        window_sum = window_sum - values[i - period] + values[i]
        sma_values[i] = window_sum / period

    return sma_values


def is_volume_confirmed(volumes: List[float], period: int = 20, multiplier: float = 1.0) -> bool:
    """
    Volume confirmation: latest volume must be at or above SMA(period).
    """
    if len(volumes) < period:
        return False

    volume_ma = sma(volumes, period)
    latest_ma = volume_ma[-1]
    if latest_ma is None:
        return False

    return volumes[-1] >= latest_ma * multiplier
