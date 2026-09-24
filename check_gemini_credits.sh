#!/bin/bash
# Gate script for systemd ExecCondition=.
# Queries agy's /usage command and exits:
#   0   -> sufficient Gemini credits, allow the service to run
#   1   -> insufficient credits (or usage says disabled/0%), skip the service
#
# systemd treats an ExecCondition exit code of 1..254 as "condition not met"
# and skips the unit WITHOUT marking it failed, leaving the timer intact.
#
# Threshold: minimum weekly-remaining percent required to run. Override via
# the MIN_PCT environment variable in the drop-in if desired.

set -u

export HOME="${HOME:-/root}"
export PATH="/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:${PATH:-}"
export GEMINI_CLI_TRUST_WORKSPACE=true

AGY="/root/.local/bin/agy"
MIN_PCT="${MIN_PCT:-10}"         # require at least this % remaining
LOG="/root/gemini_credit_gate.log"

log() { echo "$(date -Is) [$SERVICE_LABEL] $*" >> "$LOG"; }

SERVICE_LABEL="${1:-unknown}"

# Query usage (non-interactive). Guard with a timeout so a hung CLI can't stall.
OUT="$(timeout 90 "$AGY" --print "/usage" 2>/dev/null)"
RC=$?

if [ $RC -ne 0 ] || [ -z "$OUT" ]; then
    # Could not determine usage. Fail safe: SKIP so we don't burn a broken run.
    log "usage query failed (rc=$RC) -> SKIP"
    exit 1
fi

# Parse the "Gemini Models / Weekly Limit Remaining" row.
# Format is tab-separated: <group>\t<metric>\t<value>\t<reset-time>
RAW_PCT="$(printf '%s\n' "$OUT" \
    | awk -F'\t' '/^Gemini Models/ && /Weekly Limit Remaining/ { print $3; exit }')"

if [ -z "$RAW_PCT" ]; then
    log "could not parse Gemini weekly remaining from usage output -> SKIP. output was: $(printf '%s' "$OUT" | tr '\n' '|')"
    exit 1
fi

# "disabled" (no limit / unlimited) -> allow.
if printf '%s' "$RAW_PCT" | grep -qi 'disabled\|unlimited'; then
    log "weekly remaining reported '$RAW_PCT' -> RUN"
    exit 0
fi

# Strip a trailing % and any whitespace, keep integer part.
PCT="$(printf '%s' "$RAW_PCT" | tr -dc '0-9')"

if [ -z "$PCT" ]; then
    log "non-numeric remaining value '$RAW_PCT' -> SKIP"
    exit 1
fi

if [ "$PCT" -ge "$MIN_PCT" ] 2>/dev/null; then
    log "Gemini weekly remaining ${PCT}% >= ${MIN_PCT}% -> RUN"
    exit 0
else
    log "Gemini weekly remaining ${PCT}% < ${MIN_PCT}% -> SKIP"
    exit 1
fi
