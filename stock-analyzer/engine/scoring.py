from typing import Literal

Trend = Literal["BULLISH", "BEARISH", "RANGE"]
Bias = Literal["BULLISH", "BEARISH", "NEUTRAL"]


def compute_confidence(
    trend: Trend,
    ema_bias: Bias,
    volume_confirmed: bool,
    risk_reward: float,
    rr_min: float,
) -> int:
    """
    Simple deterministic confidence score (0-100).
    Designed to be transparent rather than predictive.
    """
    score = 50

    if trend == ema_bias:
        score += 15
    elif ema_bias == "NEUTRAL":
        score -= 10
    else:
        score -= 15

    if volume_confirmed:
        score += 15
    else:
        score -= 20

    if risk_reward >= rr_min + 0.5:
        score += 10
    elif risk_reward < rr_min:
        score -= 20

    return max(0, min(100, score))
