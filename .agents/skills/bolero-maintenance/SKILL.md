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

The architecture uses a **two-tier autonomous governance model** coupled with hard mathematical and execution firewalls:

| Component | File / Service | Role & Cadence | Invariant Boundary |
| :--- | :--- | :--- | :--- |
| **Execution Bot** | `bot.py` (`trading-bot.service`) | Real-time spot execution on Binance (1m/15m klines). | Enforces 3.5% circuit breaker, dynamic sizing <=18%, filters dust (<$4), and drops restricted pairs. |
| **Tactical Manager (Tier 1)** | `ai_manager.py` (Hourly daemon) | Market regime monitoring, narrative coin whitelisting, intraday risk scaling. | Adjusts tactical multipliers; does NOT modify core execution code. |
| **Reflection Engine (Tier 2 Pre-flight)** | `reflect.py` | FIFO trade matching with net fees, leak detection, autonomous quarantine. | Auto-populates `restricted_pairs.json` with chronic bleeders before committee meetings. |
| **Nightly Committee (Tier 2 Board)** | `nightly_committee.sh` (03:00 UTC) | Autonomous quant research, parameter tuning, strategy evolution. | Strictly forbidden from altering fill pricing or slippage math; consumes verified baseline performance. |
| **Optimizer** | `tuner.py` (`backtest-optimizer.service`) | Continuous Optuna hyperparameter optimization. | Search space bounded (`MAX_RISK <= 20%`); writes cache atomically to prevent race conditions. |
| **Invariant Firewall** | `audit_invariants.py` | Mathematical & dynamic forensic auditor. Pre-deployment gate. | Must pass 100% with 0 errors before any code or config can deploy. |

> [!IMPORTANT]
> **Two-Tier Architecture Sufficiency Principle:**
> The two-tier architecture (Hourly AI Manager + Nightly Committee) with hard mathematical firewalls is **fully sufficient** for Binance Spot Momentum (Strategy V160). 
> When diagnosing underperformance, agents must **never** succumb to the sycophancy trap of proposing complex theoretical derivatives infrastructure (perpetual funding rates, order-book depth, cross-venue basis arbitrage). Historical losses were caused by tangible execution bugs (oversensitive circuit breakers, fee blindness, unchecked sizing, phantom backtest fills)—not missing institutional derivatives tooling.

---

## 2. The Non-Negotiable Invariant Laws

Any agent working on this repository MUST preserve these core quantitative invariants:

### 1. Immutable Backtest Physics Engine
- In [`portfolio_backtester.py`](file:///root/portfolio_backtester.py), stop-loss fills must always be clamped to market reality:
  ```python
  exit_price = min(old_sl, price) * (1.0 - slippage_pct)
  ```
- Profit locks must NEVER trigger on losing trades:
  ```python
  if current_profit_pct >= params.get('PROFIT_LOCK_PCT', 0.005):
  ```
- Slippage and Binance spot fees (0.10% each side) must always be accounted for.

### 2. Position Sizing & Risk Ceilings (Anti-Gambler's Ruin)
- `MAX_RISK_PER_TRADE_PERCENT <= 20.0%` (Configured at 18.0%).
- `BASE_RISK_PERCENT <= 2.5%` (Configured at 1.5%).
- The bot must never concentrate >20% of account equity in a single altcoin. This guarantees the portfolio can comfortably hold 5–10 concurrent positions, maximizing capital rotation and surviving single-coin wicks.

### 3. Circuit Breaker Calibration (Anti-Paralysis Invariant)
- `CIRCUIT_BREAKER_1H_DD = 0.035` (3.5% 1-hour portfolio drawdown).
- **Hard Floor:** Threshold must remain between 3.0% and 5.0%. 
- An oversensitive circuit breaker (such as 1.0%) will trip on normal altcoin volatility, pausing the bot for 4 hours multiple times a day (e.g. 20 trips in 4 days) and causing catastrophic execution paralysis where the bot sits in 100% cash while breakouts occur.

### 4. Concurrency & Atomic Cache Integrity
- Multi-process cache files (notably `/root/.backtester_cache/*.pkl`) shared between `tuner.py`, `run_quick_validation.py`, and `nightly_committee.sh` must be written atomically:
  ```python
  temp_cache = f"{cache_file}.tmp.{os.getpid()}"
  with open(temp_cache, 'wb') as f:
      pickle.dump(cache_data, f)
  os.replace(temp_cache, cache_file)
  ```
- Direct non-atomic writes produce `EOFError: Ran out of input` crashes during concurrent reads.

### 5. Verified Quant Baseline Invariant
- The Nightly Committee must never run against empty or failing baseline metrics (`AttributeError: fetch_data`).
- Baseline metrics must be pulled directly from [`run_quick_validation.py --baseline`](file:///root/run_quick_validation.py) to supply the Price Analyst with verified reality before any strategy changes are evaluated.

### 6. Minimum Notional & Dust Immunity
- Position tracking in [`bot.py`](file:///root/bot.py) must enforce a minimum notional threshold (`MIN_NOTIONAL = $4.00`) when synchronizing open positions with the Binance account balance.
- Sub-dollar residual dust (satoshis) must never be tracked as active risk positions.

---

## 3. Standard Operating Procedures (SOP)

### SOP 1: Health & Performance Audit
To evaluate current portfolio status, circuit breaker liveness, and execution health:
```bash
# 1. Check live systemd services
systemctl status trading-bot.service backtest-optimizer.service --no-pager

# 2. Check realized 30-day PnL, fee burn, and active positions
/root/venv/bin/python /root/system_health.py
/root/venv/bin/python /root/export_report.py

# 3. Check circuit breaker state and recent logs
journalctl -u trading-bot.service -n 50 --no-pager | grep -i "circuit breaker"
```

### SOP 2: Run Strategic Reflection & Auto-Healing
To diagnose capital leaks (fee churn, chronic bleeding coins, premature exits) and auto-quarantine underperforming pairs:
```bash
/root/venv/bin/python /root/reflect.py --auto-heal
```
- Inspect outputs: [`reflection_autopsy.json`](file:///root/reflection_autopsy.json) and [`reflection_autopsy.md`](file:///root/reflection_autopsy.md).
- Quarantined coins are dynamically appended to [`restricted_pairs.json`](file:///root/restricted_pairs.json) and reloaded dynamically by `bot.py`.

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

### Issue D: Execution Paralysis (False Circuit Breaker Trips)
- **Symptom:** Bot enters 0 trades for extended hours; journal logs show repeated `Circuit breaker active, pausing entries for 4 hours`.
- **Root Cause:** Intraday drawdown threshold is set too tight (<3.0%), treating normal market drift as a portfolio emergency.
- **Remedy:** Ensure `CIRCUIT_BREAKER_1H_DD` is calibrated to `0.035` (3.5%) in [`bot.py`](file:///root/bot.py), [`portfolio_backtester.py`](file:///root/portfolio_backtester.py), and [`tuner.py`](file:///root/tuner.py).

### Issue E: Pickle Cache `EOFError` Corruptions
- **Symptom:** Scripts crash with `_pickle.UnpicklingError: pickle data was truncated` or `EOFError`.
- **Root Cause:** A process (e.g. `tuner.py`) was writing to `.backtester_cache/` directly while another process was reading it.
- **Remedy:** Verify atomic write pattern is maintained across all cache update sites using PID temporary files and `os.replace()`. Remove any corrupted partial pickle files from `/root/.backtester_cache/`.

### Issue F: Phantom Dust Position Tracking
- **Symptom:** Bot reports tracking max positions (e.g. 5/5) but account equity is mostly idle in USDT; positions contain negligible amounts.
- **Root Cause:** Small residual balances left over from previous trades (< $1.00) being counted as active trades.
- **Remedy:** Confirm the `$4.00` minimum notional filter is present in `bot.py`'s position sync logic.
