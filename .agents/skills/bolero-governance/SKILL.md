---
name: bolero-governance
description: Constitutional architectural invariants, quantitative risk boundaries, and code integrity rules for the Bolero Binance spot trading bot. Consult before modifying trading logic, backtest engines, or parameters.
---

# Bolero Bot Constitutional Governance & Invariant Rules

This skill defines the non-negotiable boundaries, backtest physics, and execution invariants governing all autonomous code generation, tuning, and committee proposals for the Bolero trading bot.

---

## 1. Strategy V160 Core Profile
* **Asset Class:** Binance Spot exclusively (USDT quote pairs). Zero leverage, no margin borrowing, no derivatives.
* **Entry Setup (Decoupled Squeeze Breakout):**
  * BTC 4h ROC between -3.0% and +1.0%.
  * Altcoin 4h ROC > (BTC 4h ROC + 3.0%).
  * Altcoin RVOL > 1.5x (current hour vs 24h average).
  * Price closes outside upper Bollinger Band with expanding bands.
* **Exit Architecture:**
  * Wide initial stop (-6.0% to -7.0%).
  * Trailing stop (-3.5%) activates only after establishing a +6.0% to +8.0% profit cushion.
  * Time-decay exit: Trades held > 48h must maintain positive 24h momentum and healthy volume, or be gracefully liquidated.
  * Portfolio Guard: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%.
  * Circuit Breaker: 4-hour entry pause if 1h portfolio drawdown exceeds 3.5% or >3 losses occur in 1 hour.

---

## 2. Non-Negotiable Invariant Laws

### 1. Immutable Backtest Physics
* Stop-loss fills must always be clamped to market reality:
  `exit_price = min(old_sl, price) * (1.0 - slippage_pct)`
* Profit locks must never trigger on losing trades:
  `if current_profit_pct >= params.get('PROFIT_LOCK_PCT', 0.005):`
* All backtests must account for round-trip Binance fees (`* 0.998001 - 1.0`) and slippage. Lookahead bias (e.g. `.bfill()`) is strictly forbidden; use strictly causal `.ffill().fillna()`.

### 2. Position Sizing & Risk Ceilings
* `MAX_RISK_PER_TRADE_PERCENT <= 20.0%` (Production: 18.0%).
* `BASE_RISK_PERCENT <= 2.5%` (Production: 1.5%).
* Never allocate >20% of account equity to a single asset.

### 3. Circuit Breaker Calibration Floor
* `CIRCUIT_BREAKER_1H_DD = 0.035` (3.5% 1-hour portfolio drawdown).
* Threshold must remain between 3.0% and 5.0%. Oversensitive thresholds (<3.0%) cause execution paralysis during normal altcoin market volatility.

### 4. Atomic File Persistence Standard
* Multi-process state and cache files (`config.json`, `restricted_pairs.json`, `active_positions.json`, `tactical_overrides.json`, `.backtester_cache/*.pkl`) must always be written atomically:
  Write to `f"{filepath}.tmp.{os.getpid()}"` first, then perform POSIX `os.replace()`.

### 5. All-in / All-out Execution (Rejection of Partial Sells)
* Partial scale-outs (e.g. 50% at TP1) are strictly rejected on small-account spot architectures:
  1. Splitting exits drops the second leg below Binance's $5.00 minNotional limit, causing `-1013 Filter failure` errors on stop-losses.
  2. Trailing stops (+6% trigger, -3.5% trail) provide downside protection without cutting winners prematurely.

### 6. Minimum Notional & Dust Filter
* Balance sync must enforce `MIN_NOTIONAL = $4.00` to prevent sub-dollar residual dust from occupying active risk slots.

### 7. Asynchronous Decoupled UI & Non-Blocking Loops
* Never perform synchronous Binance REST calls (`client.get_account()`, `get_ticker()`) or heavy trade replays inside UI render loops.
* Background daemon threads must update atomic disk caches (`.dashboard_cache.json`, `.positions_cache.json`).

### 8. Strict Signal-Only Messaging (Zero Email Infrastructure)
* All notifications, executive briefings, and autopsies must be delivered exclusively via Signal Messenger (`signal-cli`).
* Storing email credentials or importing SMTP/email libraries is strictly prohibited by fund owner mandate.

### 9. System Cleaner Whitelist Standard
* Any new operational or governance utility script placed in `/root/` must be immediately added to the `WHITELIST` in `/root/cleanup_system.py` to prevent automated pruning.

### 10. Strict Change-Gating Invariant
* If user prompt or task specifies "audit only" or "do not change code", never modify files, alter configs, or restart services.
