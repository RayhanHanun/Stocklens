# Stock Analyzer (Personal EOD)

Personal, end-of-day stock analysis engine for a single user. This is not a trading bot and does not execute trades.

## How to run

1. Create a Python 3.10+ environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run the daily script after market close:
   - `python scripts/run_daily.py`

Results are written to [output/signals.json](output/signals.json).

## What it does

- Fetches daily OHLCV data from Yahoo Finance (via `yfinance`).
- Detects basic market structure (HH/HL) and classifies trend as bullish, bearish, or range.
- Uses EMA(20) and EMA(50) for trend bias only.
- Uses ATR(14) for volatility filtering and stop placement.
- Requires volume confirmation (volume >= 20-day volume SMA).
- Produces swing trade setups and next-day day-trade plans.
- Outputs trade plans only (no execution commands).

## Assumptions

- Swing points are detected with a simple pivot method using the last 20 bars.
- Trend bias must align with structure; otherwise signals are rejected.
- Volatility filter rejects very low or very high ATR% (default: 0.5%–15%).
- Stops use the closer of structure-based or 1.5x ATR distance.
- A small fixed ticker list is used for the example run.

## Limitations

- Daily data only; no intraday or realtime data.
- No machine learning or prediction models.
- No broker integration or automated trading.
- No database; output is a JSON file.
- Simplified market structure detection; not optimized for all market conditions.

## Notes

This project is intended for personal use only and should be run once per day after the market close.
