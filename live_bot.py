"""
STEP: Live Auto-Trading Bot (Binance Testnet)
================================================
This runs your strategy continuously against Binance Testnet:
  - Every cycle, it checks the latest 15-min candles
  - If a moving-average crossover signal fires, it places a REAL
    (but fake-money) market order on testnet
  - While holding a position, it watches for stop-loss / take-profit
  - Every completed trade is logged to trade_log.csv

This is still 100% fake money (testnet). Nothing here touches real
funds. This is the "paper trading" stage of your roadmap.

SETUP:
    pip install python-binance python-dotenv pandas

Uses the same .env file as test_connection.py:
    BINANCE_API_KEY=...
    BINANCE_API_SECRET=...

RUN:
    python live_bot.py

Leave this running in a terminal window (or a cloud server later) -
it loops forever until you stop it with Ctrl+C.
"""

import os
import json
import time
import csv
from datetime import datetime, timezone
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()

API_KEY = os.environ["BINANCE_API_KEY"]
API_SECRET = os.environ["BINANCE_API_SECRET"]

# --- Strategy settings (matches our 15-min backtest: 1:3 risk:reward) ---
SYMBOL = "BTCUSDT"
KLINE_INTERVAL = Client.KLINE_INTERVAL_15MINUTE
SHORT_WINDOW = 20
LONG_WINDOW = 60
STOP_LOSS_PCT = 0.025
TAKE_PROFIT_PCT = 0.075
TRADE_AMOUNT_USDT = 100   # how much fake USDT to spend per trade
CHECK_INTERVAL_SECONDS = 60  # how often to check price for stop-loss/take-profit

STATE_FILE = "bot_state.json"
TRADE_LOG_FILE = "trade_log.csv"
STATUS_FILE = "status.json"  # written every cycle for the dashboard to read
WEBHOOK_SIGNAL_FILE = "webhook_signal.json"  # written by dashboard_server.py's /webhook route


def check_webhook_signal():
    """Check if a fresh TradingView webhook signal is waiting to be acted on."""
    if not os.path.exists(WEBHOOK_SIGNAL_FILE):
        return None
    with open(WEBHOOK_SIGNAL_FILE, "r") as f:
        signal = json.load(f)
    if signal.get("processed"):
        return None
    return signal


def mark_webhook_processed():
    if os.path.exists(WEBHOOK_SIGNAL_FILE):
        with open(WEBHOOK_SIGNAL_FILE, "r") as f:
            signal = json.load(f)
        signal["processed"] = True
        with open(WEBHOOK_SIGNAL_FILE, "w") as f:
            json.dump(signal, f, indent=2)


def get_account_balance(client, current_price):
    """Fetch USDT and BTC balances and compute total portfolio value in USDT."""
    usdt = client.get_asset_balance(asset="USDT")
    btc = client.get_asset_balance(asset="BTC")

    usdt_total = float(usdt["free"]) + float(usdt["locked"])
    btc_total = float(btc["free"]) + float(btc["locked"])
    portfolio_value = usdt_total + (btc_total * current_price)

    return usdt_total, btc_total, portfolio_value


def write_status(price, short_ma, long_ma, state, usdt_balance, btc_balance, portfolio_value):
    status = {
        "price": price,
        "short_ma": short_ma,
        "long_ma": long_ma,
        "in_position": state["in_position"],
        "entry_price": state.get("entry_price"),
        "quantity": state.get("quantity"),
        "entry_time": state.get("entry_time"),
        "usdt_balance": usdt_balance,
        "btc_balance": btc_balance,
        "portfolio_value": portfolio_value,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"in_position": False, "entry_price": None, "quantity": None,
            "entry_time": None, "last_candle_time": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def log_trade(entry_time, exit_time, entry_price, exit_price, quantity, exit_reason):
    file_exists = os.path.exists(TRADE_LOG_FILE)
    pnl = (exit_price - entry_price) * quantity
    pnl_pct = (exit_price - entry_price) / entry_price * 100

    with open(TRADE_LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["entry_time", "exit_time", "entry_price", "exit_price",
                              "quantity", "pnl", "pnl_pct", "exit_reason"])
        writer.writerow([entry_time, exit_time, entry_price, exit_price,
                          quantity, round(pnl, 2), round(pnl_pct, 2), exit_reason])

    print(f"[TRADE LOGGED] {exit_reason} | PnL: {pnl:+.2f} USDT ({pnl_pct:+.2f}%)")


def get_moving_averages(client):
    """Fetch recent klines and compute short/long moving averages + latest close."""
    klines = client.get_klines(symbol=SYMBOL, interval=KLINE_INTERVAL, limit=LONG_WINDOW + 5)
    closes = [float(k[4]) for k in klines]
    candle_open_times = [k[0] for k in klines]

    short_ma = sum(closes[-SHORT_WINDOW:]) / SHORT_WINDOW
    long_ma = sum(closes[-LONG_WINDOW:]) / LONG_WINDOW
    latest_close = closes[-1]
    latest_candle_time = candle_open_times[-1]

    return short_ma, long_ma, latest_close, latest_candle_time


def place_market_buy(client, usdt_amount):
    order = client.create_order(
        symbol=SYMBOL,
        side="BUY",
        type="MARKET",
        quoteOrderQty=usdt_amount,
    )
    fill_price = float(order["fills"][0]["price"]) if order.get("fills") else float(order["cummulativeQuoteQty"]) / float(order["executedQty"])
    quantity = float(order["executedQty"])
    return fill_price, quantity


def place_market_sell(client, quantity):
    order = client.create_order(
        symbol=SYMBOL,
        side="SELL",
        type="MARKET",
        quantity=quantity,
    )
    fill_price = float(order["fills"][0]["price"]) if order.get("fills") else float(order["cummulativeQuoteQty"]) / float(order["executedQty"])
    return fill_price


def main():
    client = Client(API_KEY, API_SECRET, testnet=True)
    state = load_state()

    print("=" * 60)
    print(f"LIVE BOT STARTED - {SYMBOL} - Testnet (fake money)")
    print(f"Strategy: SMA{SHORT_WINDOW}/SMA{LONG_WINDOW}, SL {STOP_LOSS_PCT*100}%, TP {TAKE_PROFIT_PCT*100}%")
    print("=" * 60)

    while True:
        try:
            short_ma, long_ma, price, candle_time = get_moving_averages(client)
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            usdt_balance, btc_balance, portfolio_value = get_account_balance(client, price)

            print(f"[{now}] Price: {price:.2f} | SMA{SHORT_WINDOW}: {short_ma:.2f} | "
                  f"SMA{LONG_WINDOW}: {long_ma:.2f} | In position: {state['in_position']} | "
                  f"Portfolio: {portfolio_value:.2f} USDT")

            write_status(price, short_ma, long_ma, state, usdt_balance, btc_balance, portfolio_value)

            # --- Check for a TradingView webhook signal (manual override channel) ---
            webhook_signal = check_webhook_signal()
            if webhook_signal:
                action = webhook_signal["action"]
                if action == "sell" and state["in_position"]:
                    exit_price = place_market_sell(client, state["quantity"])
                    log_trade(state["entry_time"], now, state["entry_price"], exit_price,
                               state["quantity"], "webhook_signal")
                    state = {"in_position": False, "entry_price": None, "quantity": None,
                              "entry_time": None, "last_candle_time": candle_time}
                    save_state(state)
                    mark_webhook_processed()
                    print(f"[WEBHOOK] Sold via TradingView alert at {exit_price:.2f}")
                elif action == "buy" and not state["in_position"]:
                    fill_price, quantity = place_market_buy(client, TRADE_AMOUNT_USDT)
                    state = {
                        "in_position": True,
                        "entry_price": fill_price,
                        "quantity": quantity,
                        "entry_time": now,
                        "last_candle_time": candle_time,
                    }
                    save_state(state)
                    mark_webhook_processed()
                    print(f"[WEBHOOK] Bought via TradingView alert at {fill_price:.2f}")
                else:
                    # Signal doesn't match current position state (e.g. buy while already in position)
                    mark_webhook_processed()

            if state["in_position"]:
                entry_price = state["entry_price"]
                change_pct = (price - entry_price) / entry_price

                exit_reason = None
                if change_pct <= -STOP_LOSS_PCT:
                    exit_reason = "stop_loss"
                elif change_pct >= TAKE_PROFIT_PCT:
                    exit_reason = "take_profit"
                elif short_ma < long_ma:
                    exit_reason = "signal_exit"

                if exit_reason:
                    exit_price = place_market_sell(client, state["quantity"])
                    log_trade(state["entry_time"], now, entry_price, exit_price,
                               state["quantity"], exit_reason)
                    state = {"in_position": False, "entry_price": None, "quantity": None,
                              "entry_time": None, "last_candle_time": candle_time}
                    save_state(state)

            else:
                # Only consider a new entry once per new candle to avoid re-triggering repeatedly
                is_new_candle = candle_time != state.get("last_candle_time")
                if is_new_candle and short_ma > long_ma:
                    fill_price, quantity = place_market_buy(client, TRADE_AMOUNT_USDT)
                    state = {
                        "in_position": True,
                        "entry_price": fill_price,
                        "quantity": quantity,
                        "entry_time": now,
                        "last_candle_time": candle_time,
                    }
                    save_state(state)
                    usdt_balance, btc_balance, portfolio_value = get_account_balance(client, price)
                    write_status(price, short_ma, long_ma, state, usdt_balance, btc_balance, portfolio_value)
                    print(f"[ENTRY] Bought {quantity} {SYMBOL} at {fill_price:.2f}")
                else:
                    state["last_candle_time"] = candle_time
                    save_state(state)

        except Exception as e:
            print(f"[ERROR] {e}")
            print("Will retry on next cycle...")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
