---
name: bolero-maintenance
description: Operational runbook, institutional knowledge base, and diagnostic procedures for maintaining, auditing, and evolving the Bolero Binance spot trading bot (Strategy V160). Use when auditing live trading performance, diagnosing fee drag or simulation drift, running stress tests, tuning parameters, or inspecting quantitative invariants.
metadata:
  icon: show_chart
---

# Bolero Trading Bot Operational Runbook & Maintenance Skill

This skill provides the comprehensive domain knowledge, architectural invariants, diagnostic runbooks, and autonomous multi-agent adversarial audit workflows for the autonomous Binance spot trading bot (Strategy V160).

---

## 1. Bolero Knowledge Base (What the Skill Knows About Bolero)

### 1.1 Identity & High-Level Mission
* **System Name:** Bolero (managed autonomously under the directive in [`/root/GEMINI.md`](file:///root/GEMINI.md)).
* **Exchange & Asset Class:** **Binance Spot exclusively** (USDT quote pairs). 
* **Zero Leverage / No Derivatives:** Bolero strictly trades spot assets—no margin borrowing, no perpetual contracts, no funding rates, and no liquidation risk.
* **Core Trading Philosophy:** Continuous market exposure and aggressive capital rotation. Bolero targets altcoins displaying relative strength (decoupling) and volume anomalies while Bitcoin consolidates. Capital is never left 100% idle in cash, nor held indefinitely in stagnant chop.

### 1.2 Active Strategy: V160 ("Volatile Momentum & Decoupling Squeeze")
* **Primary Entry Setup:** Decoupled squeeze breakout targeting altcoins breaking out with expanding Bollinger Bands while BTC consolidates.
  * **BTC Regime Filter:** BTC 4h Rate-of-Change (ROC) between `-3.0%` and `+1.0%`.
  * **Relative Strength Filter:** Altcoin 4h ROC > (BTC 4h ROC + 3.0%).
  * **Volume Anomaly:** Altcoin RVOL > 1.5x (current hour volume vs. 24h rolling average).
  * **Breakout Trigger:** Price closes outside the upper Bollinger Band with expanding bands.
  * **Macro Risk Scaling:** 
    * `1.0x` if BTC 24h return $\ge -1.0\%$
    * `0.8x` if BTC 24h return between `-3.0%` and `-1.0%`
    * `0.5x` if BTC 24h return $\le -3.0\%$
* **Exit Architecture:**
  * **Profit-Activated Trailing Stop:** Wide initial stop (`-6.0%` to `-7.0%`); trailing stop (`-3.5%`) activates only after establishing a profit cushion (`+6.0%` to `+8.0%`).
  * **Time-Decay Momentum Check:** Trades held $>48\text{h}$ must maintain positive 24h momentum and healthy volume, or face graceful liquidation for capital rotation.
  * **Dynamic Drawdown Floor:** Structural `-7.0%` absolute floor specifically enforced on extended trades ($>24\text{h}$).
  * **Portfolio Guard:** Global Eject at `PORTFOLIO_EJECT%` (e.g. `-5.0%`), Global Harvest at `PORTFOLIO_HARVEST%` (e.g. `+4.0%`).
  * **Circuit Breaker:** 4-hour entry pause triggered if 1-hour portfolio drawdown exceeds `3.5%` or if $>3$ execution losses occur within 1 hour.

### 1.3 Infrastructure & Tech Stack
* **Host Environment:** Ubuntu Linux VPS (`vultr`).
* **Python Runtime:** Python 3.12 in dedicated virtual environment at `/root/venv`.
* **System Services (`systemd`):**
  * `trading-bot.service`: Continuous execution engine running [`/root/bot.py`](file:///root/bot.py).
  * `backtest-optimizer.service`: Continuous Optuna hyperparameter tuner running [`/root/tuner.py`](file:///root/tuner.py).
* **Scheduled Tasks & Governance:**
  * **Hourly AI Manager (`cron`):** [`ai_manager.py`](file:///root/ai_manager.py) analyzes market sentiment, publishes tactical multipliers to [`tactical_overrides.json`](file:///root/tactical_overrides.json), and identifies narrative candidates.
  * **Nightly Committee (03:00 UTC `cron`):** [`nightly_committee.sh`](file:///root/nightly_committee.sh) convenes an autonomous multi-role AI board (Price Analyst, Risk Officer, Architect, Strategy Designer) to audit daily performance, run stress tests, and evolve parameters.
* **Data & State Persistence:**
  * [`/root/trading_bot.db`](file:///root/trading_bot.db): SQLite database with WAL journal mode storing execution history (`trades`, `failed_trades`, `daily_pnl`).
  * [`/root/config.json`](file:///root/config.json): Core parameter matrix (stops, profit targets, sizing, indicators).
  * [`/root/active_positions.json`](file:///root/active_positions.json): Real-time in-memory position state mirror.
  * [`/root/restricted_pairs.json`](file:///root/restricted_pairs.json): Dynamically quarantined chronic underperforming coins.
  * [`/root/.backtester_cache/*.pkl`](file:///root/.backtester_cache/): Multi-day 1m/15m OHLCV cache for fast backtest execution.

### 1.4 Historical Sensitivities & Known Operational Traps
* **Fee Churn Vulnerability:** Binance charges 0.10% each side (0.20% round-trip). Rapid high-frequency cycling in choppy markets can generate positive gross returns while burning net cash in fees.
* **Circuit Breaker False Tripping:** Over-tight thresholds (e.g. 1.0%) trigger 20+ times a week on standard altcoin beta noise, locking the bot in 100% cash during explosive momentum runs.
* **Wallet Dust Accumulation:** Sub-dollar leftovers from fractional fills must be filtered out with a `$4.00` minimum notional threshold during balance sync to avoid blocking valid risk slots.
* **Chronic Bleeder Coins:** Certain illiquid or downward-trending pairs bleed consistently; they must be actively identified and quarantined via [`reflect.py --auto-heal`](file:///root/reflect.py).

---

## 2. Mission & Purpose: How This Skill Helps

This skill serves as the **authoritative operational anchor, institutional memory, and quantitative guardian** for any AI agent working on the Bolero codebase.

### Core Assistance Capabilities:

1. **Enforcing Invariant Boundaries & Preventing Regressions:**
   * Prevents agents from altering backtest fill physics, un-clamping stop losses, or reintroducing phantom profit-lock bugs that report false backtest wins.
   * Enforces hard position sizing ceilings (`MAX_RISK <= 20%`, `BASE_RISK <= 2.5%`) to prevent single-coin blowups.

2. **Providing Grounded Diagnostics (The Anti-Sycophancy Filter):**
   * Keeps agents strictly focused on real, solvable spot execution problems (fee drag, circuit breaker lockouts, uncalibrated sizing, bleeder pairs).
   * Explicitly blocks future agents from proposing irrelevant institutional derivatives complexity (perpetual funding rates, order-book depth) when diagnosing spot strategy issues.

3. **Autonomous Auto-Healing & Post-Trade Reflection:**
   * Directs agents to run [`reflect.py --auto-heal`](file:///root/reflect.py) to perform FIFO trade matching with net fees, identify capital leaks, and quarantine chronic bleeding coins without needing human intervention.

4. **Multi-Agent Adversarial Auditing (`/goal` Mode):**
   * Provides a structured procedure to spawn specialized adversarial subagents (Invariant Exploiter, Execution Breaker, Governance Saboteur) to stress-test the entire codebase, discover edge cases, and maintain an active hardening backlog.

5. **Standardized Pre-Flight Verification:**
   * Provides a turnkey 7-step test suite ([`verify_system.py`](file:///root/verify_system.py)) and mathematical invariant firewall ([`audit_invariants.py`](file:///root/audit_invariants.py)) that must pass 100% before any code change or parameter update is committed.

---

## 3. System Architecture & Component Roles

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

## 4. The Non-Negotiable Invariant Laws

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

## 5. Standard Operating Procedures (SOP)

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

## 6. Diagnostic Playbook

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

---

## 7. Adversarial Multi-Agent Audit Runbook (/goal Mode)

Going forward, this skill is designed to autonomously review the entire codebase and identify architectural vulnerabilities, execution leaks, and quant simulation drift by spawning **three specialized adversarial subagents** in `/goal` mode.

### 1. The Adversarial Squad Architecture

When triggered, the coordinator agent invokes three concurrent adversarial subagents:

1. **`adversarial_invariant_auditor` (Invariant & Physics Exploiter):**
   * **Domain:** [`portfolio_backtester.py`](file:///root/portfolio_backtester.py), [`tuner.py`](file:///root/tuner.py), [`audit_invariants.py`](file:///root/audit_invariants.py), [`run_quick_validation.py`](file:///root/run_quick_validation.py).
   * **Attack Targets:** Lookahead bias (e.g. `.bfill()` on hourly indicators), round-trip fee undercounting (ignoring 0.20% fees in trade PnL), optimistic stop-loss fills during gap-downs, and Optuna objective gaming (favoring 0-trade or extreme-tail-risk parameter spaces).

2. **`adversarial_execution_auditor` (Live Execution & Risk Breaker):**
   * **Domain:** [`bot.py`](file:///root/bot.py), [`trading_utils.py`](file:///root/trading_utils.py), [`config.json`](file:///root/config.json).
   * **Attack Targets:** Binance API edge cases (misclassifying `-2010` insufficient balance as symbol restrictions), partial fills abandoning remaining inventory, infinite sell loops on `-1013` filter rejects, 24h WebSocket drop terminations, and circuit breaker bypasses when all positions close.

3. **`adversarial_governance_auditor` (Governance & Concurrency Saboteur):**
   * **Domain:** [`nightly_committee.sh`](file:///root/nightly_committee.sh), [`reflect.py`](file:///root/reflect.py), [`ai_manager.py`](file:///root/ai_manager.py), [`system_health.py`](file:///root/system_health.py), SQLite DB and JSON configs.
   * **Attack Targets:** Non-atomic config writes (`config.json` read/write race conditions causing `JSONDecodeError`), SQLite lock contention (`database is locked`), AI Manager hallucinated symbol bypasses (`test_symbol_permission` returning True), omission of pre-flight invariant gates in nightly committee, and fee asset conversion blindspots (BNB fees vs USDT).

---

### 2. Master Adversarial Audit Findings & Remediation Backlog

The following backlog was uncovered by the initial adversarial audit run and represents the active hardening targets:

| Priority | Area | Issue & Vulnerability | Affected Files & Lines | Actionable Remediation |
| :---: | :--- | :--- | :--- | :--- |
| **P0** | **Live Bot** | `self.market_trend` dict overwrite wipes `btc_daily_range_pct`, causing `relative_range` to always default to 1.0 in live trading and falsely triggering altcoin decoupling beta on every coin. | [`bot.py:405-410`](file:///root/bot.py#L405-L410) | Replace reassignment with `self.market_trend.update({...})` to preserve 24h range metrics. |
| **P0** | **Live Bot** | Circuit breaker bypassed on position closure: `check_portfolio_guard()` returns early if `not active`, failing to record equity or calculate drawdown when positions hit stop loss. | [`bot.py:687-722`](file:///root/bot.py#L687-L722) | Remove `if not active: return` before equity logging; calculate drawdown from peak-to-trough over the 1-hour window. |
| **P0** | **Live Bot** | Binance error `-2010` (insufficient balance) caught under symbol ban filter, permanently blacklisting valid pairs in `restricted_pairs.json` and wiping sell tracking. | [`bot.py:971-978`](file:///root/bot.py#L971-L978) | Decouple `-2010` from symbol restriction blacklist; retain position tracking on failed sell. |
| **P0** | **Governance** | `nightly_committee.sh` Phase 4 never runs [`audit_invariants.py`](file:///root/audit_invariants.py), allowing unverified or illegal parameter/physics changes to deploy without invariant verification. | [`nightly_committee.sh:296-335`](file:///root/nightly_committee.sh#L296-L335) | Insert `/root/venv/bin/python /root/audit_invariants.py` into verification gate alongside `verify_system.py`. |
| **P0** | **Reflection** | Fee currency blindness: treats BNB fees (e.g. 0.0003 BNB) as USD value ($0.0003), undercounting real fee drag by ~600x. | [`reflect.py:40,74`](file:///root/reflect.py#L40) | Convert non-USDT fees to USD value using current token/BNB price. |
| **P1** | **Backtest** | Lookahead bias in `portfolio_backtester.py`: `.bfill()` on resampled 1h indicators backpropagates future 50h EMA and ATR into the first 250 minutes. | [`portfolio_backtester.py:99-110`](file:///root/portfolio_backtester.py#L99-L110) | Remove all `.bfill()` calls; require a 50-hour warmup before entries. |
| **P1** | **Backtest** | Trade `pnl` ignores 0.20% round-trip Binance fees, misclassifying fee-loss churn as wins and preventing circuit breaker trips in backtests. | [`portfolio_backtester.py:285-290`](file:///root/portfolio_backtester.py#L285-L290), [`388`](file:///root/portfolio_backtester.py#L388) | Compute net PnL after round-trip fees; harmonize EOD fee to 0.10%. |
| **P1** | **Live Bot** | Partial fills on SELL unconditionally reset `entries: 0, qty: 0.0`, abandoning remaining unsold assets without stop protection. | [`bot.py:909-952`](file:///root/bot.py#L909-L952) | Deduct executed quantity from `pos['qty']` on partial fills and retain position monitoring. |
| **P1** | **Live Bot** | `test_symbol_permission()` returns `True` on `-1121 Invalid symbol`, allowing LLM hallucinations in `whitelist_add` to infiltrate `tracked_pairs.json`. | [`bot.py:363-375`](file:///root/bot.py#L363-L375) | Enforce strict validation: return `False` on any exception from `create_test_order` unless error is explicitly insufficient balance. |
| **P1** | **Concurrency** | Non-atomic write to `config.json` in `tuner.py` and `reflect.py` causes `JSONDecodeError` during periodic reload in `bot.py`. | [`tuner.py:47`](file:///root/tuner.py#L47), [`reflect.py:293`](file:///root/reflect.py#L293) | Standardize all JSON config writes with PID-scoped atomic file replacements (`atomic_json_dump`). |
| **P2** | **Optimizer** | Optuna objective in `tuner.py` rewards low trade counts (e.g. 1 lucky trade) and tight TP + 8x ATR stops (high win rate with severe tail risk). | [`tuner.py:279-327`](file:///root/tuner.py#L279-L327) | Implement Calmar/Sortino ratio objective with minimum trade count threshold ($N \ge 20$). |
| **P2** | **Auditor** | Naive 5-day drift window in `audit_invariants.py` causes boundary distortion (counting open buys as 100% losses). | [`audit_invariants.py:118-135`](file:///root/audit_invariants.py#L118-L135) | Integrate FIFO trade matching from `reflect.py` for live vs simulation drift auditing. |
