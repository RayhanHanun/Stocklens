from typing import Any, Dict, Optional
import pandas as pd
import numpy as np

# Import Indikator
from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import sma as vol_sma
from engine.indicators.rsi import rsi

# KONFIGURASI GLOBAL
MIN_BARS = 100
MIN_TX_VALUE = 2_000_000_000 # Minimal transaksi 2 Miliar

def analyze_ticker(df: pd.DataFrame, ticker: str, mode: str, market_bullish: Optional[bool] = None) -> Dict[str, Any]:
    # 1. VALIDASI DATA & LIKUIDITAS
    df = df.dropna().copy()
    if len(df) < MIN_BARS:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Data kurang"}

    df["Tx_Value"] = df["Volume"] * df["Close"]
    avg_tx = df["Tx_Value"].rolling(window=20).mean().iloc[-1]
    if avg_tx < MIN_TX_VALUE:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Likuiditas Rendah"}

    # 2. KALKULASI INDIKATOR
    closes = df["Close"].tolist()
    highs, lows, opens = df["High"].tolist(), df["Low"].tolist(), df["Open"].tolist()
    current_p = closes[-1]
    
    try:
        e20 = ema(closes, 20)[-1]
        e50 = ema(closes, 50)[-1]
        vol_now = df["Volume"].iloc[-1]
        vol_avg = vol_sma(df["Volume"].tolist(), 20)[-1]
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 0
        curr_rsi = rsi(closes, 14)[-1]
        curr_atr = atr(highs, lows, closes, 14)[-1]
        
        # Structure Check: Apakah harga di atas High 10 hari lalu?
        high_10 = max(highs[-11:-1]) 
        is_breakout = current_p > high_10
    except:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Error Indikator"}

    # 3. SCORING SYSTEM (Total 100)
    score = 0
    details = []

    # A. TREND (30 pts)
    if current_p > e20 > e50:
        score += 30
        details.append("Perfect Uptrend")
    elif current_p > e20:
        score += 15
        details.append("Short-term Uptrend")

    # B. STRUCTURE (20 pts)
    if is_breakout:
        score += 20
        details.append("New 10-Day High")
    elif current_p > opens[-1]: # Close > Open (Bullish Candle)
        score += 10
        details.append("Bullish Day")

    # C. VOLUME (20 pts)
    if vol_ratio >= 1.5:
        score += 20
        details.append(f"Volume Spike ({vol_ratio:.1f}x)")
    elif vol_ratio >= 1.2:
        score += 10
        details.append(f"Volume Confirmation ({vol_ratio:.1f}x)")

    # D. MOMENTUM (15 pts)
    if 50 <= curr_rsi <= 75:
        score += 15
        details.append("Healthy Momentum")
    elif curr_rsi > 75:
        score += 5
        details.append("Overbought Caution")

    # E. VOLATILITY/RISK (15 pts)
    # Skor jika jarak ke EMA 20 tidak terlalu jauh (tidak overextended)
    dist_ema20 = (current_p - e20) / e20
    if 0 <= dist_ema20 <= 0.03:
        score += 15
        details.append("Safe Entry Zone")
    elif dist_ema20 <= 0.06:
        score += 7
        details.append("Moderate Entry Zone")

    # 4. PENENTUAN SINYAL
    action = "DONT BUY"
    if score >= 80: action = "STRONG BUY"
    elif score >= 65: action = "BUY"

    # Kalkulasi SL & TP (1.5x ATR Risk)
    sl = current_p - (curr_atr * 1.5)
    risk = current_p - sl
    tp = current_p + (risk * 2) # Risk Reward 1:2

    return {
        "ticker": ticker,
        "mode": mode,
        "action": action,
        "score": score,
        "entry": round(current_p, 0),
        "sl": round(sl, 0),
        "tp": round(tp, 0),
        "reason": " | ".join(details) if details else "Kriteria tidak terpenuhi"
    }