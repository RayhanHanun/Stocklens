import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.tickers import TICKERS
from engine.signal import analyze_ticker

# --------------------------------------------------
# Project root setup (optional if needed)
# --------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

DATA_DIR = ROOT / "data" / "idx"
OUTPUT_PATH = ROOT / "output" / "signals.json"


# --------------------------------------------------
# Load CSV function
# --------------------------------------------------
def load_csv(ticker: str) -> pd.DataFrame:
    """
    Load OHLCV data from local CSV saved by download_csv_yahoo.py.
    """
    path = DATA_DIR / f"{ticker}.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
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
                "reason": "No data",
            })
            continue

        # Run engine analysis
        signals = analyze_ticker(df, ticker)

        if not signals:
            results.append({
                "ticker": ticker,
                "status": "NO_TRADE",
                "reason": "No valid setup",
            })
        else:
            results.extend(signals)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "market": "IDX / Local CSV",
        "data_source": "local-csv",
        "results": results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))

    trade_count = sum(1 for r in results if r.get("mode"))
    print(f"Signals generated: {trade_count}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
