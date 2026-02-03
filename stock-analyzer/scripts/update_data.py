import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


import io
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

from config.tickers import TICKERS

# --------------------------------------------------
# Configuration
# --------------------------------------------------
IDX_DAILY_CSV_URL_TEMPLATE = (
    "https://www.idx.co.id/umbraco/Surface/DownloadData/DownloadTradingSummary"
    "?date={date}&type=csv"
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "idx"

REQUEST_HEADERS = {
    "User-Agent": "Stocklens/1.0 (personal EOD use)",
    "Accept": "text/csv,application/csv,text/plain,*/*",
}

REQUEST_TIMEOUT = 20
LOOKBACK_DAYS = 400


# --------------------------------------------------
# Utilities
# --------------------------------------------------
def log(msg: str) -> None:
    print(msg)


def _normalize_column(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def _pick_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    norm = {_normalize_column(c): c for c in columns}
    for c in candidates:
        key = _normalize_column(c)
        if key in norm:
            return norm[key]
    return None


def _date_range(start: date, end: date) -> List[date]:
    dates = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # skip weekend
            dates.append(d)
        d += timedelta(days=1)
    return dates


# --------------------------------------------------
# IDX CSV Handling
# --------------------------------------------------
def _download_daily_csv(d: date) -> Optional[pd.DataFrame]:
    url = IDX_DAILY_CSV_URL_TEMPLATE.format(date=d.strftime("%Y%m%d"))
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None
        text = r.text.strip()
        if not text or text.startswith("<"):
            return None
        return pd.read_csv(io.StringIO(text))
    except Exception:
        return None


def _extract_ohlcv(df: pd.DataFrame, ticker: str) -> Optional[Dict[str, float]]:
    cols = df.columns.tolist()

    code = _pick_column(cols, ["code", "stockcode", "symbol", "ticker"])
    op = _pick_column(cols, ["open"])
    hi = _pick_column(cols, ["high"])
    lo = _pick_column(cols, ["low"])
    cl = _pick_column(cols, ["close", "last"])
    vol = _pick_column(cols, ["volume", "vol", "shares"])

    if not all([code, op, hi, lo, cl, vol]):
        return None

    row = df[df[code].astype(str).str.upper() == ticker.upper()]
    if row.empty:
        return None

    r = row.iloc[0]
    try:
        return {
            "Open": float(r[op]),
            "High": float(r[hi]),
            "Low": float(r[lo]),
            "Close": float(r[cl]),
            "Volume": float(r[vol]),
        }
    except Exception:
        return None


# --------------------------------------------------
# CSV Persistence
# --------------------------------------------------
def _load_existing(ticker: str) -> pd.DataFrame:
    path = DATA_DIR / f"{ticker}.csv"
    if not path.exists():
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])


def _save_csv(ticker: str, df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / f"{ticker}.csv", index=False)


# --------------------------------------------------
# Core Logic
# --------------------------------------------------
def update_ticker(ticker: str) -> None:
    existing = _load_existing(ticker)
    existing_dates = set(existing["Date"].astype(str)) if not existing.empty else set()

    if not existing.empty:
        last_date = pd.to_datetime(existing["Date"]).max().date()
        start = last_date + timedelta(days=1)
    else:
        start = date.today() - timedelta(days=LOOKBACK_DAYS)

    rows: List[Dict[str, object]] = []

    for d in _date_range(start, date.today()):
        iso = d.isoformat()
        if iso in existing_dates:
            continue

        df_daily = _download_daily_csv(d)
        if df_daily is None:
            continue

        ohlcv = _extract_ohlcv(df_daily, ticker)
        if ohlcv is None:
            continue

        rows.append({"Date": iso, **ohlcv})
        log(f"[{ticker}] updated {iso}")

    if rows:
        new_df = pd.DataFrame(rows)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates("Date").sort_values("Date")
        _save_csv(ticker, combined)
        log(f"[{ticker}] saved {len(combined)} rows")


def main() -> None:
    log("=== UPDATE IDX DATA START ===")
    for t in TICKERS:
        try:
            update_ticker(t)
        except Exception as e:
            log(f"[{t}] error: {e}")
    log("=== UPDATE COMPLETE ===")


if __name__ == "__main__":
    main()
