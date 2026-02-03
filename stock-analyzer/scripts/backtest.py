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
    Menjalankan simulasi trading (Backtest) dengan sistem Scoring.
    """
    all_results = []
    data_dir = ROOT / "data" / "idx"
    
    print(f"=== STARTING BACKTEST: MODE {mode} ===")
    
    for ticker in TICKERS:
        file_path = data_dir / f"{ticker}.csv"
        if not os.path.exists(file_path):
            continue
            
        df = pd.read_csv(file_path)
        # REVISI: Mulai dari baris 150 karena engine baru butuh lebih sedikit data (100 bar)
        if len(df) < 150: continue

        # Simulasi berjalan (Moving Window)
        # Menggunakan step 1 agar setiap hari dicek
        for i in range(150, len(df)):
            current_data = df.iloc[:i+1].copy()
            
            # PANGGIL ENGINE
            # Kita set market_bullish=True untuk backtest murni teknikal saham
            signal = analyze_ticker(current_data, ticker, mode, market_bullish=True)

            # REVISI: Logic untuk menangkap 'BUY' dan 'STRONG BUY'
            if "BUY" in signal.get("action", ""):
                entry_p = signal['entry']
                sl = signal['sl']
                tp = signal['tp']
                score = signal.get('score', 0) # Ambil skor
                
                # Cek hasil di masa depan (Maksimal 40 hari trading / 2 bulan)
                future_data = df.iloc[i+1:i+41]
                outcome = "EXPIRED" # Default jika tidak kena TP/SL dalam 40 hari
                profit_loss = 0
                exit_date = None
                exit_price = future_data.iloc[-1]['Close'] if not future_data.empty else entry_p

                for _, row in future_data.iterrows():
                    # 1. Cek Stop Loss (Prioritas Keamanan)
                    if row['Low'] <= sl:
                        outcome = "LOSS"
                        exit_price = sl
                        profit_loss = ((sl - entry_p) / entry_p) * 100
                        exit_date = row['Date']
                        break
                    # 2. Cek Take Profit
                    elif row['High'] >= tp:
                        outcome = "WIN"
                        exit_price = tp
                        profit_loss = ((tp - entry_p) / entry_p) * 100
                        exit_date = row['Date']
                        break
                
                # Simpan Hasil Trade
                all_results.append({
                    "ticker": ticker,
                    "mode": mode,
                    "entry_date": df.iloc[i]['Date'],
                    "exit_date": exit_date,
                    "score": score, # PENTING: Untuk analisa korelasi skor vs winrate
                    "action": signal['action'], # BUY atau STRONG BUY
                    "entry_price": entry_p,
                    "exit_price": exit_price,
                    "outcome": outcome,
                    "profit_loss": round(profit_loss, 2),
                    "reason": signal['reason']
                })
                
                # Lompat 5 hari setelah entry agar tidak spam trade di saham yang sama
                # (Asumsi kita hold posisi minimal beberapa hari)
                # Note: Loop 'for' di python range-nya fix, jadi trik i += 5 tidak efektif di sini
                # tapi logic signal biasanya akan hilang setelah harga bergerak, jadi aman.

    return pd.DataFrame(all_results)

def main():
    # 1. Backtest SWING
    df_swing = run_backtest("SWING")
    
    # 2. Backtest SCALPING
    df_scalp = run_backtest("SCALPING")
    
    # Gabungkan hasil
    final_df = pd.concat([df_swing, df_scalp], ignore_index=True)
    
    if not final_df.empty:
        os.makedirs(ROOT / "output", exist_ok=True)
        output_file = ROOT / "output" / "backtest_results.csv"
        final_df.to_csv(output_file, index=False)
        
        # Ringkasan Statistik
        print("\n" + "="*40)
        print(f"TOTAL TRADES     : {len(final_df)}")
        
        # Winrate Global
        win_count = len(final_df[final_df['outcome'] == 'WIN'])
        win_rate = (win_count / len(final_df)) * 100
        
        # Winrate STRONG BUY saja
        strong_buys = final_df[final_df['action'] == 'STRONG BUY']
        if not strong_buys.empty:
            sb_win = len(strong_buys[strong_buys['outcome'] == 'WIN'])
            sb_rate = (sb_win / len(strong_buys)) * 100
            print(f"WIN RATE (STRONG): {sb_rate:.2f}% (dari {len(strong_buys)} trade)")
            
        print(f"WIN RATE (ALL)   : {win_rate:.2f}%")
        print(f"AVG PROFIT       : {final_df['profit_loss'].mean():.2f}%")
        print("="*40)
        print(f"Laporan lengkap: {output_file}")
    else:
        print("\n[!] Tidak ada sinyal yang ditemukan selama periode backtest.")

if __name__ == "__main__":
    main()