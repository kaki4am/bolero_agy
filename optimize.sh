#!/bin/bash

# Ensure we have a full path and home directory for cron
export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root
export GEMINI_CLI_TRUST_WORKSPACE=true

BACKUP_DIR="/root/backups"
mkdir -p "$BACKUP_DIR"

perform_rollback() {
    echo "CRITICAL: Enforcing rollback to safe backup state..."
    # Only restore if backup files are non-empty
    for f in bot.py portfolio_backtester.py GEMINI.md config.json restricted_pairs.json; do
        if [ -s "$BACKUP_DIR/$f.bak" ]; then
            cp "$BACKUP_DIR/$f.bak" "/root/$f"
            echo "  Restored $f from backup"
        else
            echo "  WARNING: Backup for $f is empty/missing, skipping restore"
        fi
    done
    
    echo "Restarting services to ensure bot is running clean backup state..."
    systemctl restart trading-bot
    systemctl restart backtest-optimizer
}

# 1. Export daily report, database stats, and system health
/root/venv/bin/python /root/export_report.py
/root/venv/bin/python /root/get_db_stats.py
DB_STATS=$(cat /root/db_stats_summary.txt 2>/dev/null)
HEALTH_REPORT=$(/root/venv/bin/python /root/system_health.py)
BOT_LOGS=$(journalctl -u trading-bot.service -n 50 --no-pager)
CURRENT_CONFIG=$(cat /root/config.json)
RECENT_BACKTEST=$(/root/venv/bin/python /root/run_quick_validation.py)

# 2. Invoke Antigravity CLI to analyze and generate strategic recommendations
PROMPT=$(cat <<EOF
You are the strategy consultant and system evolver for the Binance Trading Bot. 
Analyze the system health, daily trading logs, database trade statistics (such as Win Rate, Win/Loss Ratio, holding times, and profit/loss distributions), backtest results, and bot code to provide a concise, high-impact "Daily Strategic Opinion" on what strategy rules, risk settings, or parameters should be modified to improve PnL.

RESOURCES:
- System Health: $HEALTH_REPORT
- Recent Bot Logs: $BOT_LOGS
- Long-Term Trade Stats (Last 30 Days):
$DB_STATS
- Performance Data: /root/daily_report.json
- Current Optimal Tuner Config: $CURRENT_CONFIG
- Recent 5-Day Backtest Stats: $RECENT_BACKTEST
- Bot Code: /root/bot.py
- Backtester Code: /root/portfolio_backtester.py

EVOLUTION MANDATE (ONLY WHEN NECESSARY):
You have the authority to modify the bot's code, backtester code, and evolve the strategy version (e.g. updating GEMINI.md, bot.py, and portfolio_backtester.py). However, to prevent curve-fitting (overfitting) to short-term market noise, you must ONLY apply code changes and increment the version (e.g. from V90 to V91) if it is NECESSARY.

Evolving is considered NECESSARY only if:
1. Underperformance: The current strategy has had negative weekly realized returns or is in a significant drawdown.
2. Large Performance Improvement: Your proposed code changes achieve an absolute simulated PnL improvement of at least +3.0% compared to the current baseline config on both the 5-day main test and the historical stress segments.
3. Critical Fixes: There is a bug, API issue, code/logical discrepancy, or system health error that requires a structural logic change to resolve.

INSTRUCTIONS:
1. If evolution is NOT necessary, do NOT modify any files in the workspace. Write a concise strategic review to /root/daily_opinion.html summarizing the current market conditions and why you decided that a version evolution was NOT necessary today.
2. If evolution IS necessary, make the minimal required edits to /root/bot.py and /root/portfolio_backtester.py, increment the version in /root/GEMINI.md, and write a summary of the new strategy rules and backtest results to /root/daily_opinion.html.
3. Output your daily opinion or change summary to /root/daily_opinion.html as a clean, self-contained HTML block (with inline styling) suitable for embedding inside an email card. Do not include any markdown backticks (such as triple-backtick formatting) in the file—write ONLY raw HTML content.
4. **Code Alignment & Logic Audit**: Always check for discrepancies or logic misalignments between the backtester (/root/portfolio_backtester.py) and the live bot (/root/bot.py) (e.g. exit conditions, indicators, or rules present in one but missing/behaving differently in the other). If you detect any discrepancy, prioritize fixing it immediately as a 'Critical Fix' to keep the backtest engine and live bot 100% aligned.
5. **State Persistence & Daemon Robustness Audit**: Regularly audit the live bot's startup initialization, shutdown, and config reloading routines. Ensure that any runtime state (such as trailing stop-losses, position details, or indicators) is fully preserved across service restarts and config reloads, preventing state loss or structural discrepancies between live trading and the historical backtest engine.
EOF
)

# Get current strategy version
OLD_VERSION=$(grep -o -E "Strategy V[0-9]+" /root/GEMINI.md | head -n 1)

# Backup files to persistent directory (not /tmp which gets wiped)
for f in bot.py portfolio_backtester.py GEMINI.md config.json restricted_pairs.json; do
    if [ -s "/root/$f" ]; then
        cp "/root/$f" "$BACKUP_DIR/$f.bak"
    fi
done

# Initialize opinion file
echo "AI analysis failed." > /root/daily_opinion.html

echo "[$(date)] Running daily strategic analysis..." >> /root/strategy_evolver.log

# Run agy with a 30-minute timeout and Gemini 3.1 Pro (High) model
if agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 30m0s --print "$PROMPT"; then
    echo "AI agent run completed."
    EVOLUTION_SUCCESS=true
else
    echo "CRITICAL: Antigravity CLI agent run failed!"
    echo "AI analysis failed." > /root/daily_opinion.html
    EVOLUTION_SUCCESS=false
fi

NEW_VERSION=$(grep -o -E "Strategy V[0-9]+" /root/GEMINI.md | head -n 1)

FILES_CHANGED=false
if ! cmp -s /root/bot.py "$BACKUP_DIR/bot.py.bak" || \
   ! cmp -s /root/portfolio_backtester.py "$BACKUP_DIR/portfolio_backtester.py.bak" || \
   ! cmp -s /root/config.json "$BACKUP_DIR/config.json.bak" || \
   ! cmp -s /root/GEMINI.md "$BACKUP_DIR/GEMINI.md.bak" || \
   ! cmp -s /root/restricted_pairs.json "$BACKUP_DIR/restricted_pairs.json.bak"; then
    FILES_CHANGED=true
fi

if [ "$EVOLUTION_SUCCESS" = true ]; then
    if [ "$FILES_CHANGED" = true ]; then
        echo "Changes detected in workspace. Verifying system health..."
        if /root/venv/bin/python /root/verify_system.py; then
            echo "Syntax verification passed. Running quick backtest validation..."
            
            # GUARDRAIL: Run a quick backtest to ensure new code is profitable
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

result = asyncio.run(quick_test())
" 2>/dev/null | tail -1)
            
            echo "Quick backtest result: ${BACKTEST_RESULT}%"
            
            # Only deploy if backtest is positive (or at least not terrible)
            PASSES_BACKTEST=$(python3 -c "print('yes' if float('${BACKTEST_RESULT:-"-999"}') > -1.0 else 'no')" 2>/dev/null)
            
            if [ "$PASSES_BACKTEST" = "yes" ]; then
                echo "Backtest gate PASSED (${BACKTEST_RESULT}%). Deploying changes..."
                echo "[$(date)] Strategy Evolved Successfully ($OLD_VERSION -> $NEW_VERSION). Backtest: ${BACKTEST_RESULT}%" >> /root/strategy_evolver.log
            
                OLD_PID=$(systemctl show --property=MainPID trading-bot 2>/dev/null | cut -d= -f2)
                systemctl restart trading-bot
                systemctl restart backtest-optimizer
            
                # Post-restart health check
                echo "Waiting 10 seconds to verify post-restart service health..."
                sleep 10
                NEW_PID=$(systemctl show --property=MainPID trading-bot 2>/dev/null | cut -d= -f2)
            
                if [ -z "$NEW_PID" ] || [ "$NEW_PID" = "0" ] || [ "$OLD_PID" = "$NEW_PID" ] || ! systemctl is-active --quiet trading-bot; then
                    echo "CRITICAL: Bot service failed post-restart check or did not restart! Rolling back..."
                    perform_rollback
                    EVOLUTION_SUCCESS=false
                else
                    echo "Post-restart health check passed. Bot is active and running (PID: $NEW_PID)."
                fi
            else
                echo "Backtest gate FAILED (${BACKTEST_RESULT}%). Code change rejected - rolling back..."
                echo "[$(date)] Strategy evolution REJECTED by backtest gate (score: ${BACKTEST_RESULT}%)." >> /root/strategy_evolver.log
                perform_rollback
                EVOLUTION_SUCCESS=false
            fi
        else
            echo "CRITICAL: System verification failed after AI execution! Rolling back changes..."
            perform_rollback
            EVOLUTION_SUCCESS=false
        fi
    else
        echo "No changes made to workspace. Strategy remains at $OLD_VERSION."
        echo "[$(date)] Strategy unchanged (Strategic analysis completed)." >> /root/strategy_evolver.log
    fi
else
    echo "CRITICAL: Antigravity CLI strategic analysis failed! Rolling back any partial changes..." >> /root/strategy_evolver.log
    perform_rollback
fi

# Run system cleanup script to remove obsolete scratch/test files
echo "Running system cleanup..."
/root/venv/bin/python /root/cleanup_system.py

# Check if we should skip sending the email report
SKIP_EMAIL=false
for arg in "$@"; do
    if [ "$arg" == "--skip-email" ]; then
        SKIP_EMAIL=true
    fi
done

if [ "$SKIP_EMAIL" = false ]; then
    # Always send the daily report at the end
    echo "Sending daily report..."
    /root/venv/bin/python /root/send_daily_report.py >> /root/email_report.log 2>&1
else
    echo "Skipping email report (--skip-email flag detected)."
fi
