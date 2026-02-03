from typing import Any, Dict, List, Optional

import pandas as pd

from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import is_volume_confirmed
from engine.scoring import compute_confidence
from engine.structure import classify_structure


MIN_BARS = 60


def _ema_bias(last_close: float, ema20: Optional[float], ema50: Optional[float]) -> str:
    if ema20 is None or ema50 is None:
        return "NEUTRAL"
    if last_close > ema20 and ema20 > ema50:
        return "BULLISH"
    if last_close < ema20 and ema20 < ema50:
        return "BEARISH"
    return "NEUTRAL"


def _atr_percent(atr_value: float, last_close: float) -> float:
    if last_close == 0:
        return 0.0
    return atr_value / last_close


def _build_signal(
    ticker: str,
    mode: str,
    direction: str,
    entry: float,
    stop: float,
    rr_min: float,
    volume_confirmed: bool,
    trend: str,
    ema_bias: str,
    atr_percent: float,
) -> Dict[str, Any]:
    if direction == "LONG":
        risk = entry - stop
        target = entry + risk * rr_min
        risk_reward = (target - entry) / risk if risk > 0 else 0.0
        entry_desc = f"Trigger above {entry:.2f}"
    else:
        risk = stop - entry
        target = entry - risk * rr_min
        risk_reward = (entry - target) / risk if risk > 0 else 0.0
        entry_desc = f"Trigger below {entry:.2f}"

    confidence = compute_confidence(trend, ema_bias, volume_confirmed, risk_reward, rr_min)

    return {
        "ticker": ticker,
        "mode": mode,
        "direction": direction,
        "entry": entry_desc,
        "stop_loss": round(stop, 2),
        "target": round(target, 2),
        "risk_reward": round(risk_reward, 2),
        "confidence": confidence,
        "reasoning": (
            f"Structure {trend}, EMA bias {ema_bias}, volume confirmed {volume_confirmed}, "
            f"ATR% {atr_percent:.3f}."
        ),
    }


def analyze_ticker(df: pd.DataFrame, ticker: str) -> List[Dict[str, Any]]:
    df = df.dropna()
    if len(df) < MIN_BARS:
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "Insufficient data history",
            }
        ]

    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    volumes = df["Volume"].tolist()

    structure = classify_structure(highs, lows)
    trend = structure["trend"]
    if trend == "RANGE":
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "Market structure is range-bound",
            }
        ]

    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    atr14 = atr(highs, lows, closes, 14)

    last_close = closes[-1]
    ema_bias = _ema_bias(last_close, ema20[-1], ema50[-1])

    if (trend == "BULLISH" and ema_bias != "BULLISH") or (trend == "BEARISH" and ema_bias != "BEARISH"):
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "EMA trend bias does not align with structure",
            }
        ]

    volume_confirmed = is_volume_confirmed(volumes, period=20)
    if not volume_confirmed:
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "Price movement lacks volume confirmation",
            }
        ]

    last_atr = atr14[-1]
    if last_atr is None:
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "ATR not available",
            }
        ]

    atr_pct = _atr_percent(last_atr, last_close)
    if atr_pct < 0.005 or atr_pct > 0.15:
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "ATR volatility filter not met",
            }
        ]

    signals: List[Dict[str, Any]] = []

    if trend == "BULLISH":
        entry = structure["last_swing_high"] or highs[-1]
        structure_stop = structure["last_swing_low"]
        atr_stop = last_close - last_atr * 1.5
        stop = min(structure_stop, atr_stop) if structure_stop else atr_stop

        if stop >= entry:
            stop = entry - last_atr * 1.5

        if entry > stop:
            signals.append(
                _build_signal(
                    ticker=ticker,
                    mode="SWING",
                    direction="LONG",
                    entry=entry,
                    stop=stop,
                    rr_min=2.5,
                    volume_confirmed=volume_confirmed,
                    trend=trend,
                    ema_bias=ema_bias,
                    atr_percent=atr_pct,
                )
            )
            signals.append(
                _build_signal(
                    ticker=ticker,
                    mode="DAY_TRADE_PLAN",
                    direction="LONG",
                    entry=entry,
                    stop=stop,
                    rr_min=2.0,
                    volume_confirmed=volume_confirmed,
                    trend=trend,
                    ema_bias=ema_bias,
                    atr_percent=atr_pct,
                )
            )

    if trend == "BEARISH":
        entry = structure["last_swing_low"] or lows[-1]
        structure_stop = structure["last_swing_high"]
        atr_stop = last_close + last_atr * 1.5
        stop = max(structure_stop, atr_stop) if structure_stop else atr_stop

        if stop <= entry:
            stop = entry + last_atr * 1.5

        if stop > entry:
            signals.append(
                _build_signal(
                    ticker=ticker,
                    mode="SWING",
                    direction="SHORT",
                    entry=entry,
                    stop=stop,
                    rr_min=2.5,
                    volume_confirmed=volume_confirmed,
                    trend=trend,
                    ema_bias=ema_bias,
                    atr_percent=atr_pct,
                )
            )
            signals.append(
                _build_signal(
                    ticker=ticker,
                    mode="DAY_TRADE_PLAN",
                    direction="SHORT",
                    entry=entry,
                    stop=stop,
                    rr_min=2.0,
                    volume_confirmed=volume_confirmed,
                    trend=trend,
                    ema_bias=ema_bias,
                    atr_percent=atr_pct,
                )
            )

    if not signals:
        return [
            {
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "Risk parameters invalid",
            }
        ]

    return signals
