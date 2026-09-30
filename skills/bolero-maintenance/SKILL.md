---
name: bolero-maintenance
description: Remote operational runbook, institutional knowledge base, and diagnostic procedures for maintaining, auditing, and managing the Bolero Binance spot trading bot (Strategy V160) on the remote Vultr VM over SSH. Use when auditing live trading performance, inspecting remote services, diagnosing fee drag or simulation drift, running stress tests, tuning parameters, or inspecting quantitative invariants.
metadata:
  icon: show_chart
---

# Bolero Trading Bot Operational Runbook & Remote Maintenance Skill

This skill provides the comprehensive domain knowledge, architectural invariants, diagnostic runbooks, and remote multi-agent audit workflows for the autonomous Binance spot trading bot (Strategy V160).

**Host & Execution Context:**
* **Remote Management (From Workstation `hoho`):** Commands are executed remotely over SSH via alias `bolero` (`ssh bolero "<command>"`), configured in `~/.ssh/config` using `~/.ssh/id_ed25519`.
* **Autonomous Local Daemons (On Vultr VM `vultr`):** Nightly committee, AI manager, and daily briefings run locally on the VM in `/root/` using the local python virtualenv `/root/venv/bin/python`.

---

## 1. Execution Standards (Remote vs. Local)

* **From Workstation (`hoho`):**
  ```bash
  # Remote command execution pattern:
  ssh bolero "<command>"

  # For interactive terminal dashboards (TTY required):
  ssh -t bolero "/root/venv/bin/python /root/bolero.py"

  # Copying logs or artifacts locally:
  scp bolero:/root/<file> /tmp/
  ```

* **Locally on VM (`vultr`):**
  Run commands directly in `/root/` using `/root/venv/bin/python`.

### Workstation SSH Configuration (`~/.ssh/config`)
```ssh-config
Host bolero
    HostName 209.222.30.211
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

---

## 2. Bolero Knowledge Base (What the Skill Knows About Bolero)

### 2.1 Identity & High-Level Mission
* **System Name:** Bolero (managed autonomously under the directive in `/root/GEMINI.md` on the VM).
* **Exchange & Asset Class:** **Binance Spot exclusively** (USDT quote pairs). 
* **Zero Leverage / No Derivatives:** Bolero strictly trades spot assets—no margin borrowing, no perpetual contracts, no funding rates, and no liquidation risk.
* **Core Trading Philosophy:** Continuous market exposure and aggressive capital rotation. Bolero targets altcoins displaying relative strength (decoupling) and volume anomalies while Bitcoin consolidates. Capital is never left 100% idle in cash, nor held indefinitely in stagnant chop.

### 2.2 Active Strategy: V160 ("Volatile Momentum & Decoupling Squeeze")
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

### 2.3 Remote Infrastructure & Tech Stack
* **Host Environment:** Ubuntu Linux VPS on Vultr (`209.222.30.211`).
* **Python Runtime:** Python 3.12 in dedicated virtual environment at `/root/venv`.
* **System Services (`systemd`):**
  * `trading-bot.service`: Continuous execution engine running `/root/bot.py`.
  * `backtest-optimizer.service`: Continuous Optuna hyperparameter tuner running `/root/tuner.py`.
* **Scheduled Tasks & Governance:**
  * **Hourly AI Manager (`cron`):** `/root/ai_manager.py` analyzes market sentiment, publishes tactical multipliers to `/root/tactical_overrides.json`, and identifies narrative candidates.
  * **Nightly Committee (03:00 UTC `cron`):** `/root/nightly_committee.sh` convenes an autonomous multi-role AI board (Price Analyst, Risk Officer, Architect, Strategy Designer) to audit daily performance, run stress tests, and evolve parameters.
* **Data & State Persistence:**
  * `/root/trading_bot.db`: SQLite database with WAL journal mode storing execution history (`trades`, `failed_trades`, `daily_pnl`).
  * `/root/config.json`: Core parameter matrix (stops, profit targets, sizing, indicators).
  * `/root/active_positions.json`: Real-time in-memory position state mirror.
  * `/root/restricted_pairs.json`: Dynamically quarantined chronic underperforming coins.
  * `/root/.backtester_cache/*.pkl`: Multi-day 1m/15m OHLCV cache for fast backtest execution.

### 2.4 Historical Sensitivities & Known Operational Traps
* **Fee Churn Vulnerability:** Binance charges 0.10% each side (0.20% round-trip). Rapid high-frequency cycling in choppy markets can generate positive gross returns while burning net cash in fees.
* **Circuit Breaker False Tripping:** Over-tight thresholds (e.g. 1.0%) trigger 20+ times a week on standard altcoin beta noise, locking the bot in 100% cash during explosive momentum runs.
* **Wallet Dust Accumulation:** Sub-dollar leftovers from fractional fills must be filtered out with a `$4.00` minimum notional threshold during balance sync to avoid blocking valid risk slots.
* **Chronic Bleeder Coins:** Certain illiquid or downward-trending pairs bleed consistently; they must be actively identified and quarantined via `reflect.py --auto-heal`.
* **Partial Scale-Out MinNotional Trap:** With account equity under $1,000 and 10–12 concurrent positions ($18–$25 each), selling 50% tranches leaves sub-$10 legs that quickly drop below Binance's `$5.00 minNotional` floor during pullbacks, throwing `-1013 Filter failure` on stop-losses and abandoning unsellable dust.
* **Dashboard Main-Thread Network Blocking:** Calling synchronous REST APIs (`client.get_account()`, `get_ticker()`, `get_historical_klines()`) or 6,500-trade FIFO replays inside the UI render loop freezes terminal screens for 3–8s and breaks keyboard responsiveness.
* **Heavy C-Extension Import Overhead under CPU Contention:** Under continuous hyperparameter tuning (Optuna pegged at 100% CPU), top-level imports of `pandas` and `binance.Client` in utility libraries incur a 5–7s cold-boot penalty on every script launch. Shared utility modules must lazily import these dependencies.
* **Dashboard Fee Accounting & Double-Deduction Trap:** In `/root/dashboard.py`, the `Realized PnL` column already deducts both buy-side and sell-side fees (`net_pnl = revenue - cost_basis - (buy_fee + fee)`). The adjacent `Fee` column is informational; deducting it again from `Realized PnL` constitutes erroneous double-counting.
* **Binance Daily Snapshot vs. Naive FIFO Replay Discrepancy:** Reconstructing historical equity curves by simply summing closed trade net PnL from `trading_bot.db` creates significant distortions (e.g. reporting a false $229 trough instead of the actual $291 floor). Naive trade summation omits floating mark-to-market valuations of active bags across date boundaries. The Binance Spot daily snapshot API (`client.get_account_snapshot(type='SPOT')`) is the authoritative source of truth for historical wallet equity and drawdowns.
* **LLM API Quota Exhaustion Failure Mode (The "Brain Freeze" Trap):** When Gemini API credits run out (`RESOURCE_EXHAUSTED 429`), the autonomous governance tier (Hourly AI Manager & Nightly Committee Architect) crashes silently. The execution bot continues running on stale parameters and unquarantined bleeding pairs without its risk officer.
* **The Volatility Cap Trade-off (`VOLATILITY_CAP`):** To prevent stop-out whipsaws in blown-out candles where hourly range exceeds the stop-loss distance (-6.85%), `bot.py:826` enforces `VOLATILITY_CAP = 0.025` (2.52% hourly ATR/Price). Once an altcoin goes parabolic (e.g. MOVR expanding to 5.5%–7.1% hourly ATR), this firewall deliberately blocks re-entry to prevent buying blow-off tops, catching only the initial squeeze breakout.
* **Strategy Version Lineage & Candidate Ghosting Trap (V160 vs V161/V162):** Strategy V160 is the battle-tested live version running in production. Strategy V161 was previously deployed on Sep 20, but rolled back after the mid-month drawdown to commit `bc10a69` (preserving database trade history). The Nightly Committee Architect frequently drafts next-generation candidates labeled V161 or V162 in `/tmp/architect_out.log` and `strategy_evolver.log`. If the candidate fails the automated backtest gate (e.g. 3.20% vs 3.34% baseline), it automatically rolls back. Operators seeing "V161" or "V162" in logs are seeing rejected or historical candidate runs, NOT live execution code.
* **Signal Messenger Markdown Asterisk Trap:** Signal Messenger clients do not parse standard markdown formatting asterisks (`*` or `**`) reliably, rendering them as literal clutter in the message body. Automated briefings sent via `signal-cli` must strip all markdown asterisks and rely on clean Unicode bullet points (`•`), emojis, and uppercase words for visual hierarchy.
* **Email Deprecation & Signal-Only Exclusivity Trap:** Email APIs, SMTP connections, and email credentials (`GMAIL_USER`, `GMAIL_PASS`) are strictly forbidden by fund owner mandate. All executive briefings, autopsies, and notifications must be delivered exclusively via Signal Messenger (`signal-cli`). Introducing email APIs, SMTP libraries, or storing mail credentials in `/root/.env` violates operational boundaries.
* **Cleaner Whitelist Omission Trap:** `/root/cleanup_system.py` automatically purges unwhitelisted files directly under `/root/`. Any new operational utility or governance script (such as `daily_signal_brief.py`, `link_signal.py`) must be registered immediately in `WHITELIST` in `cleanup_system.py` to prevent automated deletion during system maintenance.

---

## 3. Mission & Purpose: How This Skill Helps

This skill serves as the **authoritative operational anchor, institutional memory, and quantitative guardian** for any AI agent managing Bolero remotely from this machine.

### Core Assistance Capabilities:

1. **Enforcing Invariant Boundaries & Preventing Regressions:**
   * Prevents agents from altering backtest fill physics, un-clamping stop losses, or reintroducing phantom profit-lock bugs that report false backtest wins.
   * Enforces hard position sizing ceilings (`MAX_RISK <= 20%`, `BASE_RISK <= 2.5%`) to prevent single-coin blowups.

2. **Providing Grounded Diagnostics (The Anti-Sycophancy Filter):**
   * Keeps agents strictly focused on real, solvable spot execution problems (fee drag, circuit breaker lockouts, uncalibrated sizing, bleeder pairs).
   * Explicitly blocks future agents from proposing irrelevant institutional derivatives complexity (perpetual funding rates, order-book depth) when diagnosing spot strategy issues.

3. **Autonomous Auto-Healing & Post-Trade Reflection:**
   * Directs agents to run `ssh bolero "/root/venv/bin/python /root/reflect.py --auto-heal"` to perform FIFO trade matching with net fees, identify capital leaks, and quarantine chronic bleeding coins without needing human intervention.

4. **Multi-Agent Adversarial Auditing (`/goal` Mode):**
   * Provides a structured procedure to spawn specialized adversarial subagents (Invariant Exploiter, Execution Breaker, Governance Saboteur) to stress-test the entire codebase, discover edge cases, and maintain an active hardening backlog.

5. **Standardized Pre-Flight Verification:**
   * Provides a turnkey 7-step test suite (`verify_system.py`) and mathematical invariant firewall (`audit_invariants.py`) that must pass 100% before any code change or parameter update is committed.

---

## 4. System Architecture & Component Roles

The architecture uses a **two-tier autonomous governance model** coupled with hard mathematical and execution firewalls:

| Component | File / Service | Role & Cadence | Invariant Boundary |
| :--- | :--- | :--- | :--- |
| **Execution Bot** | `bot.py` (`trading-bot.service`) | Real-time spot execution on Binance (1m/15m klines). | Enforces 3.5% circuit breaker, dynamic sizing <=18%, filters dust (<$4), and drops restricted pairs. |
| **Tactical Manager (Tier 1)** | `ai_manager.py` (Hourly daemon) | Market regime monitoring, narrative coin whitelisting, intraday risk scaling. | Adjusts tactical multipliers; does NOT modify core execution code. |
| **Reflection Engine (Tier 2 Pre-flight)** | `reflect.py` | FIFO trade matching with net fees, leak detection, autonomous quarantine. | Auto-populates `restricted_pairs.json` with chronic bleeders before committee meetings. |
| **Nightly Committee (Tier 2 Board)** | `nightly_committee.sh` (03:00 UTC) | Autonomous quant research, parameter tuning, strategy evolution. | Strictly forbidden from altering fill pricing or slippage math; consumes verified baseline performance. |
| **Optimizer** | `tuner.py` (`backtest-optimizer.service`) | Continuous Optuna hyperparameter optimization. | Search space bounded (`MAX_RISK <= 20%`); writes cache atomically to prevent race conditions. |
| **Invariant Firewall** | `audit_invariants.py` | Mathematical & dynamic forensic auditor. Pre-deployment gate. | Must pass 100% with 0 errors before any code or config can deploy. |
| **Executive Daily Brief** | `daily_signal_brief.py` (`daily_signal_brief.timer` 08:00 UTC) | Automated multi-tier executive briefing to fund owner over Signal Messenger. | Synthesizes Binance live equity, 24h PnL, AI sentiment, and governance autopsies via `agy`; enforces asterisk-free typography. |

> [!IMPORTANT]
> **Two-Tier Architecture Sufficiency Principle:**
> The two-tier architecture (Hourly AI Manager + Nightly Committee) with hard mathematical firewalls is **fully sufficient** for Binance Spot Momentum (Strategy V160). 
> When diagnosing underperformance, agents must **never** succumb to the sycophancy trap of proposing complex theoretical derivatives infrastructure (perpetual funding rates, order-book depth, cross-venue basis arbitrage). Historical losses were caused by tangible execution bugs (oversensitive circuit breakers, fee blindness, unchecked sizing, phantom backtest fills)—not missing institutional derivatives tooling.

---

## 5. The Non-Negotiable Invariant Laws

Any agent working on this system MUST preserve these core quantitative invariants:

### 1. Immutable Backtest Physics Engine
- In `/root/portfolio_backtester.py`, stop-loss fills must always be clamped to market reality:
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
- Baseline metrics must be pulled directly from `run_quick_validation.py --baseline` to supply the Price Analyst with verified reality before any strategy changes are evaluated.

### 6. Minimum Notional & Dust Immunity
- Position tracking in `/root/bot.py` must enforce a minimum notional threshold (`MIN_NOTIONAL = $4.00`) when synchronizing open positions with the Binance account balance.
- Sub-dollar residual dust (satoshis) must never be tracked as active risk positions.

### 7. All-in / All-out Execution Invariant (Rejection of Partial Sells on Spot)
- Bolero trades spot with small position sizes ($18–$25 across 10–12 slots).
- Partial scale-out sells (e.g. 50% at TP1) are architecturally rejected:
  1. Splitting exits drops the second leg below Binance's `$5.00 minNotional` limit during pullbacks, causing `-1013 Filter failure` errors on stop-losses and abandoning unsellable dust.
  2. Momentum expectancy is driven by right-tail outliers (+20% to +40% runners like WLDUSDT); premature partial profit-taking cuts the gains of winners in half while losers take full-sized stop-losses.
  3. Holding half-positions violates the capital rotation mandate by locking risk slots in post-breakout chop. Downside protection must be handled exclusively via **Profit-Activated Trailing Stops** (+6% activation, -3.5% trail).

### 8. Asynchronous Decoupled UI & Non-Blocking Dashboard Invariant
- Terminal dashboards (`dashboard.py`, `positions_dashboard.py`) must NEVER execute synchronous network calls (Binance REST endpoints like `client.get_account()`, `get_ticker()`, or `get_historical_klines()`) or 6,500-trade FIFO replays on the main render loop.
- All account reconciliation, PnL calculations, ticker polling, and kline fetching must run exclusively in background daemon worker threads (`pnl_worker`, `positions_worker`) and persist atomically to disk caches (`.dashboard_cache.json`, `.positions_cache.json`).
- The UI thread must read only local thread-safe memory and indexed SQLite tables (`trades` order by id DESC) to guarantee frame 0 renders in `<15ms` and maintains sub-millisecond keyboard responsiveness (◀/▶ asset cycling, `TAB` view toggle).
- Heavy C-extensions (`pandas`, `binance.Client`) in shared libraries (`trading_utils.py`) must be lazily imported inside calling functions to prevent 5–7s cold-boot import penalties when the VPS CPU is under hyperparameter tuning load.
- Screen transitions in `bolero.py` must be executed in-process with bidirectional hotkey switching (`P`/`O` for Positions, `D` for Live Bot, `Q`/`ESC`/`M` for Main Menu), avoiding process spawn latency.

### 9. Strict Change-Gating Invariant (Anti-Hallucinated Execution)
- When a user prompt explicitly requests a review, audit, or report with instructions like *"do not change any code"* or *"audit only"*, agents and subagents are strictly forbidden from modifying files, altering configuration, or restarting `trading-bot.service`.

### 10. Dashboard Accounting & Net-of-Fees Invariant (Realized PnL vs. Fee Column)
- In the live trades table of `dashboard.py`, the `Realized PnL` column on closed (`SELL`) trades is calculated **net of all commissions** via `compute_sell_pnl()`:
  $$\text{Net PnL} = \text{Revenue} - \text{Cost Basis} - (\text{Buy Fee} + \text{Sell Fee})$$
- Both entry (buy) and exit (sell) commissions are already fully factored into the dollar and percentage PnL values.
- The adjacent `Fee` column displays the specific exchange commission charged by Binance on that order (e.g. in USDT or BNB) for trade audit transparency. Operators and agents must **never** manually subtract the `Fee` column from `Realized PnL`, as that would double-count the exit transaction fee.
- Aggregate `Historical PnL` in `trading_utils.py` similarly reports net of all cumulative execution fees (`realized_pnl - total_fees_usdt`).
- Open position `Unrealized PnL` (`positions_dashboard.py`) is floating mark-to-market ($\text{Price} \times \text{Qty} - \text{Cost}$); closing commissions are only deducted once the exit order fills.

### 11. Ground-Truth Account Balance Authority (Binance Snapshot over Database Replay)
- When evaluating historical account equity, maximum drawdowns, or monthly return trajectories, agents must **never** rely on naive cumulative point-to-point summing of closed trades in `trading_bot.db`.
- Database trade replays do not reflect overnight floating unrealized position values, partial tranche fills, or multi-week bag carry-over.
- The official daily Binance Spot account snapshot API (`client.get_account_snapshot(type='SPOT')`) and live account reconciliation (`client.get_account()`) are the **sole authoritative sources of truth** for portfolio equity, drawdowns, and historical performance audits.

### 12. Strict Signal-Only Communication Channel (Zero Email Infrastructure)
- All automated daily executive briefings, capital projections, governance summaries, and alerts must be routed exclusively via Signal Messenger (`signal-cli`).
- No email APIs, SMTP servers, or credentials (`GMAIL_USER`, `GMAIL_PASS`) are permitted in `/root/.env` or scripts.
- Any attempt to add email connections, SMTP libraries, or mailing tasks is strictly prohibited by fund owner mandate.

---

## 6. Remote Standard Operating Procedures (SOP)

All SOP commands are executed directly from this machine over SSH:

### SOP 1: Health & Performance Audit
To evaluate current portfolio status, circuit breaker liveness, and execution health:
```bash
# 1. Check live systemd services on VM
ssh bolero "systemctl status trading-bot.service backtest-optimizer.service --no-pager"

# 2. Check realized 30-day PnL, fee burn, and active positions
ssh bolero "/root/venv/bin/python /root/system_health.py"
ssh bolero "/root/venv/bin/python /root/export_report.py"

# 3. Check circuit breaker state and recent logs
ssh bolero 'journalctl -u trading-bot.service -n 50 --no-pager | grep -i "circuit breaker"'
```

### SOP 2: Run Strategic Reflection & Auto-Healing
To diagnose capital leaks (fee churn, chronic bleeding coins, premature exits) and auto-quarantine underperforming pairs:
```bash
ssh bolero "/root/venv/bin/python /root/reflect.py --auto-heal"
```
- Outputs on VM: `/root/reflection_autopsy.json` and `/root/reflection_autopsy.md`.
- Inspect output remotely:
  ```bash
  ssh bolero "cat /root/reflection_autopsy.md"
  ```
- Quarantined coins are dynamically appended to `/root/restricted_pairs.json` on the VM and reloaded dynamically by `bot.py`.

### SOP 3: Pre-Deployment Invariant Audit
Run this before staging any git changes or adopting new parameters on the remote VM:
```bash
ssh bolero "/root/venv/bin/python /root/audit_invariants.py"
```
Checks:
- Config risk limits (`MAX_RISK <= 20%`, `BASE_RISK <= 2.5%`).
- Mathematical code assertions (SL fill clamping, guarded profit locks).
- Dynamic backtest forensic inspection (zero phantom fills across all simulated trades).
- Live-to-simulation drift auditor (flags if backtest claims unrealistic profits vs live PnL).

### SOP 4: Full System Verification Suite
Run the 7-step pre-flight verification on the remote VM:
```bash
ssh bolero "/root/venv/bin/python /root/verify_system.py"
```
Validates:
1. Syntax check across all Python files.
2. Bot logic dry-run with tactical overrides.
3. Backtester smoke tests across Optuna search space.
4. Monitoring script execution.
5. Strategy version consistency (`GEMINI.md`, `bot.py`).
6. Historical stress testing across 4 crisis regimes (COVID, FTX, Leverage Flush, Random Walk) using legacy altcoins (`BNBUSDT`, `ADAUSDT`, `LINKUSDT`).
7. Pyflakes & Vulture dead-code / lint inspection.

### SOP 5: Restarting or Reloading Services
When a config change or code update requires restarting the bot:
```bash
# Restart trading engine
ssh bolero "systemctl restart trading-bot.service"

# Verify healthy startup
ssh bolero "systemctl status trading-bot.service --no-pager"
ssh bolero "journalctl -u trading-bot.service -n 30 --no-pager"
```

---

## 7. Diagnostic Playbook

### Issue A: High Binance Fee Drag
- **Symptom:** Gross PnL is positive, but net PnL is negative due to high fees.
- **Remedy:** Trade churn is too high.
  1. Increase `VOL_THRESHOLD` in `/root/config.json` on the VM (e.g. from 1.5 to 1.8) to require stronger volume anomalies.
  2. Increase `TAKE_PROFIT` or `TRAILING_TRIGGER` to ensure winners cover round-trip fees.
  3. Increase `COOLDOWN_PERIOD` to prevent immediate re-entry into chop.

### Issue B: Chronic Bleeding Coins
- **Symptom:** A specific coin has >= 3 trades with zero wins and heavy losses.
- **Remedy:** Run `ssh bolero "/root/venv/bin/python /root/reflect.py --auto-heal"`. This automatically adds the pair to `/root/restricted_pairs.json`, which `bot.py` reloads dynamically without requiring a restart.

### Issue C: Simulation vs. Live Drift
- **Symptom:** Backtester reports +15% but live portfolio equity is dropping.
- **Remedy:** Run `ssh bolero "/root/venv/bin/python /root/audit_invariants.py"`. Check if the backtester has phantom profit exits or if slippage/fees are mismatched. Confirm live positions are not suffering from low liquidity or wide bid-ask spreads.

### Issue D: Execution Paralysis (False Circuit Breaker Trips)
- **Symptom:** Bot enters 0 trades for extended hours; journal logs show repeated `Circuit breaker active, pausing entries for 4 hours`.
- **Root Cause:** Intraday drawdown threshold is set too tight (<3.0%), treating normal market drift as a portfolio emergency.
- **Remedy:** Ensure `CIRCUIT_BREAKER_1H_DD` is calibrated to `0.035` (3.5%) in `bot.py`, `portfolio_backtester.py`, and `tuner.py` on the VM.

### Issue E: Pickle Cache `EOFError` Corruptions
- **Symptom:** Scripts crash with `_pickle.UnpicklingError: pickle data was truncated` or `EOFError`.
- **Root Cause:** A process (e.g. `tuner.py`) was writing to `.backtester_cache/` directly while another process was reading it.
- **Remedy:** Verify atomic write pattern is maintained across all cache update sites using PID temporary files and `os.replace()`. Remove any corrupted partial pickle files from `/root/.backtester_cache/`.

### Issue F: Phantom Dust Position Tracking
- **Symptom:** Bot reports tracking max positions (e.g. 5/5) but account equity is mostly idle in USDT; positions contain negligible amounts.
- **Root Cause:** Small residual balances left over from previous trades (< $1.00) being counted as active trades.
- **Remedy:** Confirm the `$4.00` minimum notional filter is present in `bot.py`'s position sync logic.

### Issue G: Historical Equity Discrepancy (Replay vs. Binance Ground Truth)
- **Symptom:** Local trade replay scripts calculate unrealistic equity troughs (e.g. reporting $229 instead of the real $291 floor).
- **Root Cause:** Point-to-point cumulative sum of closed trades in `trading_bot.db` omits floating mark-to-market valuations of active bags across month boundaries.
- **Remedy:** Always query `client.get_account_snapshot(type='SPOT', limit=30)` to obtain the official Binance daily asset and BTC/USDT equity record.

### Issue H: Bot Refuses to Buy a Pumping Coin (The Missed Parabola)
- **Symptom:** An altcoin is surging (+50% to +100% on the day, like `MOVRUSDT`), but the bot takes 0 trades or refuses to re-enter.
- **Root Cause:** In `/root/bot.py:826`, the `VOLATILITY_CAP` firewall rejects setups where hourly volatility ($\text{ATR}_{1\text{h}} / \text{Price}$) exceeds `0.025` (2.52%). Parabolic runners typically have 5%–8% hourly ATR, which would immediately stop out standard -6.85% stops.
- **Remedy:** This is intended risk behavior to prevent buying blow-off tops. Verify `volatility = atr_1h / cp`. If $> 0.025$, confirm the firewall is working as designed.

### Issue I: Autonomous Governance Paralysis (LLM Quota Exhaustion)
- **Symptom:** Chronic bleeding pairs continue trading for days without being blacklisted; nightly evolution stops deploying improvements.
- **Root Cause:** Gemini API quota exhausted (`RESOURCE_EXHAUSTED 429: Individual quota reached`) in `/root/strategy_evolver.log`.
- **Remedy:** Run deterministic reflection manually: `ssh bolero "/root/venv/bin/python /root/reflect.py --auto-heal"` (which does not depend on LLM generation) to immediately blacklist negative-expectancy pairs into `restricted_pairs.json`.

---

## 8. Adversarial Multi-Agent Audit Runbook (/goal Mode)

Going forward, this skill is designed to autonomously review the remote codebase and identify architectural vulnerabilities, execution leaks, and quant simulation drift by spawning **three specialized adversarial subagents** in `/goal` mode.

### 1. The Adversarial Squad Architecture

When triggered, the coordinator agent invokes three concurrent adversarial subagents:

1. **`adversarial_invariant_auditor` (Invariant & Physics Exploiter):**
   * **Domain:** `portfolio_backtester.py`, `tuner.py`, `audit_invariants.py`, `run_quick_validation.py`.
   * **Attack Targets:** Lookahead bias (e.g. `.bfill()` on hourly indicators), round-trip fee undercounting (ignoring 0.20% fees in trade PnL), optimistic stop-loss fills during gap-downs, and Optuna objective gaming (favoring 0-trade or extreme-tail-risk parameter spaces).

2. **`adversarial_execution_auditor` (Live Execution & Risk Breaker):**
   * **Domain:** `bot.py`, `trading_utils.py`, `config.json`.
   * **Attack Targets:** Binance API edge cases (misclassifying `-2010` insufficient balance as symbol restrictions), partial fills abandoning remaining inventory, infinite sell loops on `-1013` filter rejects, 24h WebSocket drop terminations, and circuit breaker bypasses when all positions close.

3. **`adversarial_governance_auditor` (Governance & Concurrency Saboteur):**
   * **Domain:** `nightly_committee.sh`, `reflect.py`, `ai_manager.py`, `system_health.py`, SQLite DB and JSON configs.
   * **Attack Targets:** Non-atomic config writes (`config.json` read/write race conditions causing `JSONDecodeError`), SQLite lock contention (`database is locked`), AI Manager hallucinated symbol bypasses (`test_symbol_permission` returning True), omission of pre-flight invariant gates in nightly committee, and fee asset conversion blindspots (BNB fees vs USDT).

---

### 2. Master Adversarial Audit Findings & Remediation Backlog

The following table records the historical adversarial audit findings and their **verified remediation status**:

| Priority | Area | Issue & Vulnerability | Affected Files & Lines | Status | Resolution & Invariant Guard |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **P0** | **Live Bot** | `self.market_trend` dict overwrite wiped `btc_daily_range_pct`, causing fallback 1.0 and false beta decoupling on all coins. | `bot.py:404-411` | **RESOLVED** | Unified dictionary construction preserves `'btc_daily_range_pct'` for accurate relative daily range (RDR) filtering. |
| **P0** | **Live Bot** | Circuit breaker bypassed on position closure: `check_portfolio_guard()` returned early on `if not active: return`. | `bot.py:685-722` | **RESOLVED** | Equity history recorded unconditionally and drawdown calculated from rolling peak equity before checking `active`. |
| **P0** | **Live Bot** | Binance error `-2010` (insufficient balance) caught as symbol ban, blacklisting valid pairs and abandoning unsold inventory. | `bot.py:976-988` | **RESOLVED** | Error `-2010` decoupled from symbol restrictions; position tracking and WebSockets retained on failed sell. |
| **P0** | **Governance** | `nightly_committee.sh` Phase 4 permitted negative baseline comparisons (`-999.0`) to deploy losing strategies. | `nightly_committee.sh:324-336` | **RESOLVED** | Fail-closed Python comparison rejects sentinel values (`<= -900.0`) and requires candidate score $\ge$ baseline. |
| **P0** | **Governance** | `nightly_committee.sh` Phase 4 never ran standalone `audit_invariants.py` before deployment. | `nightly_committee.sh:303` | **RESOLVED** | Chained `/root/audit_invariants.py` with `verify_system.py` in Phase 4 verification gate; added EXIT restart trap. |
| **P0** | **Reflection** | Fee currency blindness: treated BNB fees as USD value, undercounting real fee drag ~600x. | `reflect.py:30-40`, `export_report.py:24-37` | **RESOLVED** | Dynamically queries BNB/USDT ticker and converts BNB fees to USDT; pro-rates sell fees on partial fills. |
| **P1** | **Backtest** | Lookahead bias in `portfolio_backtester.py`: `.bfill()` on resampled 1h indicators leaked future EMAs into early bars. | `portfolio_backtester.py:99-113` | **RESOLVED** | Excised all `.bfill()` calls; enforced strictly causal `.ffill().fillna()` and 250m warmup period. |
| **P1** | **Backtest** | Trade `pnl` ignored 0.20% round-trip Binance fees, masking fee churn as wins and evading circuit breaker. | `portfolio_backtester.py:289, 393` | **RESOLVED** | Multiplies by `0.998001` on all exits (0.10% buy + 0.10% sell); marks trades failing fee hurdle as losses. |
| **P1** | **Live Bot** | Partial fills on SELL unconditionally reset `entries: 0, qty: 0.0`, abandoning remaining unsold tokens. | `bot.py:950-958` | **RESOLVED** | Calculates `remaining_qty`; retains active position if `remaining_qty * ep > minNotional`. |
| **P1** | **Live Bot** | `test_symbol_permission()` returned `True` on `-1121 Invalid symbol`, allowing hallucinations into `tracked_pairs.json`. | `bot.py:359-373` | **RESOLVED** | Validates against `exchange_info['isAllowed']`; returns `False` on `-1121` and all unhandled exceptions. |
| **P1** | **Concurrency** | Non-atomic write to `config.json`, `restricted_pairs.json`, and `tactical_overrides.json` caused `JSONDecodeError`. | `trading_utils.py:19-24` | **RESOLVED** | Implemented PID-scoped atomic replace pattern (`atomic_json_dump`) across all state and config writers. |
| **P1** | **Database** | SQLite default 5s timeout caused `database is locked` OperationalErrors during concurrent analytics scans. | `trading_utils.py:12-17` | **RESOLVED** | Configured `PRAGMA busy_timeout = 30000` and `timeout=30.0` in centralized `get_db_connection()`. |
| **P2** | **Optimizer** | `tuner.py` search space allowed `BASE_RISK` up to 3.5%, violating quantitative risk limits. | `tuner.py:23-24, 100-106` | **RESOLVED** | Search space strictly bounded to `BASE_RISK <= 2.5%` and `MAX_RISK <= 20%`; enforced by pre-deployment firewall. |
| **P2** | **Auditor** | Naive 5-day drift window in `audit_invariants.py` counted open position buys as 100% losses. | `audit_invariants.py:121-132` | **RESOLVED** | Integrated mark-to-market valuation of open positions from `active_positions.json` into net return calculation. |
| **P2** | **Live UI** | Synchronous Binance REST API calls and 6,500-trade loop in `dashboard.py` froze UI for ~4s per frame. | `dashboard.py:40-85` | **RESOLVED** | Decoupled UI with background worker thread, atomic disk cache (`.dashboard_cache.json`), and dynamic height auto-fit. |
| **P2** | **Live UI** | Synchronous REST calls (`get_ticker` x 9, `get_historical_klines`) in `positions_dashboard.py` froze UI for ~3.1s on each arrow keypress. | `positions_dashboard.py` | **RESOLVED** | Decoupled UI with `positions_worker` daemon thread, atomic disk cache (`.positions_cache.json`), and sub-2ms local memory rendering. |
| **P2** | **Performance** | Top-level import of heavy C-extensions (`pandas`, `binance.Client`) in `trading_utils.py` imposed a 5.4s cold-boot penalty under Optuna load. | `trading_utils.py:1-10` | **RESOLVED** | Implemented lazy imports inside `get_binance_client` and `get_trade_data`, cutting import time from 5.39s to 0.44s (12x speedup). |
| **P2** | **Live UI** | Subprocess spawning in `bolero.py` on menu options added ~7.6s process boot and terminal buffer flicker on screen transitions. | `bolero.py` | **RESOLVED** | Integrated in-process screen execution, hotkey flipping (`P` for positions, `D` for live bot, `Q`/`ESC` for menu), and numeric shortcuts. |
| **P2** | **Live UI** | Sells lacked per-trade realized dollar and percentage PnL in the recent trades table. | `dashboard.py:126-150` | **RESOLVED** | Integrated FIFO cost basis matching into background worker and added color-coded `Realized PnL` column on SELL rows. |
| **P2** | **Governance** | Agent session violated explicit user instruction ("do not change code"), modifying 23 files and restarting live bot. | Historical Session `b1d05c86` | **RESOLVED** | Formulated Law 9 Strict Change-Gating Invariant in `bolero-maintenance` skill. |
| **P2** | **Reporting** | Markdown asterisks (`*`, `**`) render literally in Signal Messenger, cluttering mobile display readability. | `daily_signal_brief.py:317-325` | **RESOLVED** | Implemented `clean_for_signal()` filter and prompt rule forbidding asterisks, enforcing clean Unicode bullets (`•`) and uppercase headers. |
| **P2** | **Governance** | Operator confusion regarding "V162" or "V161" appearing in logs while live engine runs V160. | `strategy_evolver.log`, `nightly_committee.sh` | **RESOLVED** | Documented version lineage: V160 is production live code; V161 was rolled back post-FTX/trough; V162 was a candidate proposal in committee logs. |
| **P2** | **Reporting** | User directive mandate: deprecated all email SMTP APIs/credentials; enforced Signal exclusivity. | `daily_signal_brief.py`, `.env` | **RESOLVED** | Stripped GMAIL credentials from .env, excised send_email_message and CLI args, preserved Signal-only messaging. |

---

### 3. Key Architectural Patterns & Invariant Standards (Institutional Lessons)

1. **Atomic File Persistence Standard (`atomic_json_dump`):**
   * Never use `with open(filepath, 'w') as f: json.dump(...)` for files read by concurrent daemons (`config.json`, `restricted_pairs.json`, `active_positions.json`, `tactical_overrides.json`).
   * Always write to a PID-scoped temporary file (`f"{filepath}.tmp.{os.getpid()}"`) and perform POSIX atomic `os.replace()`.

2. **Centralized SQLite Connection Factory (`get_db_connection`):**
   * Never establish bare `sqlite3.connect()` calls with default 5-second timeouts.
   * Always use `trading_utils.get_db_connection(db_path)` which sets `timeout=30.0`, `PRAGMA busy_timeout = 30000`, and `PRAGMA journal_mode=WAL`.

3. **Peak-to-Trough Drawdown Invariant:**
   * Never calculate drawdown as point-to-point percentage return against the oldest window element.
   * Always calculate drawdown against the dynamic peak equity achieved during the rolling 1-hour window:
     ```python
     peak_equity = max(e[1] for e in equity_history)
     drawdown_1h = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0.0
     ```

4. **Fee-Aware Physics Invariant:**
   * Backtest physics must always calculate trade PnL net of round-trip Binance fees (`* 0.998001 - 1.0`).
   * Reflection and reporting engines must always convert non-USDT commissions (specifically BNB) to USD using live or fallback ticker pricing.

5. **Zero-Flicker Event-Driven Terminal Standard (`console.capture` + `term.clear_eos`):**
   * Never execute `print(term.home + term.clear)` inside timed render loops (`timeout=0.25`). Sending ANSI `\x1b[2J` multiple times per second erases the buffer and produces severe screen strobing.
   * Always gate redraws on a `need_redraw` flag (triggered strictly by keystrokes or background data updates).
   * Always buffer the complete screen frame in memory using `console.capture()`, and paint it in a single atomic write:
     ```python
     print(term.home + frame_output + term.clear_eos, end='', flush=True)
     ```
     `term.home` replaces text in-place without erasing, and `term.clear_eos` trims trailing rows cleanly without full-screen wipes.

6. **Live Account Balance & Cash Allocation Transparency Standard:**
   * Dashboards must never display isolated PnL figures (`Realized PnL`, `Unrealized PnL`) without prominently reporting **Total Spot Account Equity** and **Free USDT Cash**.
   * On small-account multi-slot spot architectures ($345 total equity across 7–10 positions of $20–$25 each), floating unrealized gains represent temporary intra-trade cushions (+1% to +2% portfolio move), which are already factored into live equity.
   * Background daemon workers must reconcile directly with `client.get_account()` and persist:
     - `Total Equity`: `USDT cash + sum(position values) + BNB valuation` (matching the Binance mobile app down to the penny).
     - `USDT Cash Reserve`: Free unallocated liquidity awaiting high-expectancy setups.
     - `Active Positions Value`: Capital actively deployed in decoupled momentum breakouts.
