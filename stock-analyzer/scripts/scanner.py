import json
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# 1. Setup Project Root agar bisa import engine dan config
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from engine.signal import analyze_ticker, get_ihsg_trend
from config.tickers import TICKERS

def run_scanner():
    """
    Memindai semua ticker untuk mencari sinyal harian dan menyimpan hasilnya ke JSON.
    """
    print(f"=== STOCKLENS DAILY SCANNER [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===")
    
    # 2. Cek Sentimen Market Global (IHSG)
    # Ini dilakukan sekali saja agar efisien
    market_is_bullish = get_ihsg_trend()
    market_status = "BULLISH (Safe)" if market_is_bullish else "BEARISH (High Risk)"
    print(f"Market Sentiment: {market_status}")

    # Struktur data untuk file JSON
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
        "watchlist": [] # Untuk hasil pencarian status 'DONT BUY'
    }

    data_dir = ROOT / "data" / "idx"

    # 3. Looping Pemindaian Saham
    for ticker in TICKERS:
        file_path = data_dir / f"{ticker}.csv"
        
        if not os.path.exists(file_path):
            print(f"   ⚠️ {ticker}: Data CSV tidak ditemukan. Lewati.")
            continue
            
        try:
            df = pd.read_csv(file_path)
            
            # Scan Mode SWING
            res_swing = analyze_ticker(df, ticker, "SWING", market_bullish=market_is_bullish)
            if res_swing['action'] == "BUY":
                output_data['signals']['swing'].append(res_swing)
            
            # Scan Mode SCALPING
            res_scalp = analyze_ticker(df, ticker, "SCALPING", market_bullish=market_is_bullish)
            if res_scalp['action'] == "BUY":
                output_data['signals']['scalping'].append(res_scalp)
                
            # Simpan status terbaru ke watchlist (untuk fitur Search di web)
            output_data['watchlist'].append({
                "ticker": ticker,
                "swing_status": res_swing['action'],
                "swing_reason": res_swing['reason'],
                "scalp_status": res_scalp['action'],
                "scalp_reason": res_scalp['reason']
            })
            
            print(f"   ✅ {ticker}: Scan complete.")

        except Exception as e:
            print(f"   ❌ {ticker}: Gagal memproses. Error: {str(e)}")

    # 4. Simpan ke File JSON
    output_path = ROOT / "data" / "signals.json"
    os.makedirs(ROOT / "data", exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=4)

    print(f"\n=== SCAN SELESAI ===")
    print(f"Sinyal SWING ditemukan   : {len(output_data['signals']['swing'])}")
    print(f"Sinyal SCALPING ditemukan: {len(output_data['signals']['scalping'])}")
    print(f"Data disimpan di         : {output_path}")

if __name__ == "__main__":
    run_scanner()