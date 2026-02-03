import sys
import pandas as pd
import yfinance as yf
import datetime
from pathlib import Path

# Setup Project Root agar bisa import dari folder config
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

try:
    from config.tickers import TICKERS
except ImportError:
    print("[ERROR] File config/tickers.py tidak ditemukan. Pastikan file tersebut ada.")
    sys.exit(1)

# Konfigurasi Direktori
DATA_DIR = ROOT / "data" / "idx"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_data():
    print(f"=== STARTING RELIABLE YFINANCE DOWNLOAD ===")
    print(f"Target Directory: {DATA_DIR}")
    
    # Menentukan rentang tanggal secara eksplisit untuk menghindari YFTzMissingError
    # Kita ambil 5 tahun ke belakang untuk memastikan EMA 200 memiliki data yang cukup
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=1825) # 5 Tahun
    
    success_count = 0
    
    for ticker in TICKERS:
        symbol = f"{ticker}.JK"
        print(f"[{ticker}] Downloading {symbol} from {start_date.date()} to {end_date.date()}...")
        
        try:
            # Menggunakan parameter start/end lebih stabil daripada period="max"
            df = yf.download(
                symbol, 
                start=start_date, 
                end=end_date, 
                interval="1d", 
                progress=False,
                auto_adjust=True # Menyesuaikan harga Close dengan aksi korporasi
            )
            
            if df.empty:
                print(f"[{ticker}] WARNING: Data kosong atau simbol tidak ditemukan.")
                continue
            
            # Reset index agar kolom 'Date' menjadi kolom biasa
            df = df.reset_index()
            
            # Standardisasi Nama Kolom agar sesuai dengan engine/signal.py
            # Yahoo terkadang mengembalikan MultiIndex atau nama kolom huruf kecil
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
            
            # Pastikan kolom utama ada
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            df = df[required_cols]
            
            # Simpan ke CSV
            output_path = DATA_DIR / f"{ticker}.csv"
            df.to_csv(output_path, index=False)
            print(f"[{ticker}] SUCCESS: Saved {len(df)} rows.")
            success_count += 1
            
        except Exception as e:
            print(f"[{ticker}] FAILED: {str(e)}")

    print(f"\n=== DOWNLOAD COMPLETE ===")
    print(f"Successfully processed {success_count}/{len(TICKERS)} tickers.")

if __name__ == "__main__":
    download_data()