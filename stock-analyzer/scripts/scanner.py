import json
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# 1. Setup Project Root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from engine.signal import analyze_ticker, get_ihsg_trend
from config.tickers import TICKERS

def run_scanner():
    """
    Scanner V3: Menyimpan data Entry/SL/TP ke Watchlist untuk fitur Search yang lebih detail.
    """
    print(f"=== STOCKLENS PRIME SCANNER [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===")
    
    market_is_bullish = get_ihsg_trend()
    market_status = "BULLISH (Safe)" if market_is_bullish else "BEARISH (High Risk)"
    print(f"Market Sentiment: {market_status}")

    output_data = {
        "metadata": {
            "last_run": datetime.now().isoformat(),
            "market_sentiment": market_status,
            "total_tickers_scanned": len(TICKERS)
        },
        "signals": { "swing": [], "scalping": [] },
        "watchlist": [] 
    }

    data_dir = ROOT / "data" / "idx"

    for ticker in TICKERS:
        file_path = data_dir / f"{ticker}.csv"
        if not os.path.exists(file_path): continue
            
        try:
            df = pd.read_csv(file_path)
            
            # --- ANALISA ---
            res_swing = analyze_ticker(df, ticker, "SWING", market_bullish=market_is_bullish)
            res_scalp = analyze_ticker(df, ticker, "SCALPING", market_bullish=market_is_bullish)
            
            # --- FILL SIGNALS TABLE (Hanya Valid Buy) ---
            if res_swing['action'] in ["BUY", "STRONG BUY"]: 
                output_data['signals']['swing'].append(res_swing)
            
            if res_scalp['action'] in ["BUY", "STRONG BUY"]:
                output_data['signals']['scalping'].append(res_scalp)
                
            # --- FILL WATCHLIST (Untuk Search - LEBIH LENGKAP) ---
            output_data['watchlist'].append({
                "ticker": ticker,
                # Data Swing
                "swing_status": res_swing['action'],
                "swing_score": res_swing.get('score', 0),
                "swing_reason": res_swing['reason'],
                "swing_entry": res_swing.get('entry', 0), # Baru
                "swing_sl": res_swing.get('sl', 0),       # Baru
                "swing_tp": res_swing.get('tp', 0),       # Baru
                # Data Scalping
                "scalp_status": res_scalp['action'],
                "scalp_score": res_scalp.get('score', 0),
                "scalp_reason": res_scalp['reason'],
                "scalp_entry": res_scalp.get('entry', 0), # Baru
                "scalp_sl": res_scalp.get('sl', 0),       # Baru
                "scalp_tp": res_scalp.get('tp', 0)        # Baru
            })
            
            if res_swing.get('score', 0) >= 60:
                print(f"   🚀 {ticker}: Scanned (Score: {res_swing.get('score', 0)})")

        except Exception as e:
            print(f"   ❌ {ticker}: Error {str(e)}")

    output_path = ROOT / "output" / "signals.json"
    os.makedirs(ROOT / "output", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=4)

    print(f"\n=== SCAN SELESAI ===")
    print(f"Sinyal SWING    : {len(output_data['signals']['swing'])}")
    print(f"Sinyal SCALPING : {len(output_data['signals']['scalping'])}")

if __name__ == "__main__":
    run_scanner()