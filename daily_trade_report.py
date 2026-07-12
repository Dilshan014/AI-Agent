"""
Daily Trading Report -> WhatsApp (via Twilio)

WHAT THIS DOES
--------------
1. Connects to your SQL database
2. Pulls trades from a `trades` table
3. Computes: P&L, balance, win rate, profit factor, drawdown, trade count
4. Formats a short WhatsApp-friendly summary
5. Sends it to your phone via Twilio's WhatsApp API

SETUP REQUIRED (read before running)
-------------------------------------
1. pip install sqlalchemy twilio python-dotenv
   (add psycopg2-binary if Postgres, or pymysql if MySQL, or nothing extra for SQLite)

2. Create a `.env` file next to this script with:
    DB_CONNECTION_STRING=sqlite:///trades.db          # or postgresql://user:pass@host/db etc.
    TWILIO_ACCOUNT_SID=your_account_sid
    TWILIO_AUTH_TOKEN=your_auth_token
    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886         # Twilio sandbox number
    MY_WHATSAPP_NUMBER=whatsapp:+91XXXXXXXXXX          # your number, with country code

3. Adjust EXPECTED SCHEMA below to match your actual `trades` table.
   This script assumes columns:
     id, symbol, entry_price, exit_price, size, stop_loss, target,
     opened_at, closed_at, pnl, status ('open' / 'closed')

4. Run manually first to test:
     python daily_trade_report.py

5. Once it works, schedule it (e.g. cron on Linux/Mac, Task Scheduler on Windows):
     # Run every day at 6:00 PM
     0 18 * * * /usr/bin/python3 /path/to/daily_trade_report.py
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from twilio.rest import Client

load_dotenv()

DB_CONNECTION_STRING = os.environ["DB_CONNECTION_STRING"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ["TWILIO_WHATSAPP_FROM"]
MY_WHATSAPP_NUMBER = os.environ["MY_WHATSAPP_NUMBER"]

STARTING_BALANCE = float(os.environ.get("STARTING_BALANCE", "10000"))  # set your account's starting balance


def get_trades_for_period(engine, start_date, end_date):
    """Pull closed trades within a date range. Adjust column names to match your schema."""
    query = text("""
        SELECT id, symbol, entry_price, exit_price, size,
               stop_loss, target, opened_at, closed_at, pnl, status
        FROM trades
        WHERE status = 'closed'
          AND closed_at >= :start_date
          AND closed_at < :end_date
        ORDER BY closed_at ASC
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"start_date": start_date, "end_date": end_date})
        return [dict(row._mapping) for row in result]


def get_all_time_pnl(engine):
    """Cumulative P&L across all closed trades, for balance/drawdown calc."""
    query = text("""
        SELECT closed_at, pnl
        FROM trades
        WHERE status = 'closed'
        ORDER BY closed_at ASC
    """)
    with engine.connect() as conn:
        result = conn.execute(query)
        return [dict(row._mapping) for row in result]


def compute_metrics(trades_today, all_trades):
    total_trades = len(trades_today)
    wins = [t for t in trades_today if t["pnl"] > 0]
    losses = [t for t in trades_today if t["pnl"] <= 0]

    win_rate = (len(wins) / total_trades * 100) if total_trades else 0.0

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    today_pnl = sum(t["pnl"] for t in trades_today)

    # Running balance & max drawdown across ALL trades (not just today)
    running_balance = STARTING_BALANCE
    peak = STARTING_BALANCE
    max_drawdown_pct = 0.0
    for t in all_trades:
        running_balance += t["pnl"]
        peak = max(peak, running_balance)
        drawdown_pct = (peak - running_balance) / peak * 100 if peak > 0 else 0
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    current_balance = running_balance
    total_pnl_pct = (current_balance - STARTING_BALANCE) / STARTING_BALANCE * 100

    return {
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "today_pnl": today_pnl,
        "current_balance": current_balance,
        "total_pnl_pct": total_pnl_pct,
        "max_drawdown_pct": max_drawdown_pct,
    }


def format_message(metrics, report_date):
    pf_display = f"{metrics['profit_factor']:.2f}" if metrics["profit_factor"] != float("inf") else "∞"
    return (
        f"📊 *Daily Trading Report* — {report_date}\n\n"
        f"💰 Today's P&L: {metrics['today_pnl']:+.2f}\n"
        f"🏦 Balance: {metrics['current_balance']:.2f} "
        f"({metrics['total_pnl_pct']:+.2f}% all-time)\n\n"
        f"📈 Trades today: {metrics['total_trades']} "
        f"({metrics['wins']}W / {metrics['losses']}L)\n"
        f"🎯 Win rate: {metrics['win_rate']:.1f}%\n"
        f"⚖️ Profit factor: {pf_display}\n"
        f"📉 Max drawdown (all-time): {metrics['max_drawdown_pct']:.1f}%\n\n"
        f"_Note: win rate alone can mislead — check profit factor and drawdown too._"
    )


def send_whatsapp_message(body):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=MY_WHATSAPP_NUMBER,
        body=body,
    )
    return message.sid


def main():
    engine = create_engine(DB_CONNECTION_STRING)

    today = datetime.utcnow().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = start_date + timedelta(days=1)

    trades_today = get_trades_for_period(engine, start_date, end_date)
    all_trades = get_all_time_pnl(engine)

    metrics = compute_metrics(trades_today, all_trades)
    message = format_message(metrics, today.strftime("%d %b %Y"))

    print(message)  # also print to console/logs for your own record

    sid = send_whatsapp_message(message)
    print(f"\nSent. Twilio message SID: {sid}")


if __name__ == "__main__":
    main()
