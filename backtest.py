"""
STEP 1: Your first trading strategy backtest
==============================================
Strategy: Moving Average Crossover (a classic beginner strategy)

THE IDEA:
- Calculate a short-term average price (e.g. last 20 days) and a
  long-term average price (e.g. last 50 days)
- When the short average crosses ABOVE the long average -> BUY signal
  (price is gaining upward momentum)
- When the short average crosses BELOW the long average -> SELL signal
  (momentum is turning down)

This is not necessarily a profitable strategy - it's a starting point to
learn how backtesting works. We measure everything so we can judge it
honestly rather than guessing.

HOW TO RUN THIS FOR REAL:
1. pip install pandas numpy matplotlib yfinance
2. Replace load_data() with the real data loader (see fetch_real_data.py)
3. python backtest.py
"""

import pandas as pd
import numpy as np


def load_data(csv_path):
    """Load price data. Expects columns: Date, Close"""
    df = pd.read_csv(csv_path, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def add_signals(df, short_window=20, long_window=50):
    """Add moving averages and buy/sell signals to the dataframe."""
    df["SMA_short"] = df["Close"].rolling(window=short_window).mean()
    df["SMA_long"] = df["Close"].rolling(window=long_window).mean()

    # Signal: 1 = we should be holding (long), 0 = we should be out (cash)
    df["signal"] = 0
    df.loc[df["SMA_short"] > df["SMA_long"], "signal"] = 1

    # A "trade" happens when signal changes from previous row
    df["signal_change"] = df["signal"].diff()
    # signal_change ==  1 -> just turned BUY
    # signal_change == -1 -> just turned SELL
    return df


def run_backtest(df, starting_balance=10000, stop_loss_pct=0.05, take_profit_pct=0.15):
    """
    Simulate trades based on signals, applying a stop-loss and take-profit
    to each trade rather than just following signals blindly to exit.
    """
    balance = starting_balance
    position = None  # holds entry price + size while in a trade
    trades = []
    equity_curve = []

    for i, row in df.iterrows():
        price = row["Close"]

        # --- Manage an open position: check stop-loss / take-profit first ---
        if position is not None:
            entry_price = position["entry_price"]
            change_pct = (price - entry_price) / entry_price

            exit_reason = None
            if change_pct <= -stop_loss_pct:
                exit_reason = "stop_loss"
            elif change_pct >= take_profit_pct:
                exit_reason = "take_profit"
            elif row["signal_change"] == -1:
                exit_reason = "signal_exit"

            if exit_reason:
                pnl = position["size"] * change_pct
                balance += pnl
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": row["Date"],
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl": pnl,
                    "pnl_pct": change_pct * 100,
                    "exit_reason": exit_reason,
                })
                position = None

        # --- Consider entering a new position ---
        if position is None and row["signal_change"] == 1:
            risk_amount = balance * 0.02  # risk 2% of balance per trade
            position = {
                "entry_price": price,
                "entry_date": row["Date"],
                "size": risk_amount / stop_loss_pct,  # position sized so stop-loss = risk_amount
            }

        equity_curve.append({"Date": row["Date"], "balance": balance})

    equity_df = pd.DataFrame(equity_curve)
    trades_df = pd.DataFrame(trades)
    return trades_df, equity_df, balance


def summarize(trades_df, equity_df, starting_balance, final_balance):
    if len(trades_df) == 0:
        print("No trades were triggered by this strategy on this data period.")
        return

    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]
    win_rate = len(wins) / len(trades_df) * 100

    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Max drawdown
    equity_df["peak"] = equity_df["balance"].cummax()
    equity_df["drawdown_pct"] = (equity_df["peak"] - equity_df["balance"]) / equity_df["peak"] * 100
    max_dd = equity_df["drawdown_pct"].max()

    total_return_pct = (final_balance - starting_balance) / starting_balance * 100

    print("=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(f"Starting balance:   ${starting_balance:,.2f}")
    print(f"Final balance:      ${final_balance:,.2f}")
    print(f"Total return:       {total_return_pct:+.2f}%")
    print(f"Total trades:       {len(trades_df)}")
    print(f"Win rate:           {win_rate:.1f}%")
    print(f"Profit factor:      {profit_factor:.2f}")
    print(f"Max drawdown:       {max_dd:.1f}%")
    print("=" * 50)
    print("\nExit reasons breakdown:")
    print(trades_df["exit_reason"].value_counts())


if __name__ == "__main__":
    # These are the settings YOU found via optimize.py - update if you re-run optimization
    SHORT_WINDOW = 20
    LONG_WINDOW = 100
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.20

    df = load_data("sample_btc_data.csv")
    df = add_signals(df, short_window=SHORT_WINDOW, long_window=LONG_WINDOW)
    trades_df, equity_df, final_balance = run_backtest(
        df, starting_balance=10000, stop_loss_pct=STOP_LOSS, take_profit_pct=TAKE_PROFIT
    )
    summarize(trades_df, equity_df, starting_balance=10000, final_balance=final_balance)

    if len(trades_df) > 0:
        trades_df.to_csv("backtest_trades.csv", index=False)
        print("\nFull trade log saved to backtest_trades.csv")
