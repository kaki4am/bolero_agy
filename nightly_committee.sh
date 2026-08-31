#!/bin/bash
# Nightly AI Committee - Map-Reduce Strategy Architecture
# Replaces optimize.sh, weekly_research.sh, and price_research.sh

export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root
export GEMINI_CLI_TRUST_WORKSPACE=true

BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

# 0. Backup current state
for f in *.py GEMINI.md *.json; do
    if [ -s "/root/$f" ]; then
        cp "/root/$f" "$BACKUP_DIR/$f.bak"
    fi
done

perform_rollback() {
    echo "CRITICAL: Committee failed or rejected changes. Rolling back..."
    for f in *.py GEMINI.md *.json; do
        if [ -s "$BACKUP_DIR/$f.bak" ]; then
            cp "$BACKUP_DIR/$f.bak" "/root/$f"
        fi
    done
    systemctl restart trading-bot
    systemctl restart backtest-optimizer
}

echo "========================================="
echo "[$(date)] Starting Nightly Committee..."
echo "========================================="

# 1. Gather Data for Analysts
echo "Gathering data for analysts..."
/root/venv/bin/python /root/export_report.py
/root/venv/bin/python /root/get_db_stats.py
DB_STATS=$(cat /root/db_stats_summary.txt 2>/dev/null)
DAILY_REPORT=$(cat /root/daily_report.json 2>/dev/null)
HEALTH_REPORT=$(/root/venv/bin/python /root/system_health.py)
BOT_LOGS=$(journalctl -u trading-bot.service -n 50 --no-pager)
CURRENT_CONFIG=$(cat /root/config.json)
RECENT_BACKTEST=""
RESEARCH_NOTES=$(cat /root/research_notes.md 2>/dev/null || echo "No previous research notes.")

# Get baseline for Price Analyst
BASELINE=$(/root/venv/bin/python -c "
import asyncio, sys, json
sys.path.insert(0, '/root')
from portfolio_backtester import PortfolioBacktester
async def run():
    with open('/root/config.json') as f:
        params = json.load(f)
    bt = PortfolioBacktester(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'LINKUSDT', 'NEARUSDT', 'INJUSDT', 'UNIUSDT', 'FILUSDT'], lookback='14 days ago UTC')
    await bt.fetch_data()
    bt.precalculate_all(params)
    result = bt.run(params)
    print(f'{result:.4f}')
asyncio.run(run())
" 2>/dev/null | tail -1)

# Get market characteristics for Price Analyst
PRICE_SUMMARY=$(/root/venv/bin/python << 'PYEOF'
import asyncio, json, os
from binance import AsyncClient
from dotenv import load_dotenv
import pandas as pd
import pandas_ta as ta

load_dotenv('/root/.env')

async def analyze():
    client = await AsyncClient.create(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'LINKUSDT', 'NEARUSDT']
    market_summary = {}
    try:
        for sym in symbols:
            klines = await client.get_historical_klines(sym, AsyncClient.KLINE_INTERVAL_1HOUR, "30 days ago UTC")
            df = pd.DataFrame(klines, columns=['t','o','h','l','c','v','ct','qav','nt','tbb','tbq','i'])
            df['close'] = df['c'].astype(float)
            df['high'] = df['h'].astype(float)
            df['low'] = df['l'].astype(float)
            df['volume'] = df['v'].astype(float)
            returns = df['close'].pct_change()
            bb = ta.bbands(df['close'], length=20, std=2.0)
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            market_summary[sym] = {
                'avg_daily_range_pct': float((atr / df['close']).mean() * 100 * 24),
                'trend_30d_pct': float((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100),
                'volatility_hourly': float(returns.std() * 100),
                'bb_squeeze_count': int(((bb['BBU_20_2.0_2.0'] - bb['BBL_20_2.0_2.0']) / bb['BBM_20_2.0_2.0'] < 0.03).sum()) if bb is not None else 0,
                'avg_volume_usd': float((df['close'] * df['volume']).mean()),
            }
    finally:
        await client.close_connection()
    print(json.dumps(market_summary, indent=2))
asyncio.run(analyze())
PYEOF
)

# Get trade analysis for Trade Analyst
TRADE_ANALYSIS=$(/root/venv/bin/python << 'PYEOF'
import sqlite3, json
conn = sqlite3.connect('/root/trading_bot.db')
cursor = conn.cursor()
results = {}
try:
    cursor.execute("""
        WITH buy_sells AS (
            SELECT ((t2.price - t1.price) / t1.price) * 100 as pnl_pct, CAST(strftime('%H', t1.timestamp) AS INTEGER) as hour
            FROM trades t1 JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id) WHERE t1.side = 'BUY'
        )
        SELECT hour, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg, ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr
        FROM buy_sells GROUP BY hour ORDER BY hour
    """)
    results['by_hour'] = [{'hour': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]
    
    cursor.execute("""
        WITH buy_sells AS (
            SELECT ((t2.price - t1.price) / t1.price) * 100 as pnl_pct, CAST(strftime('%w', t1.timestamp) AS INTEGER) as dow
            FROM trades t1 JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id) WHERE t1.side = 'BUY'
        )
        SELECT dow, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg, ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr
        FROM buy_sells GROUP BY dow ORDER BY dow
    """)
    results['by_day'] = [{'dow': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]
    
    cursor.execute("""
        WITH buy_sells AS (
            SELECT ((t2.price - t1.price) / t1.price) * 100 as pnl_pct, (julianday(t2.timestamp) - julianday(t1.timestamp)) * 24 as hold_h
            FROM trades t1 JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id) WHERE t1.side = 'BUY'
        )
        SELECT CASE WHEN hold_h < 2 THEN '0-2h' WHEN hold_h < 6 THEN '2-6h' WHEN hold_h < 12 THEN '6-12h' WHEN hold_h < 24 THEN '12-24h' ELSE '24h+' END as bucket, COUNT(*), ROUND(AVG(pnl_pct), 3), ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1)
        FROM buy_sells GROUP BY bucket
    """)
    results['by_hold_time'] = [{'bucket': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3]} for r in cursor.fetchall()]
    
    cursor.execute("""
        WITH buy_sells AS (
            SELECT t1.pair, ((t2.price - t1.price) / t1.price) * 100 as pnl_pct
            FROM trades t1 JOIN trades t2 ON t1.pair = t2.pair AND t2.side = 'SELL' AND t2.id = (SELECT MIN(id) FROM trades WHERE pair = t1.pair AND side = 'SELL' AND id > t1.id) WHERE t1.side = 'BUY'
        )
        SELECT pair, COUNT(*) as n, ROUND(AVG(pnl_pct), 3) as avg, ROUND(SUM(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) as wr, ROUND(SUM(pnl_pct), 2) as total
        FROM buy_sells GROUP BY pair HAVING n >= 5 ORDER BY avg DESC
    """)
    results['by_pair'] = [{'pair': r[0], 'trades': r[1], 'avg_pnl': r[2], 'win_rate': r[3], 'total_pnl': r[4]} for r in cursor.fetchall()]
except Exception as e:
    pass
conn.close()
print(json.dumps(results, indent=2))
PYEOF
)

# 2. Phase 1: Parallel Analysis
echo "Phase 1: Starting parallel committee analysis..."

PROMPT_PRICE="You are the Price Action Analyst. Analyze the raw market data characteristics and propose 1-2 new entry/exit signals or filters that could improve the strategy.
BASELINE: $BASELINE
MARKET SUMMARY (30d): $PRICE_SUMMARY
PREVIOUS LEARNINGS: $RESEARCH_NOTES
IMPORTANT: YOU ARE AN ANALYST ONLY. DO NOT MODIFY ANY CODE FILES OR WORKSPACE FILES. 
Just output your analysis and proposed logic (including indicators and parameters) directly to standard output. Be extremely concise and clear."

PROMPT_TRADE="You are the Trade Data Analyst. Analyze the historical trade data and identify statistically significant filters (time-of-day, day-of-week, hold time limits, pair exclusions) that could improve win rate.
DB STATS: $DB_STATS
TRADE ANALYSIS: $TRADE_ANALYSIS
PREVIOUS LEARNINGS: $RESEARCH_NOTES
IMPORTANT: YOU ARE AN ANALYST ONLY. DO NOT MODIFY ANY CODE FILES OR WORKSPACE FILES. 
Just output your proposed filters directly to standard output. Be extremely concise and clear."

PROMPT_SYSTEM="You are the System & Risk Analyst. Review the system health, logs, and current performance. Propose structural or risk management changes (stop loss, take profit, portfolio guards).
HEALTH REPORT: $HEALTH_REPORT
LAST 24H PERFORMANCE: $DAILY_REPORT
RECENT LOGS: $BOT_LOGS
RECENT BACKTEST: $RECENT_BACKTEST
PREVIOUS LEARNINGS: $RESEARCH_NOTES
IMPORTANT: YOU ARE AN ANALYST ONLY. DO NOT MODIFY ANY CODE FILES OR WORKSPACE FILES. 
Just output your structural/risk proposals directly to standard output. Be extremely concise and clear."

# Run in background with separate logs
agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 10m0s --print "$PROMPT_PRICE" > /root/price_ideas.md 2>/dev/null &
PID_PRICE=$!
agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 10m0s --print "$PROMPT_TRADE" > /root/trade_ideas.md 2>/dev/null &
PID_TRADE=$!
agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 10m0s --print "$PROMPT_SYSTEM" > /root/system_ideas.md 2>/dev/null &
PID_SYSTEM=$!

wait $PID_PRICE
wait $PID_TRADE
wait $PID_SYSTEM

echo "Phase 1 complete. Ideas generated."

# Stop heavy background tuner to save RAM during AI pipeline
systemctl stop backtest-optimizer

# Calculate Baseline for Architect
BASELINE_VAL=$(/root/venv/bin/python /root/run_quick_validation.py --baseline 2>/dev/null | tail -1)

PROMPT_ARCHITECT=$(cat <<EOF
You are the Chief Architect of the trading system. Your job is to read the proposals from your committee, synthesize the best ideas, and apply the final cohesive changes to the codebase.

COMMITTEE REPORTS:
--- PRICE IDEAS ---
$(cat /root/price_ideas.md 2>/dev/null)
--- TRADE IDEAS ---
$(cat /root/trade_ideas.md 2>/dev/null)
--- SYSTEM IDEAS ---
$(cat /root/system_ideas.md 2>/dev/null)

INSTRUCTIONS:
1. Review all the ideas. Discard any that contradict each other or seem too risky/overfit.
2. Formulate a final strategy plan.
3. IMPLEMENT the chosen changes by modifying bot.py, portfolio_backtester.py, and tuner.py (if SEARCH_SPACE needs changing). Ensure the logic is 100% aligned. CRITICAL: Clean up any unused imports or dead code to pass linters.
4. ITERATE AND TEST: First, run \`/root/venv/bin/python /root/verify_system.py\` to catch any vulture (dead code) or syntax errors, and fix them. Then, run \`/root/venv/bin/python /root/run_quick_validation.py\` using your run_command tool. The current baseline score is ${BASELINE_VAL:-"Unknown"}. If your new code scores lower than the baseline, revise your code and test again. MAXIMUM 5 ATTEMPTS. If you cannot beat the baseline after 5 attempts, you MUST stop testing, revert your changes to the safest option, and proceed to the next steps. Do NOT loop infinitely. Once you beat the baseline (or hit 5 fails), immediately proceed to step 5.
5. Modify config.json if new parameters are needed. You are also explicitly AUTHORIZED to modify bolero.py, dashboard.py, and other UI scripts if the new strategy logic requires new visualizations, data tracking, or updated UI options.
6. Update the strategy version and "Current Active Strategy" block in GEMINI.md.
7. Write a summary of your actions to daily_opinion.html as raw HTML (no markdown backticks).
8. If an idea was rejected, append a 1-sentence note to research_notes.md.
EOF
)

agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 15m0s --print "$PROMPT_ARCHITECT" > /dev/null

echo "Phase 3: Running Auditors..."
bash /root/audit_coherence.sh
bash /root/audit_hygiene.sh

# 4. Verification and Backtest Gate
echo "Phase 4: Verification and Backtest Gate..."

VERIFY_PASSED=false
for ATTEMPT in 1 2 3; do
    VERIFY_OUTPUT=$(/root/venv/bin/python /root/verify_system.py 2>&1)
    if [ $? -eq 0 ]; then
        VERIFY_PASSED=true
        echo "Verification passed."
        break
    else
        echo "Verification FAILED (attempt $ATTEMPT/3). Asking AI to fix..."
        FIX_PROMPT="The code you just wrote failed verification. Fix these errors and try again. Do NOT explain, just fix the files:
$VERIFY_OUTPUT"
        agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 5m0s --print "$FIX_PROMPT" > /dev/null
    fi
done

if [ "$VERIFY_PASSED" = true ]; then
    echo "Running backtest gate..."
    BACKTEST_RESULT=$(/root/venv/bin/python /root/run_quick_validation.py | tail -1)
    
    BASELINE_VAL=$(/root/venv/bin/python /root/run_quick_validation.py --baseline | tail -1)

    echo "Baseline: ${BASELINE_VAL}% | New: ${BACKTEST_RESULT}%"
    
    PASSES=$(python3 -c "
try:
    baseline = float('${BASELINE_VAL:-"-999"}')
    result = float('${BACKTEST_RESULT:-"-999"}')
    print('yes' if result > -990.0 and result >= baseline else 'no')
except:
    print('no')
" 2>/dev/null)

    if [ "$PASSES" = "yes" ]; then
        echo "Backtest PASSED! Deploying changes..."
        echo "[$(date)] Nightly Committee Evolved Strategy! Baseline: ${BASELINE_VAL} -> ${BACKTEST_RESULT}" >> /root/strategy_evolver.log
        systemctl restart trading-bot
        systemctl restart backtest-optimizer
        
        echo "Pushing new strategy to GitHub..."
        git -C /root add *.py GEMINI.md *.json *.md 2>/dev/null
        git -C /root commit -m "Auto-Deploy: Nightly Committee Strategy Evolution (Score: ${BACKTEST_RESULT})" 2>/dev/null
        git -C /root push origin main 2>/dev/null
    else
        echo "Backtest gate FAILED (Score: $BACKTEST_RESULT). Rolling back."
        perform_rollback
    fi
else
    echo "Verification FAILED. Rolling back."
    perform_rollback
fi

# Clean up ideas so they don't leak into next run
rm -f /root/price_ideas.md /root/trade_ideas.md /root/system_ideas.md
echo "Nightly Committee finished."
