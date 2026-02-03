#!/usr/bin/env python3
import time
import os
from pathlib import Path
from typing import List, Set
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------
# CONFIG
# ---------------------------
TICKERS: List[str] = [
    # isi sesuai config/tickers.py atau import dari sana
    "BBRI","BBCA","BMRI","BBNI","ANTM","ADRO","PTBA","ITMG","BUMI","DEWA",
    "ARCI","CUAN","MDKA","EMTK","SCMA","BABY","IOTF","ASII","PTRO","ZATA",
    "OASA","NAIK","CDIA","IRSX"
]

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = ROOT / "data" / "idx"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Use visible browser (headful) — more reliable
CHROME_OPTIONS = webdriver.ChromeOptions()
CHROME_OPTIONS.add_experimental_option("prefs", {
    "download.default_directory": str(DOWNLOAD_DIR.resolve()),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})
# optionally you can disable headless to see browser; headless sometimes blocked
# CHROME_OPTIONS.add_argument("--headless=new")  # avoid headless if blocked

# User agent can help, but using real Chrome should be fine
# CHROME_OPTIONS.add_argument("user-agent=Mozilla/5.0 ...")

# ---------------------------
# Helpers
# ---------------------------
def wait_for_new_csv(before: Set[str], timeout=30):
    """Poll the download folder for a new .csv file not in 'before' set."""
    start = time.time()
    while time.time() - start < timeout:
        files = set(p.name for p in DOWNLOAD_DIR.glob("*.csv"))
        new = files - before
        if new:
            # return one (there should be only one per click)
            return list(new)[0]
        time.sleep(0.5)
    return None

def sanitize_and_move(file_name: str, ticker: str):
    """Rename the downloaded file to {TICKER}.csv"""
    src = DOWNLOAD_DIR / file_name
    dst = DOWNLOAD_DIR / f"{ticker}.csv"
    try:
        src.rename(dst)
    except Exception:
        # fallback: copy contents then remove original
        import shutil
        shutil.copy2(src, dst)
        try:
            src.unlink()
        except Exception:
            pass

# ---------------------------
# Main
# ---------------------------
def main():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=CHROME_OPTIONS)
    wait = WebDriverWait(driver, 20)

    try:
        for ticker in TICKERS:
            symbol = f"{ticker}.JK"
            url = f"https://finance.yahoo.com/quote/{symbol}/history"

            print(f"[{ticker}] opening {url}")
            driver.get(url)

            # Wait page to load: the "Historical Data" table or Download link
            # The download anchor has attribute 'download' in Yahoo, try locate it
            try:
                # Accept cookies popup if shown (common)
                try:
                    consent_btn = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Accept') or contains(., 'Agree') or contains(., 'Accept all')]")
                    ))
                    consent_btn.click()
                    time.sleep(0.5)
                except Exception:
                    pass

                # Wait until the "Download" link appears
                dl_before = set(p.name for p in DOWNLOAD_DIR.glob("*.csv"))
                dl_el = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@download, '.csv') or contains(text(),'Download')]")
                ))
                time.sleep(0.5)  # tiny pause
                dl_el.click()
                print(f"[{ticker}] clicked download, waiting file...")
                new = wait_for_new_csv(dl_before, timeout=40)
                if new:
                    sanitize_and_move(new, ticker)
                    print(f"[{ticker}] saved to {DOWNLOAD_DIR / (ticker + '.csv')}")
                else:
                    print(f"[{ticker}] no CSV detected after click")
            except Exception as e:
                print(f"[{ticker}] error while downloading: {e}")

            # be polite — sleep to avoid rate limiting
            time.sleep(6)  # you can increase to 8-12 if blocked
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
