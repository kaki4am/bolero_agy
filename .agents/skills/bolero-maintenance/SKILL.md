---
name: bolero-maintenance
description: Operational runbook and diagnostic procedures for maintaining, auditing, and evolving the Bolero Binance spot trading bot (Strategy V160). Use when auditing live trading performance, diagnosing fee drag or simulation drift, running stress tests, tuning parameters, or inspecting quantitative invariants.
metadata:
  icon: show_chart
---

# Bolero Trading Bot Operational Runbook & Maintenance Skill

This skill provides the standard operating procedures, architectural invariants, and diagnostic runbooks for the autonomous Binance spot trading bot (Strategy V160).

---

## 1. System Architecture & Component Roles

The system is organized into decoupled layers:

| Component | File / Service | Role & Cadence | Invariant Boundary |
| :--- | :--- | :--- | :--- |
| **Execution Bot** | `bot.py` (`trading-bot.service`) | Real-time spot execution on Binance (1m/15m klines). | Strictly loads config from `config.json` and excludes pairs in `restricted_pairs.json`. |
| **Tactical Manager** | `ai_manager.py` (Hourly daemon) | Market regime monitoring, narrative coin whitelisting, intraday risk scaling. | Adjusts tactical multipliers; does NOT modify core code. |
| **Reflection Engine** | `reflect.py` | FIFO trade matching with net fees, leak detection, autonomous quarantine. | Auto-populates `restricted_pairs.json` with chronic bleeders. |
| **Invariant Firewall** | `audit_invariants.py` | Mathematical & dynamic forensic auditor. Pre-deployment gate. | Must pass 100% with 0 errors before any code or config can deploy. |
| **Optimizer** | `tuner.py` (`backtest-optimizer.service`) | Continuous Optuna hyperparameter optimization. | Search space bounded; cannot suggest >20% position allocation. |
| **Nightly Committee** | `nightly_committee.sh` (03:00 UTC) | Autonomous quant research, parameter tuning, strategy evolution. | Strictly forbidden from altering fill pricing or slippage math. |

---

## 2. The Non-Negotiable Invariant Laws

Any agent working on this repository MUST preserve these core quantitative invariants:

1. **Immutable Backtest Physics Engine:**
   - In [`portfolio_backtester.py`](file:///root/portfolio_backtester.py), stop-loss fills must always be clamped to market reality:
     `exit_price = min(old_sl, price) * (1.0 - slippage_pct)`
   - Profit locks must NEVER trigger on losing trades:
     `if current_profit_pct >= params.get('PROFIT_LOCK_PCT', 0.005):`
   - Slippage and Binance spot fees (0.10% each side) must always be accounted for.

2. **Position Sizing & Risk Ceilings (Anti-Gambler's Ruin):**
   - `MAX_RISK_PER_TRADE_PERCENT <= 20.0%` (Configured at 18.0%).
   - `BASE_RISK_PERCENT <= 2.5%` (Configured at 1.5%).
   - The bot must never concentrate >20% of account equity in a single altcoin. This ensures the portfolio can comfortably hold 5 concurrent positions, maximizing capital rotation and surviving single-coin wicks.

3. **Autonomous Rotation Mandate:**
   - The bot must maintain active market exposure and rotate capital into fresh high-conviction breakout setups rather than sitting in 100% cash or holding dead chop.

---

## 3. Standard Operating Procedures (SOP)

### SOP 1: Health & Performance Audit
To evaluate current portfolio status and live execution health:
```bash
# 1. Check live systemd services
systemctl status trading-bot.service backtest-optimizer.service --no-pager

# 2. Check realized 30-day PnL, fee burn, and active positions
/root/venv/bin/python /root/system_health.py
/root/venv/bin/python /root/export_report.py
```

### SOP 2: Run Strategic Reflection & Auto-Healing
To diagnose capital leaks (fee churn, chronic bleeding coins, premature exits) and auto-quarantine underperforming pairs:
```bash
/root/venv/bin/python /root/reflect.py --auto-heal
```
- Inspect outputs: [`reflection_autopsy.json`](file:///root/reflection_autopsy.json) and [`reflection_autopsy.md`](file:///root/reflection_autopsy.md).
- Quarantined coins are dynamically appended to [`restricted_pairs.json`](file:///root/restricted_pairs.json).

### SOP 3: Pre-Deployment Invariant Audit
Run this before staging any git changes or adopting new parameters:
```bash
/root/venv/bin/python /root/audit_invariants.py
```
Checks:
- Config risk limits (`MAX_RISK <= 20%`, `BASE_RISK <= 2.5%`).
- Mathematical code assertions (SL fill clamping, guarded profit locks).
- Dynamic backtest forensic inspection (zero phantom fills across all simulated trades).
- Live-to-simulation drift auditor (flags if backtest claims unrealistic profits vs live PnL).

### SOP 4: Full System Verification Suite
Run the 7-step pre-flight verification:
```bash
/root/venv/bin/python /root/verify_system.py
```
Validates:
1. Syntax check across all Python files.
2. Bot logic dry-run with tactical overrides.
3. Backtester smoke tests across Optuna search space.
4. Monitoring script execution.
5. Strategy version consistency (`GEMINI.md`, `bot.py`).
6. Historical stress testing across 4 crisis regimes (COVID, FTX, Leverage Flush, Random Walk) using legacy altcoins (`BNBUSDT`, `ADAUSDT`, `LINKUSDT`).
7. Pyflakes & Vulture dead-code / lint inspection.

---

## 4. Diagnostic Playbook

### Issue A: High Binance Fee Drag
- **Symptom:** Gross PnL is positive, but net PnL is negative due to high fees.
- **Remedy:** Trade churn is too high.
  1. Increase `VOL_THRESHOLD` in [`config.json`](file:///root/config.json) (e.g. from 1.5 to 1.8) to require stronger volume anomalies.
  2. Increase `TAKE_PROFIT` or `TRAILING_TRIGGER` to ensure winners cover round-trip fees.
  3. Increase `COOLDOWN_PERIOD` to prevent immediate re-entry into chop.

### Issue B: Chronic Bleeding Coins
- **Symptom:** A specific coin has >= 3 trades with zero wins and heavy losses.
- **Remedy:** Run `/root/venv/bin/python /root/reflect.py --auto-heal`. This automatically adds the pair to [`restricted_pairs.json`](file:///root/restricted_pairs.json), which `bot.py` reloads dynamically without requiring a restart.

### Issue C: Simulation vs. Live Drift
- **Symptom:** Backtester reports +15% but live portfolio equity is dropping.
- **Remedy:** Run `audit_invariants.py`. Check if the backtester has phantom profit exits or if slippage/fees are mismatched. Confirm live positions are not suffering from low liquidity or wide bid-ask spreads.
