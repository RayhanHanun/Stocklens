from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf

# Import Indikator
from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import sma as vol_sma
from engine.indicators.rsi import rsi

# KONFIGURASI GLOBAL
MIN_BARS = 100
MIN_TX_VALUE = 2_000_000_000 # 2 Miliar

def get_ihsg_trend() -> bool:
    try:
        df_ihsg = yf.download("^JKSE", period="1y", interval="1d", progress=False)
        if df_ihsg.empty: return True
        closes = df_ihsg['Close'].tolist()
        if len(closes) > 200:
            return closes[-1] > ema(closes, 200)[-1]
        return True
    except:
        return True

def analyze_ticker(df: pd.DataFrame, ticker: str, mode: str, market_bullish: Optional[bool] = None) -> Dict[str, Any]:
    # 1. VALIDASI DATA
    df = df.dropna().copy()
    if len(df) < MIN_BARS:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Data kurang"}

    df["Tx_Value"] = df["Volume"] * df["Close"]
    avg_tx = df["Tx_Value"].rolling(window=20).mean().iloc[-1]
    if avg_tx < MIN_TX_VALUE:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Likuiditas Rendah"}

    # 2. HITUNG INDIKATOR
    closes = df["Close"].tolist()
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    opens = df["Open"].tolist()
    current_p = closes[-1]
    
    try:
        e20 = ema(closes, 20)[-1]
        e50 = ema(closes, 50)[-1]
        vol_now = df["Volume"].iloc[-1]
        vol_avg = vol_sma(df["Volume"].tolist(), 20)[-1]
        vol_ratio = vol_now / vol_avg if vol_avg > 0 else 0
        curr_rsi = rsi(closes, 14)[-1]
        curr_atr = atr(highs, lows, closes, 14)[-1]
        
        # Structure Check
        high_10 = max(highs[-11:-1])
        is_breakout = current_p > high_10
    except:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Error Indikator"}

    # 3. LOGIKA TERPISAH (BRANCHING)
    score = 0
    details = []
    sl = 0
    tp = 0
    
    # =========================================================
    # MODE A: SWING (Trend Following - Santai)
    # =========================================================
    if mode.upper() == "SWING":
        # A1. Trend Score (Max 40)
        # Swing wajib uptrend kuat
        if current_p > e20 > e50: 
            score += 40
            details.append("Perfect Uptrend")
        elif current_p > e50: 
            score += 20
            details.append("Moderate Uptrend")
            
        # A2. Volume (Max 30)
        # Swing butuh volume stabil/konfirmasi
        if vol_ratio >= 1.2: 
            score += 30
            details.append(f"Vol Confirmed ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.0:
            score += 15
            
        # A3. Momentum/RSI (Max 30)
        # Swing suka RSI yang 'sehat' (45-65), bukan yang terlalu panas
        if 45 <= curr_rsi <= 68: 
            score += 30
            details.append("Healthy RSI")
        elif curr_rsi > 68:
            score += 10 # Sedikit overbought
            
        # Perhitungan Target Swing (Risk Reward 1:2.5)
        # Stoploss lebih longgar (2x ATR) agar tidak mudah kena gocek
        sl = current_p - (curr_atr * 2.0)
        risk = current_p - sl
        tp = current_p + (risk * 2.5)

    # =========================================================
    # MODE B: SCALPING (Momentum - Agresif)
    # =========================================================
    elif mode.upper() == "SCALPING":
        # B1. Momentum Score (Max 40)
        # Scalping suka RSI panas (>60) tanda saham sedang 'lari'
        if curr_rsi >= 60: 
            score += 40
            details.append("Strong Momentum")
        elif curr_rsi >= 50:
            score += 20
            
        # B2. Volume Spike (Max 40) - WAJIB
        # Scalping butuh ledakan volume tiba-tiba
        if vol_ratio >= 1.8: 
            score += 40
            details.append(f"Vol Spike ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.3:
            score += 20
            details.append("Vol Rising")
            
        # B3. Price Action (Max 20)
        # Harga harus di atas EMA 20 (Short term strong)
        if current_p > e20:
            score += 20
            details.append("> EMA20")
            
        # Perhitungan Target Scalping (Risk Reward 1:1.5)
        # Stoploss ketat (1x ATR) untuk main cepat
        sl = current_p - (curr_atr * 1.0)
        risk = current_p - sl
        tp = current_p + (risk * 1.5)

    # 4. PENENTUAN STATUS
    action = "DONT BUY"
    if score >= 80: action = "STRONG BUY"
    elif score >= 60: action = "BUY" # Batas bawah sedikit diturunkan agar lebih sensitif

    return {
        "ticker": ticker,
        "mode": mode,
        "action": action,
        "score": score,
        "entry": round(current_p, 0),
        "sl": round(sl, 0),
        "tp": round(tp, 0),
        "reason": " | ".join(details) if details else "Low Signal Quality"
    }