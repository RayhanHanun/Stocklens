import sys
from pathlib import Path

# --- WAJIB DI ATAS: Setup agar Python mengenali folder 'config' dan 'engine' ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import json
from datetime import datetime
import pandas as pd

# Sekarang import ini akan berhasil karena ROOT sudah masuk ke sys.path
from config.tickers import TICKERS
from engine.signal import analyze_ticker

# --------------------------------------------------
# Load CSV function
# --------------------------------------------------
def load_csv(ticker: str) -> pd.DataFrame:
    """
    Load OHLCV data from local CSV saved by download_yfinance.py.
    """
    path = ROOT / "data" / "idx" / f"{ticker}.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
        # Menangani standardisasi kolom dari yfinance
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()

# --------------------------------------------------
# Main execution
# --------------------------------------------------
def main() -> None:
    results = []
    print("=== RUN DAILY ANALYSIS (LOCAL CSV IDX) ===")

    for ticker in TICKERS:
        df = load_csv(ticker)

        if df.empty:
            results.append({
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "No data found in CSV",
            })
            continue

        # Jalankan engine analisis profesional
        signals = analyze_ticker(df, ticker)

        if not signals:
            results.append({
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "No valid professional setup found",
            })
        else:
            results.extend(signals)

    # Simpan hasil ke output/signals.json
    output_path = ROOT / "output" / "signals.json"
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "market": "IDX / IHSG",
        "data_source": "yfinance-csv",
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))

    trade_count = sum(1 for r in results if r.get("mode"))
    print(f"Signals generated: {trade_count}")
    print(f"Full report saved to: {output_path}")

if __name__ == "__main__":
    main()