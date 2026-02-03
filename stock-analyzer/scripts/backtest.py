import pandas as pd
import os
import sys
from pathlib import Path

# Setup Project Root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from engine.signal import analyze_ticker
from config.tickers import TICKERS

def run_backtest(mode="SWING"):
    """
    Menjalankan simulasi trading berdasarkan mode yang dipilih.
    """
    all_results = []
    data_dir = ROOT / "data" / "idx"
    
    print(f"=== STARTING BACKTEST: MODE {mode} ===")
    
    for ticker in TICKERS:
        file_path = data_dir / f"{ticker}.csv"
        if not os.path.exists(file_path):
            continue
            
        df = pd.read_csv(file_path)
        if len(df) < 250: continue

        # Simulasi berjalan dari hari ke-250 sampai hari terakhir
        for i in range(250, len(df)):
            current_data = df.iloc[:i+1].copy()
            
            # PANGGIL ENGINE (Sekarang mengirimkan argumen 'mode')
            signal = analyze_ticker(current_data, ticker, mode)

            # HANYA EKSEKUSI JIKA ACTION == "BUY"
            if signal.get("action") == "BUY":
                entry_p = signal['entry']
                sl = signal['sl']
                tp = signal['tp']
                
                # Cek hasil di masa depan (maksimal 60 hari ke depan)
                future_data = df.iloc[i+1:i+61]
                outcome = "PENDING"
                profit_loss = 0
                exit_date = None
                exit_price = 0

                for _, row in future_data.iterrows():
                    # Cek Stop Loss dulu (Prioritas Keamanan)
                    if row['Low'] <= sl:
                        outcome = "LOSS"
                        exit_price = sl
                        profit_loss = ((sl - entry_p) / entry_p) * 100
                        exit_date = row['Date']
                        break
                    # Cek Take Profit
                    elif row['High'] >= tp:
                        outcome = "WIN"
                        exit_price = tp
                        profit_loss = ((tp - entry_p) / entry_p) * 100
                        exit_date = row['Date']
                        break
                
                if outcome != "PENDING":
                    all_results.append({
                        "ticker": ticker,
                        "mode": mode,
                        "entry_date": df.iloc[i]['Date'],
                        "exit_date": exit_date,
                        "entry_price": entry_p,
                        "exit_price": exit_price,
                        "outcome": outcome,
                        "profit_loss": profit_loss,
                        "reason": signal['reason']
                    })
                    # Skip i agar tidak membuka trade berlipat di hari yang berdekatan
                    i += 5 

    return pd.DataFrame(all_results)

def main():
    # Menjalankan backtest untuk kedua mode
    # 1. Backtest SWING
    df_swing = run_backtest("SWING")
    
    # 2. Backtest SCALPING
    df_scalp = run_backtest("SCALPING")
    
    # Gabungkan hasil
    final_df = pd.concat([df_swing, df_scalp], ignore_index=True)
    
    if not final_df.empty:
        os.makedirs(ROOT / "output", exist_ok=True)
        final_df.to_csv(ROOT / "output" / "backtest_results.csv", index=False)
        
        # Ringkasan Statistik
        print("\n" + "="*30)
        print(f"TOTAL TRADES     : {len(final_df)}")
        win_rate = (final_df['outcome'] == 'WIN').mean() * 100
        print(f"WIN RATE         : {win_rate:.2f}%")
        print(f"AVG PROFIT/TRADE : {final_df['profit_loss'].mean():.2f}%")
        print("="*30)
        print(f"Detail laporan disimpan di: output/backtest_results.csv")
    else:
        print("\n[!] Tidak ada sinyal yang ditemukan selama periode backtest.")

if __name__ == "__main__":
    main()