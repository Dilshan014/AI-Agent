"""
STEP: Connect to Binance Testnet (paper trading)
====================================================
This script verifies your API keys work and shows your fake
testnet balance. This is the first step before running the
strategy live on paper money.

SETUP:
    pip install python-binance python-dotenv

Create a .env file in the same folder with:
    BINANCE_API_KEY= API_KEY
    BINANCE_API_SECRET= API_SECRET

RUN:
    python test_connection.py
"""

import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.environ["BINANCE_API_KEY"]
API_SECRET = os.environ["BINANCE_API_SECRET"]


def main():
    # testnet=True points the client at the paper-trading environment,
    # NOT the real Binance exchange. No real money is ever touched here.
    client = Client(API_KEY, API_SECRET, testnet=True)

    print("Connecting to Binance Testnet...")

    account = client.get_account()
    print("\nConnected successfully!\n")
    print("=" * 50)
    print("YOUR TESTNET BALANCES (fake money)")
    print("=" * 50)

    for balance in account["balances"]:
        free = float(balance["free"])
        locked = float(balance["locked"])
        if free > 0 or locked > 0:
            print(f"{balance['asset']:8s} free: {free:>15.8f}   locked: {locked:>15.8f}")

    # Also fetch the current BTC/USDT price as a sanity check that
    # market data is flowing correctly
    ticker = client.get_symbol_ticker(symbol="BTCUSDT")
    print("\n" + "=" * 50)
    print(f"Current BTC/USDT testnet price: {ticker['price']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
