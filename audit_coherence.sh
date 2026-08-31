#!/bin/bash
# Logic Coherence & Alignment Meta-Auditor
export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root

echo "Gathering system files for coherence audit & auto-heal..."

PROMPT=$(cat <<'PROMPT_EOF'
You are the Lead Quantitative Auditor.
Your job is to audit this autonomous trading system for overall logic coherence and alignment between the live bot, the backtester, and the dashboard UI.

Carefully review the entire codebase for any hidden discrepancies, unhandled edge cases, lookahead bias, state persistence issues, or logical flaws. Do not constrain yourself to a specific checklist—you have full autonomy to find and fix any inconsistency that could cause the live bot to behave differently than the backtester, or any logic that simply doesn't make sense.

Crucially, you must also verify that the UI dashboards (dashboard.py, forecast_dashboard.py, view_blacklist.py, backtest_dashboard.py) and the bolero.py menu wrapper are fully coherent with the current strategy approach. Ensure that the dashboards accurately pull, calculate, and display the exact indicators and data used by the live bot. If the strategy logic changed, you MUST update the dashboard scripts to reflect those changes and ensure they work logically without syntax errors or outdated variables.

INSTRUCTIONS:
You have full access to the file system. YOU MUST USE YOUR tools to EDIT AND FIX ANY FILES that contain discrepancies.
If no issues are found, do not edit anything.
Once you have finished, write a clean summary of what you analyzed and repaired (if anything) to /root/coherence_report.md.
PROMPT_EOF
)

for f in *.py GEMINI.md; do
    if [ -f "/root/$f" ]; then
        PROMPT="$PROMPT

=== $f ===
$(cat /root/$f)
"
    fi
done

BACKUP_DIR="/root/backups"
perform_rollback() {
    echo "CRITICAL: Coherence Auditor broke the system! Rolling back..."
    for f in *.py GEMINI.md; do
        if [ -s "$BACKUP_DIR/$f.bak" ]; then
            cp "$BACKUP_DIR/$f.bak" "/root/$f"
        fi
    done
}

echo "Running AI Meta-Auditor & Auto-Healer (this will take a few minutes)..."
if agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 20m0s --print "$PROMPT" > /root/coherence_report.md; then
    echo "Coherence Audit and Auto-Heal complete! System logic is aligned."
else
    echo "Coherence Audit failed (Timeout or Error). Rolling back."
    perform_rollback
fi
