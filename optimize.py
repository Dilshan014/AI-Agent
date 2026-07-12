"""
STEP 2: Optimize the strategy
================================
This tests MANY combinations of moving average lengths and
stop-loss/take-profit levels to find which settings give the most
STABLE result (not just the highest return - stability matters more
when you're starting with small capital).

RUN:
    python optimize.py

Requires sample_btc_data.csv to already exist (run fetch_real_data.py first).
"""

import pandas as pd
from backtest import load_data, add_signals, run_backtest

# Ranges to test - feel free to adjust
SHORT_WINDOWS = [10, 20, 30]
LONG_WINDOWS = [40, 50, 100]
STOP_LOSSES = [0.03, 0.05, 0.08]
TAKE_PROFITS = [0.10, 0.15, 0.20]


def main():
    df_raw = load_data("sample_btc_data.csv")
    results = []

    for short in SHORT_WINDOWS:
        for long in LONG_WINDOWS:
            if short >= long:
                continue  # short average must be shorter than long average
            for sl in STOP_LOSSES:
                for tp in TAKE_PROFITS:
                    df = add_signals(df_raw.copy(), short_window=short, long_window=long)
                    trades_df, equity_df, final_balance = run_backtest(
                        df, starting_balance=10000, stop_loss_pct=sl, take_profit_pct=tp
                    )

                    if len(trades_df) < 3:
                        continue  # too few trades to trust the result

                    wins = trades_df[trades_df["pnl"] > 0]
                    losses = trades_df[trades_df["pnl"] <= 0]
                    win_rate = len(wins) / len(trades_df) * 100
                    gross_profit = wins["pnl"].sum()
                    gross_loss = abs(losses["pnl"].sum())
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

                    equity_df["peak"] = equity_df["balance"].cummax()
                    equity_df["dd_pct"] = (equity_df["peak"] - equity_df["balance"]) / equity_df["peak"] * 100
                    max_dd = equity_df["dd_pct"].max()

                    total_return_pct = (final_balance - 10000) / 10000 * 100

                    results.append({
                        "short_window": short,
                        "long_window": long,
                        "stop_loss_pct": sl,
                        "take_profit_pct": tp,
                        "total_trades": len(trades_df),
                        "win_rate": round(win_rate, 1),
                        "profit_factor": round(profit_factor, 2),
                        "total_return_pct": round(total_return_pct, 2),
                        "max_drawdown_pct": round(max_dd, 1),
                    })

    results_df = pd.DataFrame(results)

    if results_df.empty:
        print("No combinations produced enough trades to evaluate. Try wider ranges.")
        return

    # "Stability score" - reward profit factor and return, penalize drawdown
    results_df["stability_score"] = (
        results_df["profit_factor"] * 2
        + results_df["total_return_pct"] * 0.1
        - results_df["max_drawdown_pct"] * 0.3
    )

    results_df = results_df.sort_values("stability_score", ascending=False)
    results_df.to_csv("optimization_results.csv", index=False)

    print("=" * 70)
    print("TOP 10 MOST STABLE COMBINATIONS")
    print("=" * 70)
    print(results_df.head(10).to_string(index=False))
    print("\nFull results (all combinations tested) saved to optimization_results.csv")

    best = results_df.iloc[0]
    print("\n" + "=" * 70)
    print("RECOMMENDED SETTINGS (best stability score)")
    print("=" * 70)
    print(f"Short MA window:  {int(best['short_window'])} days")
    print(f"Long MA window:   {int(best['long_window'])} days")
    print(f"Stop-loss:        {best['stop_loss_pct']*100:.0f}%")
    print(f"Take-profit:      {best['take_profit_pct']*100:.0f}%")
    print(f"--> Total return: {best['total_return_pct']:+.2f}%")
    print(f"--> Win rate:     {best['win_rate']:.1f}%")
    print(f"--> Profit factor:{best['profit_factor']:.2f}")
    print(f"--> Max drawdown: {best['max_drawdown_pct']:.1f}%")


if __name__ == "__main__":
    main()
