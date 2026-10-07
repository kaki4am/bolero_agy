---
name: bolero-governance
description: Constitutional architectural invariants, quantitative risk boundaries, code integrity rules, and telemetry failure guardrails for the Bolero Binance spot trading bot. Consult before modifying trading logic, backtest engines, or parameters.
---

# Bolero Bot Constitutional Governance & Invariant Rules

This skill defines the non-negotiable boundaries, backtest physics, execution invariants, and runtime health standards governing all autonomous code generation, tuning, and committee proposals for the Bolero trading bot.

---

## 1. Strategy V161 Core Profile
* **Asset Class:** Binance Spot exclusively (USDT quote pairs). Zero leverage, no margin borrowing, no derivatives.
* **Entry Setup (Decoupled Squeeze Breakout & Trend Continuation):**
  * **Trend Alignment Filter:** 1h Close > 50 EMA and 50 EMA Slope >= Flat.
  * **Momentum Filter:** 1h RSI(14) between 52.0 and 75.0 (rejects exhausted or climax pumps).
  * **Decoupling Gate:** BTC 4h ROC between -3.0% and +1.0%, while Altcoin 4h ROC > (BTC 4h ROC + 3.0%).
  * **Entry Signal:** Altcoin RVOL > 1.8x (vs 24h average), Candlestick Body-to-Range > 0.40, and price closes outside upper Bollinger Band with expanding bands.
* **Exit Architecture:**
  * Initial stop loss hard-capped at max -7.0% (calibrated dynamically by ATR and BTC 24h return).
  * Trailing stop (-3.5%) activates only after establishing a +6.0% to +8.0% profit cushion.
  * Time-decay exit: Trades held > 48h must maintain positive 24h momentum and healthy volume, or be gracefully liquidated.
  * Portfolio Guard: Global Eject at PORTFOLIO_EJECT% (-8.0%), Global Harvest at PORTFOLIO_HARVEST%.
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
* `SL_MAX_PCT <= 0.070` (Hard 7.0% stop-loss ceiling).
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

### 11. Ingestion Schema Parity & Test Mock Integrity
* Any column or indicator evaluated in `analyze()` (e.g. `open`, `volume`, `rsi`) **MUST** be explicitly populated in both:
  1. Initial historical klines ingestion (`client.get_historical_klines` in `bot.py`).
  2. Live streaming websocket updates (`update_data` / `kline_socket` in `bot.py`).
* Unit tests in `verify_system.py` Step 2 must test the **real Binance kline schema** (`['t','o','h','l','c','v',...]`) and live websocket event structure. Tests must NEVER artificially synthesize DataFrames with columns that live ingestion does not provide.

### 12. Asyncio Exception Visibility & Defensive Data Access
* All column lookups in `analyze()` must use defensive checks (`op = df['open'].iloc[-1] if 'open' in df.columns else cp`) to avoid halting background evaluation on schema variations.
* Every asynchronous background worker (such as `process_and_analyze()`) must be wrapped in explicit `try...except Exception as e:` blocks with stderr logging and traceback output.
* The main asyncio event loop must register an uncaught task exception handler (`loop.set_exception_handler()`) so runtime failures cannot be silently swallowed.

### 13. Active Journal Log Health Auditing (No False-Green Daemons)
* Health monitors (`system_health.py`, `daily_signal_brief.py`) must **NEVER** treat `systemctl is-active` as sufficient proof of system health. A Python process can remain running while its background event tasks fail on every tick.
* Health checks must actively scan `journalctl -u trading-bot.service` since the current service invocation for Python tracebacks, `KeyError`, `AttributeError`, or unhandled task exceptions. If errors are detected, the system status must immediately transition to **`CRITICAL ERROR`** and surface the exact error in executive briefings.

### 14. Governance Intelligence Recency & Anti-Staleness Gate
* All governance status reporting and daily briefings must inspect the file modification time and embedded execution timestamp of committee outputs (`reflection_autopsy.md`, `strategy_evolver.log`).
* If a committee run is older than 24–30 hours or was bypassed by the credit/quota gate, the briefing must explicitly state that the committee was **SKIPPED / Inactive** and that the active strategy version remains unchanged in production.
* Historical backtest scores, autopsies, and diagnosed leak ledgers from prior runs must **NEVER** be presented as fresh overnight results.
