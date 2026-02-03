from typing import Any, Dict, Optional
import pandas as pd
import yfinance as yf # Diperlukan untuk cek IHSG

# Import Indikator
from engine.indicators.atr import atr
from engine.indicators.ema import ema
from engine.indicators.volume import sma as vol_sma
from engine.indicators.rsi import rsi

# KONFIGURASI
MIN_BARS = 250
MIN_TX_VALUE = 7_000_000_000 

def get_ihsg_trend() -> bool:
    """
    Mengecek apakah IHSG sedang dalam kondisi Bullish (di atas EMA 200).
    """
    try:
        # Download data IHSG
        df_ihsg = yf.download("^JKSE", period="2y", interval="1d", progress=False)
        if df_ihsg.empty: return True # Default True jika gagal download agar tidak menghalangi sinyal
        
        closes = df_ihsg['Close'].tolist()
        curr_ihsg = closes[-1]
        ema200_ihsg = ema(closes, 200)[-1]
        
        # Market dianggap aman jika IHSG > EMA 200
        return curr_ihsg > ema200_ihsg
    except:
        return True

def analyze_ticker(df: pd.DataFrame, ticker: str, mode: str, market_bullish: Optional[bool] = None) -> Dict[str, Any]:
    """
    Engine dengan tambahan Filter Global Market (IHSG).
    """
    # 1. MARKET FILTER CHECK
    # Jika market_bullish tidak dikirim dari luar, kita cek sendiri (tapi ini bisa lambat jika di loop)
    # Saran: Cek IHSG sekali saja di level scripts/scanner.py lalu masukkan hasilnya ke sini.
    if market_bullish is False:
        return {
            "ticker": ticker, "mode": mode, "action": "DONT BUY", 
            "reason": "Market (IHSG) sedang Bearish. Risiko sistemik tinggi."
        }

    # 2. VALIDASI DATA & LIKUIDITAS
    df = df.dropna().copy()
    if len(df) < MIN_BARS:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Data kurang"}

    df["Tx_Value"] = df["Volume"] * df["Close"]
    avg_tx = df["Tx_Value"].rolling(window=20).mean().iloc[-1]
    if avg_tx < MIN_TX_VALUE:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Likuiditas Rendah"}

    # 3. KALKULASI INDIKATOR
    closes = df["Close"].tolist()
    highs, lows, opens = df["High"].tolist(), df["Low"].tolist(), df["Open"].tolist()
    current_p = closes[-1]
    curr_open = opens[-1]
    
    try:
        curr_ema20 = ema(closes, 20)[-1]
        curr_ema50 = ema(closes, 50)[-1]
        curr_ema200 = ema(closes, 200)[-1]
        curr_atr = atr(highs, lows, closes, 14)[-1]
        curr_rsi = rsi(closes, 14)[-1]
        curr_vol = df["Volume"].iloc[-1]
        curr_vol_avg = vol_sma(df["Volume"].tolist(), 20)[-1]
        vol_ratio = curr_vol / curr_vol_avg
    except:
        return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Error Indikator"}

    # ---------------------------------------------------------
    # 4. SWING LOGIC
    # ---------------------------------------------------------
    if mode.upper() == "SWING":
        is_uptrend = current_p > curr_ema50 > curr_ema200
        lower_shadow = min(curr_open, current_p) - lows[-1]
        body = abs(current_p - curr_open)
        is_rejection = lower_shadow > (body * 1.8) and (current_p >= curr_open)
        is_near_support = -0.01 <= (current_p - curr_ema20) / curr_ema20 <= 0.02
        is_vol_confirmed = vol_ratio >= 1.1

        if is_uptrend and is_rejection and is_near_support and (45 <= curr_rsi <= 68) and is_vol_confirmed:
            sl = current_p - (curr_atr * 2.2)
            tp = current_p + ((current_p - sl) * 2.5)
            return {
                "ticker": ticker, "mode": "SWING", "action": "BUY",
                "entry": round(current_p, 0), "sl": round(sl, 0), "tp": round(tp, 0),
                "reason": f"Uptrend + Hammer Rejection + Vol Confirmation ({vol_ratio:.1f}x)"
            }
        else:
            if not is_uptrend: reason = "Trend masih Bearish/Sideways (P < EMA50/200)"
            elif not is_vol_confirmed: reason = f"Pantulan tanpa volume (Vol hanya {vol_ratio:.1f}x)"
            else: reason = "Belum memenuhi kriteria teknikal Swing"
            return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": reason}

    # ---------------------------------------------------------
    # 5. SCALPING LOGIC
    # ---------------------------------------------------------
    elif mode.upper() == "SCALPING":
        is_momentum = curr_rsi >= 60 and current_p > curr_ema20
        is_vol_spike = vol_ratio >= 2.0
        daily_range = highs[-1] - lows[-1]
        close_pos = (current_p - lows[-1]) / daily_range if daily_range > 0 else 0
        is_strong_close = close_pos >= 0.85 

        if is_momentum and is_vol_spike and is_strong_close and (current_p > curr_open):
            entry_p = highs[-1] + (curr_atr * 0.1)
            sl = lows[-1]
            tp = entry_p + ((entry_p - sl) * 2.0)
            return {
                "ticker": ticker, "mode": "SCALPING", "action": "BUY",
                "entry": round(entry_p, 0), "sl": round(sl, 0), "tp": round(tp, 0),
                "reason": f"Momentum Breakout: Volume Spike ({vol_ratio:.1f}x)"
            }
        else:
            return {"ticker": ticker, "mode": "SCALPING", "action": "DONT BUY", "reason": "Kondisi Breakout tidak terpenuhi"}

    return {"ticker": ticker, "mode": mode, "action": "DONT BUY", "reason": "Mode tidak dikenal"}