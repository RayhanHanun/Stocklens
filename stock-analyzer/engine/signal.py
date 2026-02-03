from typing import Any, Dict, List, Optional
import pandas as pd

# Import Indikator
from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import sma as vol_sma
from engine.indicators.rsi import rsi  # File baru yang kita buat
from engine.structure import classify_structure

MIN_BARS = 60

def _build_signal(
    ticker: str,
    mode: str,
    setup_type: str,
    entry: float,
    stop: float,
    target: float,
    risk_reward: float,
    confidence: int,
    details: str
) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "mode": mode,         # SWING atau SCALPING
        "setup": setup_type,  # PULLBACK atau BREAKOUT
        "action": "BUY",      # Fokus Long Only untuk saham
        "entry_price": round(entry, 0),
        "stop_loss": round(stop, 0),
        "target_price": round(target, 0),
        "risk_reward": round(risk_reward, 2),
        "confidence_score": confidence,
        "reasoning": details,
    }

def analyze_ticker(df: pd.DataFrame, ticker: str) -> List[Dict[str, Any]]:
    # 1. Data Validation
    df = df.dropna()
    if len(df) < MIN_BARS:
        return []

    # 2. Extract Data Series
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    volumes = df["Volume"].tolist()
    
    current_price = closes[-1]
    
    # 3. Calculate Indicators
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200) # Long term trend
    atr14 = atr(highs, lows, closes, 14)
    rsi14 = rsi(closes, 14)
    vol_avg = vol_sma(volumes, 20)

    # Ambil nilai terakhir (Latest Values)
    curr_ema20 = ema20[-1]
    curr_ema50 = ema50[-1]
    curr_ema200 = ema200[-1] if ema200[-1] else 0
    curr_atr = atr14[-1]
    curr_rsi = rsi14[-1]
    curr_vol = volumes[-1]
    curr_vol_avg = vol_avg[-1]

    if not (curr_ema20 and curr_ema50 and curr_atr and curr_rsi and curr_vol_avg):
        return []

    signals: List[Dict[str, Any]] = []

    # ============================================================
    # STRATEGI 1: SWING TRADING (The Trend Follower)
    # Filosofi: "Buy the Dip" di saham Uptrend.
    # ============================================================
    
    # Syarat 1: Trend Wajib Bullish (Harga > EMA 50)
    is_uptrend = current_price > curr_ema50
    
    # Syarat 2: RSI "Sehat" (Tidak Overbought > 70, Tidak Oversold < 30 yang menandakan crash)
    is_rsi_healthy = 40 <= curr_rsi <= 70
    
    # Syarat 3: Pullback Logic (Harga dekat dengan EMA 20)
    # Kita anggap "dekat" jika harga tidak lebih dari 3% di atas EMA 20
    dist_to_ema20 = (current_price - curr_ema20) / curr_ema20
    is_pullback = -0.02 <= dist_to_ema20 <= 0.03

    if is_uptrend and is_rsi_healthy and is_pullback:
        # Rencana Trade Swing
        stop_loss = curr_ema50 # Stoploss di bawah trend menengah (EMA 50)
        risk = current_price - stop_loss
        
        # Filter Risk: Jika stoploss terlalu dekat (<2%), gunakan ATR
        if risk < (current_price * 0.02):
            stop_loss = current_price - (curr_atr * 2)
            risk = current_price - stop_loss
            
        target_price = current_price + (risk * 2.5) # RR 1:2.5
        rr_ratio = (target_price - current_price) / risk
        
        # Confidence Score Calculation
        score = 60
        if current_price > curr_ema200: score += 10 # Di atas MA200 (Super Bullish)
        if curr_vol > curr_vol_avg: score += 10     # Volume confirm
        if 50 <= curr_rsi <= 60: score += 10        # Sweet spot momentum
        
        if rr_ratio >= 2.0:
            signals.append(_build_signal(
                ticker, "SWING", "PULLBACK_EMA20",
                current_price, stop_loss, target_price, rr_ratio, score,
                f"Trend Bullish (Above EMA50), Pullback near EMA20 ({dist_to_ema20*100:.1f}%), RSI {curr_rsi:.1f}"
            ))

    # ============================================================
    # STRATEGI 2: SCALPING / DAY TRADE (The Momentum Hunter)
    # Filosofi: "Follow the Explosion" untuk trading besok pagi.
    # ============================================================
    
    # Syarat 1: Volume Spike (Minimal 1.5x rata-rata)
    is_vol_spike = curr_vol >= (curr_vol_avg * 1.5)
    
    # Syarat 2: Strong Candle (Close di 25% area teratas High-Low)
    daily_range = highs[-1] - lows[-1]
    if daily_range > 0:
        close_position = (current_price - lows[-1]) / daily_range
        is_strong_close = close_position >= 0.75
    else:
        is_strong_close = False
        
    # Syarat 3: Trend Momentum (Harga > EMA 20)
    is_momentum = current_price > curr_ema20
    
    if is_vol_spike and is_strong_close and is_momentum:
        # Rencana Trade Scalping (Untuk Besok)
        # Entry: Buy Stop di atas High hari ini (Breakout)
        entry_price = highs[-1] + (curr_atr * 0.1) # Buffer sedikit di atas High
        
        # Stoploss: Di bawah Low hari ini atau separuh candle body
        stop_loss = lows[-1]
        risk = entry_price - stop_loss
        
        # Target: Pendek saja (1:1.5 atau 1:2 karena scalping)
        target_price = entry_price + (risk * 2.0)
        rr_ratio = (target_price - entry_price) / risk if risk > 0 else 0
        
        # Confidence Score
        score = 70
        if curr_vol >= (curr_vol_avg * 2.5): score += 15 # Super Volume
        if curr_rsi > 60: score += 10                    # Strong Momentum
        
        if rr_ratio >= 1.5:
             signals.append(_build_signal(
                ticker, "SCALPING", "MOMENTUM_BREAKOUT",
                entry_price, stop_loss, target_price, rr_ratio, score,
                f"Volume Spike {curr_vol/curr_vol_avg:.1f}x, Strong Close, RSI {curr_rsi:.1f}"
            ))
            
    return signals