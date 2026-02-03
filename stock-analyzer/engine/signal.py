from typing import Any, Dict, List, Optional
import pandas as pd

# Import Indikator dari folder engine/indicators
from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import sma as vol_sma
from engine.indicators.rsi import rsi  # Pastikan file rsi.py sudah dibuat
from engine.structure import classify_structure

# KONFIGURASI PROFESIONAL
MIN_BARS = 60
MIN_TRANSACTION_VALUE = 5_000_000_000  # Minimal transaksi harian Rp 5 Miliar (Filter Likuiditas)

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
    """
    Helper function untuk memformat output sinyal standar.
    """
    return {
        "ticker": ticker,
        "mode": mode,         # SWING atau SCALPING
        "setup": setup_type,  # PULLBACK atau MOMENTUM
        "action": "BUY",      # Fokus Long Only
        "entry_price": round(entry, 0),
        "stop_loss": round(stop, 0),
        "target_price": round(target, 0),
        "risk_reward": round(risk_reward, 2),
        "confidence_score": confidence,
        "reasoning": details,
    }

def analyze_ticker(df: pd.DataFrame, ticker: str) -> List[Dict[str, Any]]:
    # -----------------------------------------------------------
    # 1. DATA VALIDATION & CLEANING
    # -----------------------------------------------------------
    df = df.dropna()
    if len(df) < MIN_BARS:
        return []

    # -----------------------------------------------------------
    # 2. LIQUIDITY FILTER (THE GATEKEEPER)
    # -----------------------------------------------------------
    # Hitung rata-rata nilai transaksi 20 hari terakhir
    # Rumus: (Volume * Close Price)
    df["Tx_Value"] = df["Volume"] * df["Close"]
    avg_tx_value = df["Tx_Value"].rolling(window=20).mean().iloc[-1]

    # Reject saham tidak likuid (di bawah 5 Miliar/hari) untuk keamanan swing
    if avg_tx_value < MIN_TRANSACTION_VALUE:
        return [] 

    # -----------------------------------------------------------
    # 3. INDICATOR CALCULATION (THE ENGINE)
    # -----------------------------------------------------------
    # Extract Series
    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()
    volumes = df["Volume"].tolist()
    opens = df["Open"].tolist()
    
    current_price = closes[-1]
    
    # Calculate Tech Indicators
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200) # Tren Jangka Panjang
    atr14 = atr(highs, lows, closes, 14)
    rsi14 = rsi(closes, 14)
    vol_avg = vol_sma(volumes, 20)

    # Ambil Nilai Terakhir (Latest Values)
    curr_ema20 = ema20[-1]
    curr_ema50 = ema50[-1]
    curr_ema200 = ema200[-1] if ema200[-1] else 0
    curr_atr = atr14[-1]
    curr_rsi = rsi14[-1]
    curr_vol = volumes[-1]
    curr_vol_avg = vol_avg[-1]
    curr_open = opens[-1]

    # Pastikan indikator valid (tidak None)
    if not (curr_ema20 and curr_ema50 and curr_atr and curr_rsi and curr_vol_avg):
        return []

    signals: List[Dict[str, Any]] = []

    # -----------------------------------------------------------
    # 4. MARKET CONDITION CHECKS
    # -----------------------------------------------------------
    # Tren Dasar
    is_uptrend_mid = current_price > curr_ema50
    is_uptrend_long = current_price > curr_ema200 if curr_ema200 else False
    
    # Price Action Hari Ini
    is_green_day = current_price >= curr_open
    daily_spread = highs[-1] - lows[-1]
    
    # Rejection Detection (Ekor Bawah Panjang)
    # Ekor bawah = Min(Open, Close) - Low
    lower_shadow = min(curr_open, current_price) - lows[-1]
    body_size = abs(current_price - curr_open)
    # Valid Rejection jika ekor bawah > body candle (Hammer-like pattern)
    is_rejection = lower_shadow > body_size

    # ============================================================
    # STRATEGI 1: SWING TRADING (The Trend Follower)
    # Logic: Buy on Support (Pullback) in Uptrend
    # ============================================================
    
    # A. Filter RSI: Swing butuh ruang gerak (40-65). 
    # Jika > 70 sudah terlalu mahal (Overbought).
    is_rsi_swing_valid = 40 <= curr_rsi <= 65
    
    # B. Filter Pullback: Harga harus "diskon" dekat EMA 20
    # Jarak toleransi: -2% sampai +3% dari EMA 20
    dist_ema20_pct = (current_price - curr_ema20) / curr_ema20
    is_near_ema20 = -0.02 <= dist_ema20_pct <= 0.03

    if is_uptrend_mid and is_rsi_swing_valid and is_near_ema20:
        # Konfirmasi Entry: Harus ada pantulan (Rejection) ATAU Candle Hijau
        # Kita tidak menangkap pisau jatuh (Red candle besar di support itu bahaya)
        if is_rejection or is_green_day:
            
            # --- RISK MANAGEMENT ---
            # Stoploss Swing: Idealnya di bawah EMA 50 (Support Kuat)
            swing_sl = curr_ema50
            
            # Safety check: Jika EMA 50 terlalu dekat (<2%) atau terlalu jauh (>10%),
            # gunakan ATR Trailing Stop (2x ATR)
            risk_pct = (current_price - swing_sl) / current_price
            if risk_pct < 0.02 or risk_pct > 0.10:
                swing_sl = current_price - (curr_atr * 2.0)
            
            # Target Profit: Rasio 1:2.5 (Minimal)
            risk = current_price - swing_sl
            target = current_price + (risk * 2.5)
            rr = (target - current_price) / risk
            
            # Scoring
            score = 60
            if is_uptrend_long: score += 15     # Di atas MA200 = Strong Bull
            if is_rejection: score += 10        # Pola Hammer = Strong Reversal
            if curr_vol > curr_vol_avg: score += 10
            
            # Final Gate: RR harus masuk akal
            if rr >= 2.0:
                signals.append(_build_signal(
                    ticker, "SWING", "PULLBACK_EMA20",
                    current_price, swing_sl, target, rr, score,
                    f"Trend Uptrend, Pullback EMA20 ({dist_ema20_pct*100:.1f}%), RSI {curr_rsi:.1f}, Rejection: {is_rejection}"
                ))

    # ============================================================
    # STRATEGI 2: SCALPING / DAY TRADE (The Momentum Hunter)
    # Logic: Buy High, Sell Higher (Breakout & Volume Spike)
    # ============================================================
    
    # A. Volume Explosion: Minimal 1.5x rata-rata
    vol_ratio = curr_vol / curr_vol_avg
    is_vol_spike = vol_ratio >= 1.5
    
    # B. Strong Close (Candle Kekuatan)
    # Harga ditutup di 25% area teratas (High - Low)
    if daily_spread > 0:
        close_pos = (current_price - lows[-1]) / daily_spread
        is_strong_close = close_pos >= 0.75
    else:
        is_strong_close = False

    # C. Accumulation Check (VPA Logic)
    # Volume tinggi HANYA valid jika harga naik (Green Day)
    is_accumulation = is_vol_spike and is_green_day

    # D. Momentum Check: Harga harus di atas EMA 20
    is_momentum = current_price > curr_ema20

    if is_accumulation and is_strong_close and is_momentum:
        # --- EXECUTION PLAN (FOR NEXT DAY) ---
        # Entry: Buy Stop di atas High hari ini (Breakout Confirmation)
        # Kita beri buffer 0.2 x ATR agar tidak kena false break
        entry_price = highs[-1] + (curr_atr * 0.2)
        
        # Stoploss Scalping: Di Low hari ini (Support terdekat)
        scalp_sl = lows[-1]
        
        # Cek Risk jangan terlalu tipis
        if (entry_price - scalp_sl) / entry_price < 0.01:
             scalp_sl = entry_price * 0.98 # Min risk 2%
             
        risk = entry_price - scalp_sl
        
        # Target: Scalping targetnya lebih pendek (RR 1:2)
        target = entry_price + (risk * 2.0)
        rr = (target - entry_price) / risk if risk > 0 else 0
        
        # Scoring
        score = 70
        if vol_ratio > 2.5: score += 15         # Volume Ledakan Besar
        if curr_rsi > 60: score += 10           # Momentum RSI Kuat
        
        if rr >= 1.5:
             signals.append(_build_signal(
                ticker, "SCALPING", "MOMENTUM_BREAKOUT",
                entry_price, scalp_sl, target, rr, score,
                f"Volume Spike {vol_ratio:.1f}x, Strong Close, RSI {curr_rsi:.1f}, Accumulation Valid"
            ))
            
    return signals