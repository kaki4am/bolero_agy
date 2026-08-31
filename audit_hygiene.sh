#!/bin/bash
# System Hygiene & Performance Meta-Auditor
# Scans python code to actively remove dead code, unused indicators, and performance leaks.

export PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root

echo "Gathering system files for performance & hygiene audit..."

PROMPT=$(cat <<'PROMPT_EOF'
You are the Lead Quantitative Performance Engineer.
Your job is to audit this autonomous trading system for "dead code", "performance leaks", and "directory hygiene", and ACTIVELY REPAIR any flaws you find.

Checklist for Audit & Repair:
1. Dead Indicator Math: Scan the entry/exit logic in bot.py and portfolio_backtester.py. Identify EXACTLY which indicators are actually used in the IF statements. Any indicator that is calculated but NOT used in the trading logic (e.g., leftover MACD, ADX, SMA from old strategies) MUST BE DELETED from `calc_indicators` and `portfolio_backtester.py` to save CPU cycles.
2. Unused Variables & Imports: Remove any unused python imports or orphan variables.
3. Clean Code: Ensure there are no unused loops or redundant database calls.

INSTRUCTIONS:
You have full access to the file system. YOU MUST USE YOUR tools (like `replace_file_content`) TO EDIT AND FIX ANY FILES that contain performance leaks or dead code. 
Once you have applied all fixes, write a clean summary of what you repaired and why to /root/hygiene_report.md.
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
    echo "CRITICAL: Hygiene Auditor broke the system! Rolling back..."
    for f in *.py GEMINI.md; do
        if [ -s "$BACKUP_DIR/$f.bak" ]; then
            cp "$BACKUP_DIR/$f.bak" "/root/$f"
        fi
    done
}

echo "Running Hygiene Auditor (this will take a few minutes)..."
if agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 20m0s --print "$PROMPT" > /root/hygiene_report.md; then
    echo "Running post-audit syntax verification..."
    
    VERIFY_PASSED=false
    for ATTEMPT in 1 2 3; do
        VERIFY_OUTPUT=$(/root/venv/bin/python /root/verify_system.py 2>&1)
        VERIFY_EXIT=$?
        
        if [ $VERIFY_EXIT -eq 0 ]; then
            VERIFY_PASSED=true
            echo "Verification passed on attempt $ATTEMPT."
            break
        else
            echo "Verification FAILED (attempt $ATTEMPT/3). Errors:"
            echo "$VERIFY_OUTPUT" | grep -E "FAIL|Error|error" | head -30
            
            if [ $ATTEMPT -lt 3 ]; then
                echo "Asking AI to fix the errors..."
                FIX_PROMPT="The code you just cleaned failed verification. Fix these syntax errors and try again. Do NOT explain, just fix the files:

$VERIFY_OUTPUT"
                if ! agy --model "Gemini 3.1 Pro (High)" --dangerously-skip-permissions --print-timeout 5m0s --print "$FIX_PROMPT"; then
                    echo "AI fix attempt failed. Giving up."
                    break
                fi
            fi
        fi
    done

    if [ "$VERIFY_PASSED" = true ]; then
        echo "Hygiene Audit and Auto-Heal complete! System is healthy."
    else
        echo "Verification failed after 3 attempts. Rolling back."
        perform_rollback
    fi
else
    echo "Performance Audit failed."
    perform_rollback
fi
