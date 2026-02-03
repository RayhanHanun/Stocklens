import sys
import pandas as pd
import yfinance as yf
import datetime
import time # Diperlukan untuk jeda waktu
from pathlib import Path

# 1. Setup Project Root agar bisa import dari folder config
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

try:
    from config.tickers import TICKERS
except ImportError:
    print("[ERROR] File config/tickers.py tidak ditemukan. Pastikan file tersebut ada.")
    sys.exit(1)

# 2. Konfigurasi Direktori Penyimpanan
DATA_DIR = ROOT / "data" / "idx"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_data():
    print(f"=== STARTING RELIABLE YFINANCE DOWNLOAD ===")
    print(f"Target Directory: {DATA_DIR}")
    print(f"Total Tickers to Process: {len(TICKERS)}")
    
    # 3. Setup Rentang Waktu (5 Tahun untuk stabilitas EMA 200)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=1825) 
    
    success_count = 0
    
    for index, ticker in enumerate(TICKERS, 1):
        symbol = f"{ticker}.JK"
        print(f"[{index}/{len(TICKERS)}] Downloading {symbol}...")
        
        try:
            # Download data dengan auto_adjust agar harga Close akurat (Stock Split/Dividen)
            df = yf.download(
                symbol, 
                start=start_date, 
                end=end_date, 
                interval="1d", 
                progress=False,
                auto_adjust=True 
            )
            
            if df.empty:
                print(f"   ⚠️ WARNING: Data {ticker} kosong.")
            else:
                # Reset index agar Date menjadi kolom
                df = df.reset_index()
                
                # Menangani MultiIndex pada header (antisipasi update yfinance terbaru)
                df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
                
                # Standardisasi kolom yang dibutuhkan engine
                required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                df = df[required_cols]
                
                # Simpan ke CSV
                output_path = DATA_DIR / f"{ticker}.csv"
                df.to_csv(output_path, index=False)
                
                print(f"   ✅ SUCCESS: Saved {len(df)} rows.")
                success_count += 1
            
            # --- JEDA WAKTU (TIME SLEEP) ---
            # Menghindari error "Too Many Requests" (429) dari Yahoo Finance
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"   ❌ FAILED {ticker}: {str(e)}")
            time.sleep(1) # Jeda lebih lama jika terjadi error koneksi

    print(f"\n=== DOWNLOAD COMPLETE ===")
    print(f"Successfully processed {success_count}/{len(TICKERS)} tickers.")

if __name__ == "__main__":
    download_data()