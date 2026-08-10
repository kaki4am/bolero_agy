#!/bin/bash
# Bi-weekly Price Data Research - Test alternative entry signals on raw market data
# Runs every other Sunday at 4am via cron (offset from trade DB research at 3am)

export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root
export GEMINI_CLI_TRUST_WORKSPACE=true

BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

# Backup files before AI runs
for f in bot.py portfolio_backtester.py GEMINI.md config.json restricted_pairs.json; do
    if [ -s "/root/$f" ]; then
        cp "/root/$f" "$BACKUP_DIR/$f.bak"
    fi
done

perform_rollback() {
    echo "CRITICAL: Price research rollback triggered..."
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

# Generate current performance baseline
BASELINE=$(/root/venv/bin/python -c "
import asyncio, sys, json
sys.path.insert(0, '/root')
from portfolio_backtester import PortfolioBacktester

async def run():
    with open('/root/config.json') as f:
        params = json.load(f)
    bt = PortfolioBacktester(
        ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'LINKUSDT', 'NEARUSDT', 'INJUSDT', 'UNIUSDT', 'FILUSDT'],
        lookback='14 days ago UTC'
    )
    await bt.fetch_data()
    bt.precalculate_all(params)
    result = bt.run(params)
    print(f'{result:.4f}')

asyncio.run(run())
" 2>/dev/null | tail -1)

echo "Current strategy baseline (14-day): ${BASELINE}%"

# Get available indicators and price data summary
PRICE_SUMMARY=$(/root/venv/bin/python << 'PYEOF'
import asyncio, json, os
from binance import AsyncClient
from dotenv import load_dotenv
import pandas as pd
import pandas_ta as ta

load_dotenv('/root/.env')

async def analyze():
    client = await AsyncClient.create(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
    
    # Fetch 30 days of 1h data for top pairs to characterize the market
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
            
            # Compute market characteristics
            returns = df['close'].pct_change()
            bb = ta.bbands(df['close'], length=20, std=2.0)
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            market_summary[sym] = {
                'avg_daily_range_pct': float((atr / df['close']).mean() * 100 * 24),
                'trend_30d_pct': float((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100),
                'volatility_hourly': float(returns.std() * 100),
                'bb_squeeze_count': int(((bb['BBU_20_2.0_2.0'] - bb['BBL_20_2.0_2.0']) / bb['BBM_20_2.0_2.0'] < 0.03).sum()),
                'avg_volume_usd': float((df['close'] * df['volume']).mean()),
            }
    finally:
        await client.close_connection()
    print(json.dumps(market_summary, indent=2))

asyncio.run(analyze())
PYEOF
)

CURRENT_CONFIG=$(cat /root/config.json)
CURRENT_BOT=$(cat /root/bot.py)
CURRENT_BT=$(cat /root/portfolio_backtester.py)

PREVIOUS_RESEARCH="No previous research found."
if [ -f "/root/price_research.html" ]; then
    PREVIOUS_RESEARCH=$(cat /root/price_research.html)
fi
RESEARCH_NOTES=$(cat /root/research_notes.md 2>/dev/null || echo "No previous research notes.")

PROMPT=$(cat <<'PROMPT_END'
You are a quantitative trading strategy researcher. Your job is to analyze raw price data characteristics and propose NEW entry signals that could outperform the current strategy.

CURRENT STRATEGY PERFORMANCE:
PROMPT_END
)

PROMPT="$PROMPT
- 14-day backtest baseline: ${BASELINE}%
- Current entry signals: RSI(14) crossing above 30 from below, MACD histogram reversal (neg to pos)
- Current filters: BTC uptrend, 15m EMA trend, SMA200 above, time-of-day (14-16 UTC, 21 UTC), day-of-week (Thu-Sun only)
- Current exits: ATR stop loss, breakeven after 6h, trailing at +4%, 48h time exit

MARKET CHARACTERISTICS (last 30 days):
$PRICE_SUMMARY

PREVIOUS RESEARCH FINDINGS (Read this to avoid repeating recently failed experiments):
$PREVIOUS_RESEARCH

PREVIOUS LEARNINGS / REJECTED IDEAS FROM OTHER AGENTS:
$RESEARCH_NOTES

CURRENT BOT CODE: /root/bot.py
CURRENT BACKTESTER CODE: /root/portfolio_backtester.py
CURRENT CONFIG: $CURRENT_CONFIG

YOUR TASK:
1. Propose 2-3 alternative or additional entry signals that exploit different market microstructure (e.g., Bollinger Band squeezes, volume breakouts, mean reversion after large drops, support/resistance bounces).
2. For each proposed signal, explain the market logic (WHY it should work), not just the indicator math.
3. If you believe a signal would improve results, implement it as an ADDITIONAL setup (V100_NewSetup) in both bot.py and portfolio_backtester.py. Do NOT remove existing setups that are working.
4. The new signal must:
   - Still respect the time-of-day and day-of-week filters (Session Sniper)
   - Still respect the 6h min hold / 48h max hold
   - Use pre-calculated indicators (don't add heavy computation to the hot path)
   - Be aligned between bot and backtester
5. Write a research report to /root/price_research.html explaining your proposed signals, the market logic, and what you implemented.
6. IMPORTANT: Be conservative. One solid additional signal is better than three weak ones. If nothing clearly beats the current setup, write the report explaining why and make NO code changes.
7. RESEARCH LEDGER: If you test an idea and reject it, or learn something new that does NOT result in a code change, you MUST write a brief 1-sentence note to /root/research_notes.md (append to the file). This prevents you from repeating the exact same failed experiments. However, if market conditions have changed significantly, or you are testing a meaningful variation of a past idea, you MAY retry it.

OUTPUT: Research report to /root/price_research.html. Code changes only if you're confident they improve the strategy."

echo "[$(date)] Running price data research (baseline: ${BASELINE}%)..." >> /root/strategy_evolver.log

if agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 30m0s --print "$PROMPT"; then
    echo "AI price research run completed."

    # Check if code was changed
    FILES_CHANGED=false
    if ! cmp -s /root/bot.py "$BACKUP_DIR/bot.py.bak" || \
       ! cmp -s /root/portfolio_backtester.py "$BACKUP_DIR/portfolio_backtester.py.bak"; then
        FILES_CHANGED=true
    fi

    if [ "$FILES_CHANGED" = true ]; then
        echo "Code changes detected. Running verification..."
        
        # Retry loop: give agy up to 3 attempts to fix errors
        VERIFY_PASSED=false
        for ATTEMPT in 1 2 3; do
            if /root/venv/bin/python /root/verify_system.py 2>&1; then
                VERIFY_PASSED=true
                break
            else
                echo "Verification FAILED (attempt $ATTEMPT/3)."
                if [ $ATTEMPT -lt 3 ]; then
                    ERRORS=$(/root/venv/bin/python /root/verify_system.py 2>&1 | grep -E "FAIL|Error" | head -10)
                    agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 5m0s --print "Fix these verification errors in the code: $ERRORS" 2>/dev/null || break
                fi
            fi
        done
        
        if [ "$VERIFY_PASSED" = true ]; then
            echo "Verification passed. Running backtest gate..."

            BACKTEST_RESULT=$(/root/venv/bin/python -c "
import asyncio, sys, json
sys.path.insert(0, '/root')
from portfolio_backtester import PortfolioBacktester

async def quick_test():
    with open('/root/config.json') as f:
        params = json.load(f)
    bt = PortfolioBacktester(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'], lookback='5 days ago UTC')
    await bt.fetch_data()
    bt.precalculate_all(params)
    result = bt.run(params)
    print(f'{result:.4f}')

asyncio.run(quick_test())
" 2>/dev/null | tail -1)

            echo "Backtest result: ${BACKTEST_RESULT}%"
            
            # Must beat baseline by at least 1% to deploy
            IMPROVEMENT=$(python3 -c "
baseline = float('${BASELINE:-\"-999\"}')
result = float('${BACKTEST_RESULT:-\"-999\"}')
print('yes' if result > -1.0 and result > baseline + 1.0 else 'no')
" 2>/dev/null)

            if [ "$IMPROVEMENT" = "yes" ]; then
                echo "[$(date)] Price research deployed! Baseline: ${BASELINE}% -> New: ${BACKTEST_RESULT}%" >> /root/strategy_evolver.log
                systemctl restart trading-bot
                systemctl restart backtest-optimizer
                sleep 10
                if ! systemctl is-active --quiet trading-bot; then
                    echo "CRITICAL: Bot failed after research deploy! Rolling back..."
                    perform_rollback
                fi
            else
                echo "New strategy (${BACKTEST_RESULT}%) didn't beat baseline (${BASELINE}%) by >1%. Rolling back..."
                echo "[$(date)] Price research REJECTED (no improvement over baseline)." >> /root/strategy_evolver.log
                perform_rollback
            fi
        else
            echo "Verification FAILED after 3 attempts. Rolling back..."
            echo "[$(date)] Price research REJECTED by verification." >> /root/price_research.log
            perform_rollback
        fi
    else
        echo "[$(date)] Price research completed (report only, no code changes)." >> /root/strategy_evolver.log
    fi
else
    echo "[$(date)] Price research AI run failed." >> /root/strategy_evolver.log
    perform_rollback
fi
