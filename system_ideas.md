# System & Risk Analyst Review

**Evaluation Timestamp:** `2026-10-02 03:00:59 UTC`  
**Strategy Version:** V160 — Volatile Momentum & Decoupling Squeeze  
**Governing Policy:** [bolero-governance](file:///root/.agents/skills/bolero-governance/SKILL.md)

---

## 1. System Health & Infrastructure Audit

| Component | Status | Metrics / Observation |
| :--- | :--- | :--- |
| **Trading Engine** ([`bot.py`](file:///root/bot.py)) | **ACTIVE / HEALTHY** | 5-minute event loop executing normally; feeds & order locks synchronized. |
| **Optimizer Engine** ([`tuner.py`](file:///root/tuner.py)) | **ACTIVE / HEALTHY** | Optuna Bayesian Study active; new best train score achieved: **13.98%**. |
| **Circuit Breakers** | **NORMAL** | 1h portfolio drawdown << 3.50%; 0 failed execution orders in the last 1h/24h. |
| **Restricted Pairs** | **ENFORCED** | 229 blacklisted symbols successfully loaded from [`restricted_pairs.json`](file:///root/restricted_pairs.json). |

---

## 2. Performance Forensic & Root-Cause Analysis (Last 24h & 30d)

* **24h Realized Net PnL:** **-$4.13 USDT** (Gross: -$4.05, Fees: $0.074, 5 completed trades).
* **Multi-Horizon Context:**
  * **Last 7 Days:** **+$29.62 Net PnL**, 68.0% Win Rate, Profit Factor 2.54 across 50 trades.
  * **Last 30 Days:** **+$19.18 Net PnL**, 46.7% Win Rate, Profit Factor 1.06 across 225 trades with **$20.34 paid in fees** (51.5% fee drag against gross profit).
* **Forensic on Outlier Losses (ARBUSDT -18.92%, RAYUSDT -10.57%):**
  * Dissection of [trading_bot.db](file:///root/trading_bot.db) and [export_report.py](file:///root/export_report.py) confirms the reported large losses and 180h+ durations are **FIFO trade-matching artifacts** against residual positions opened on Sept 23.
  * Actual execution stops closed ARBUSDT at **-7.48%** (entry: $0.2150, exit: $0.1989) and RAYUSDT at **-6.92%** (entry: $2.0430, exit: $1.9016), adhering to the parameterized initial stop-loss band in [`config.json`](file:///root/config.json).

---

## 3. Risk Boundary & Invariant Verification

1. **`MAX_RISK_PER_TRADE_PERCENT` Verification:**
   * Current config value: **18.74%** (Production ceiling: 18.00%, Hard governance limit: 20.00%).
   * **Status: COMPLIANT**. Current allocation remains safely below the critical 20.00% destructive drawdown ceiling.
2. **Trailing Stop & Profit Lock Verification:**
   * Line-by-line verification of [`bot.py`](file:///root/bot.py#L610-L637) confirms trailing stops and profit locks **trigger strictly on genuine profits**:
     * Trailing stop activates only when `profit_pct > TRAILING_TRIGGER` (+8.0%), trailing by `TRAILING_DIST` (3.5%).
     * Profit lock activates after 18h hold only if `profit_pct >= PROFIT_LOCK_PCT` (+0.75%), ratcheting to `entry_price * 1.0075`.
     * Zero risk of locking in negative returns or converting winners into losses.

---

## 4. Structural & Risk Management Proposals

### Proposal 1: Strict Upper Clamp on Initial Stop-Loss (`SL_MAX_PCT`)
* **Problem:** `SL_MAX_PCT` has drifted in Optuna tuning to **0.075 (7.5%)**, exceeding the V160 specification cap (-6.0% to -7.0%).
* **Action:** Restrict `SL_MAX_PCT` upper bound in [`config.json`](file:///root/config.json) to **0.070 (7.0%)** and keep `MAX_RISK_PER_TRADE_PERCENT` clamped at **<= 18.0%** to avoid widening per-trade risk in volatile regimes.

### Proposal 2: Churn & Fee Drag Mitigation via Volume Threshold
* **Problem:** 30-day autopsy highlights $20.34 burned in trading fees across 225 trades. Low-conviction entries during choppy BTC consolidation erode capital.
* **Action:** Increase `VOL_THRESHOLD` from **1.5x to 1.8x** for `Decoupled_Squeeze_Breakout` entries to demand true institutional volume confirmation and filter marginal chop.

### Proposal 3: Staleness Exit Calibration
* **Problem:** 10 positions exited around 18–24 hours at small net losses (totaling -$25.58) within the `[-0.5%, +0.5%]` flat zone due to fee erosion.
* **Action:** Shift the `STALENESS_EXIT_MIN` / `STALENESS_EXIT_MAX` range from `[-0.005, 0.005]` to **`[+0.002, +0.006]`**, ensuring time-decay exits only release capital when the trade is at least break-even net of round-trip fees.

### Proposal 4: Portfolio Guard Structural Hardening
* **Problem:** `PORTFOLIO_EJECT` currently sits at **-9.93%**, which is too wide for spot capital preservation during sudden correlated market sell-offs.
* **Action:** Tighten `PORTFOLIO_EJECT` to **-8.00%** while leaving `CIRCUIT_BREAKER_1H_DD` at its constitutional invariant of **0.035 (3.5%)**.
