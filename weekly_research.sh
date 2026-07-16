#!/bin/bash
# Weekly AI Research Job - Discover new edges from trade data
# Runs Sunday 3am via cron

export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root
export GEMINI_CLI_TRUST_WORKSPACE=true

# Generate fresh stats
/root/venv/bin/python /root/get_db_stats.py

# Run the data mining queries
TRADE_ANALYSIS=$(/root/venv/bin/python << 'PYEOF'
import sqlite3
import json

conn = sqlite3.connect('/root/trading_bot.db')
cursor = conn.cursor()

results = {}

# PnL by hour of entry
cursor.execute("""
    WITH buy_sells AS (
        SELECT t1.timestamp as buy_time, t2.price as sell_price, t1.price as buy_price,
            ((t2.price - t1.price) / t1.price) * 100 as pnl_pct,
            CAST(strftime('%H', t1.timestamp) AS INTEGER) as hour,
            CAST(strftime('%w', t1.timestamp) AS INTEGER) as dow,
            (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 as hold_h,
            t1.pair
        FROM trades t1
        JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' 
            AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id)
        WHERE t1.side = 'BUY'
    )
    SELECT hour, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg, 
        ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr
    FROM buy_sells GROUP BY hour ORDER BY hour
""")
results['by_hour'] = [{'hour': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]

# PnL by day of week
cursor.execute("""
    WITH buy_sells AS (
        SELECT t1.timestamp as buy_time, t2.price as sell_price, t1.price as buy_price,
            ((t2.price - t1.price) / t1.price) * 100 as pnl_pct,
            CAST(strftime('%w', t1.timestamp) AS INTEGER) as dow
        FROM trades t1
        JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' 
            AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id)
        WHERE t1.side = 'BUY'
    )
    SELECT dow, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg,
        ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr
    FROM buy_sells GROUP BY dow ORDER BY dow
""")
results['by_day'] = [{'dow': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]

# PnL by hold duration
cursor.execute("""
    WITH buy_sells AS (
        SELECT ((t2.price - t1.price) / t1.price) * 100 as pnl_pct,
            (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 as hold_h
        FROM trades t1
        JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' 
            AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id)
        WHERE t1.side = 'BUY'
    )
    SELECT 
        CASE WHEN hold_h < 2 THEN '0-2h' WHEN hold_h < 6 THEN '2-6h' 
             WHEN hold_h < 12 THEN '6-12h' WHEN hold_h < 24 THEN '12-24h'
             WHEN hold_h < 48 THEN '24-48h' ELSE '48h+' END as bucket,
        COUNT(*), ROUND(AVG(pnl_pct), 3),
        ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1)
    FROM buy_sells GROUP BY bucket
""")
results['by_hold_time'] = [{'bucket': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]

# PnL by pair
cursor.execute("""
    WITH buy_sells AS (
        SELECT t1.pair, ((t2.price - t1.price) / t1.price) * 100 as pnl_pct
        FROM trades t1
        JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' 
            AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id)
        WHERE t1.side = 'BUY'
    )
    SELECT pair, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg,
        ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr,
        ROUND(SUM(pnl_pct), 2) as total
    FROM buy_sells GROUP BY pair HAVING n >= 5 ORDER BY avg DESC
""")
results['by_pair'] = [{'pair': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3], 'total_pnl': r[4]} for r in cursor.fetchall()]

conn.close()
print(json.dumps(results, indent=2))
PYEOF
)

DB_STATS=$(cat /root/db_stats_summary.txt 2>/dev/null)
CURRENT_CONFIG=$(cat /root/config.json)
BOT_CODE=$(cat /root/bot.py)

PROMPT=$(cat <<'PROMPT_END'
You are a quantitative trading researcher. Your job is to analyze the statistical patterns in a live Binance spot trading bot's historical trade data and propose concrete, data-driven improvements.

TRADE DATABASE ANALYSIS (grouped by hour, day, hold time, and pair):
PROMPT_END
)

PROMPT="$PROMPT
$TRADE_ANALYSIS

CURRENT BOT CONFIGURATION:
$CURRENT_CONFIG

LONG-TERM TRADE STATS:
$DB_STATS

CURRENT BOT CODE: /root/bot.py
CURRENT BACKTESTER CODE: /root/portfolio_backtester.py

YOUR TASK:
1. Identify statistically significant patterns in the trade data (time-of-day edges, pair selection, hold time sweet spots, day-of-week effects).
2. Quantify the expected improvement if these patterns were exploited as filters.
3. If you find a filter combination that would turn the overall negative expectancy positive (based on the historical data), implement it by modifying /root/bot.py and /root/portfolio_backtester.py.
4. Write a research report to /root/weekly_research.html explaining your findings, the statistical significance, and what you changed.
5. IMPORTANT: Only make changes that are supported by at least 50 historical trades showing positive expectancy. Do not overfit to small samples.
6. Keep bot.py and portfolio_backtester.py logic perfectly aligned.

OUTPUT: Write findings to /root/weekly_research.html as clean HTML. If you modify code, explain why with data backing."

echo "[$(date)] Running weekly research analysis..." >> /root/strategy_evolver.log

BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

# Backup files before AI runs
for f in bot.py portfolio_backtester.py GEMINI.md config.json restricted_pairs.json; do
    if [ -s "/root/$f" ]; then
        cp "/root/$f" "$BACKUP_DIR/$f.bak"
    fi
done

perform_rollback() {
    echo "CRITICAL: Research rollback triggered..."
    for f in bot.py portfolio_backtester.py GEMINI.md config.json restricted_pairs.json; do
        if [ -s "$BACKUP_DIR/$f.bak" ]; then
            cp "$BACKUP_DIR/$f.bak" "/root/$f"
            echo "  Restored $f from backup"
        else
            echo "  WARNING: Backup for $f is empty/missing, skipping"
        fi
    done
    systemctl restart trading-bot
    systemctl restart backtest-optimizer
}

if agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 30m0s --print "$PROMPT"; then
    echo "AI research run completed."

    # Check if code was changed
    FILES_CHANGED=false
    if ! cmp -s /root/bot.py "$BACKUP_DIR/bot.py.bak" || \
       ! cmp -s /root/portfolio_backtester.py "$BACKUP_DIR/portfolio_backtester.py.bak"; then
        FILES_CHANGED=true
    fi

    if [ "$FILES_CHANGED" = true ]; then
        echo "Code changes detected. Running verification..."
        if /root/venv/bin/python /root/verify_system.py; then
            echo "Verification passed. Running backtest gate..."

            BACKTEST_RESULT=$(/root/venv/bin/python -c "
import asyncio, sys
sys.path.insert(0, '/root')
from portfolio_backtester import PortfolioBacktester
import json

async def quick_test():
    with open('/root/config.json') as f:
        params = json.load(f)
    bt = PortfolioBacktester(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'], lookback='5 days ago UTC')
    await bt.fetch_data()
    bt.precalculate_all(params)
    result = bt.run(params)
    print(f'{result:.4f}')
    return result

asyncio.run(quick_test())
" 2>/dev/null | tail -1)

            echo "Backtest result: ${BACKTEST_RESULT}%"
            PASSES=$(python3 -c "print('yes' if float('${BACKTEST_RESULT:-\"-999\"}') > -1.0 else 'no')" 2>/dev/null)

            if [ "$PASSES" = "yes" ]; then
                echo "[$(date)] Weekly research deployed successfully. Backtest: ${BACKTEST_RESULT}%" >> /root/strategy_evolver.log
                systemctl restart trading-bot
                systemctl restart backtest-optimizer
                sleep 10
                if ! systemctl is-active --quiet trading-bot; then
                    echo "CRITICAL: Bot failed after research deploy! Rolling back..."
                    perform_rollback
                fi
            else
                echo "Backtest gate FAILED (${BACKTEST_RESULT}%). Rolling back..."
                echo "[$(date)] Weekly research REJECTED by backtest gate (${BACKTEST_RESULT}%)." >> /root/strategy_evolver.log
                perform_rollback
            fi
        else
            echo "Verification FAILED. Rolling back..."
            echo "[$(date)] Weekly research REJECTED by verification." >> /root/strategy_evolver.log
            perform_rollback
        fi
    else
        echo "[$(date)] Weekly research completed (no code changes, report only)." >> /root/strategy_evolver.log
    fi
else
    echo "[$(date)] Weekly research AI run failed." >> /root/strategy_evolver.log
    perform_rollback
fi
