"""
STEP 0: Get real historical Bitcoin data
==========================================
Run this ONCE to download real BTC price history into a CSV that
backtest.py can use.

SETUP:
    pip install yfinance pandas

RUN:
    python fetch_real_data.py

This creates 'sample_btc_data.csv' with real daily BTC-USD prices,
which backtest.py already knows how to read.
"""

import yfinance as yf
import pandas as pd

TICKER = "BTC-USD"
PERIOD = "5y"      # how far back: e.g. "1y", "2y", "5y", "max"
INTERVAL = "1d"    # daily candles. Could also use "1h" for hourly, etc.


def fetch_and_save(ticker=TICKER, period=PERIOD, interval=INTERVAL, out_path="sample_btc_data.csv"):
    print(f"Fetching {ticker} data ({period}, {interval} candles)...")
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if data.empty:
        raise RuntimeError("No data returned - check your ticker/period/interval or internet connection.")

    df = data.reset_index()[["Date", "Close"]]
    df.columns = ["Date", "Close"]
    df.to_csv(out_path, index=False)

    print(f"Saved {len(df)} rows to {out_path}")
    print(df.head())
    print("...")
    print(df.tail())


if __name__ == "__main__":
    fetch_and_save()
