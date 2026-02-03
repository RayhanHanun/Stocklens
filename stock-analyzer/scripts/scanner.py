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
    Memindai ticker dengan Logic Terpisah:
    - Signals Table: Hanya BUY / STRONG BUY (Data harga pasti lengkap)
    - Watchlist Search: Semua status (Termasuk DONT BUY / Data harga kosong)
    """
    print(f"=== STOCKLENS PRIME SCANNER [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===")
    
    # 2. Cek Sentimen Market Global (IHSG)
    market_is_bullish = get_ihsg_trend()
    market_status = "BULLISH (Safe)" if market_is_bullish else "BEARISH (High Risk)"
    print(f"Market Sentiment: {market_status}")

    # Struktur data output
    output_data = {
        "metadata": {
            "last_run": datetime.now().isoformat(),
            "market_sentiment": market_status,
            "total_tickers_scanned": len(TICKERS)
        },
        "signals": {
            "swing": [],
            "scalping": []
        },
        "watchlist": [] 
    }

    data_dir = ROOT / "data" / "idx"

    # 3. Looping Pemindaian Saham
    for ticker in TICKERS:
        file_path = data_dir / f"{ticker}.csv"
        
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # --- Scan Mode SWING ---
            res_swing = analyze_ticker(df, ticker, "SWING", market_bullish=market_is_bullish)
            
            # FILTER KETAT: Hanya masukkan ke 'signals' jika statusnya benar-benar BUY
            # "DONT BUY" tidak akan lolos filter ini
            if res_swing['action'] in ["BUY", "STRONG BUY"]: 
                output_data['signals']['swing'].append(res_swing)
            
            # --- Scan Mode SCALPING ---
            res_scalp = analyze_ticker(df, ticker, "SCALPING", market_bullish=market_is_bullish)
            
            if res_scalp['action'] in ["BUY", "STRONG BUY"]:
                output_data['signals']['scalping'].append(res_scalp)
                
            # --- Watchlist (Untuk Fitur Search) ---
            # Simpan SEMUA status di sini, agar user bisa cari saham apa saja (termasuk yang DONT BUY)
            output_data['watchlist'].append({
                "ticker": ticker,
                "swing_status": res_swing['action'],
                "swing_score": res_swing.get('score', 0),
                "swing_reason": res_swing['reason'],
                "scalp_status": res_scalp['action'],
                "scalp_score": res_scalp.get('score', 0),
                "scalp_reason": res_scalp['reason']
            })
            
            # Log progress hanya jika ada potensi sinyal (skor > 60)
            if res_swing.get('score', 0) >= 60:
                print(f"   🚀 {ticker}: Signal Candidate (Score: {res_swing.get('score', 0)})")

        except Exception as e:
            print(f"   ❌ {ticker}: Gagal memproses. Error: {str(e)}")

    # 4. Simpan ke File JSON
    output_path = ROOT / "output" / "signals.json"
    os.makedirs(ROOT / "output", exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=4)

    print(f"\n=== SCAN SELESAI ===")
    print(f"Sinyal SWING (Valid)    : {len(output_data['signals']['swing'])}")
    print(f"Sinyal SCALPING (Valid) : {len(output_data['signals']['scalping'])}")
    print(f"Data disimpan di        : {output_path}")

if __name__ == "__main__":
    run_scanner()