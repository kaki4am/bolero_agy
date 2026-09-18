# System Health & Risk Analysis Report
**Timestamp:** `2026-09-18 03:00:38 UTC`  
**Strategy Version:** `V158 - Volatile Momentum & Decoupling Squeeze`  
**Portfolio Equity:** `~$293.99 USDT` (24h Realized PnL: `+19.33 USDT` / `+6.6%`)

---

### 1. System Health & Execution Review

* **Service Status:** `trading-bot` and `backtest-optimizer` are operational (`OK`). 0 failed trades in the last hour.
* **Bayesian Tuner (Optuna):** Active and healthy (last run 0.11h ago). New best train score reached **17.60%**.
* **Order Execution Failure:**
  * Pair: `BNCBUSDT` (Failure ID: 130, `2026-09-17 16:38:01`)
  * Error: `apierror(code=-2010): this symbol is not permitted for this account.`
  * **Finding:** While 195 restricted pairs are loaded, `BNCBUSDT` bypassed the whitelist filter and failed at execution.

---

### 2. Performance & Risk Assessment

* **Trade Asymmetry:** Strong positive skew.
  * **Winners:** Multi-day runners captured massive moves (`ARBUSDT` +15.64% over 36h, `AVAUSDT` +15.33% over 90h, `DASHUSDT` +8.35% over 204h).
  * **Losers:** Contained losses (`TLMUSDT` -3.48% exited in 36m, `ZENUSDT` +0.20% near breakeven).
* **Hold Time Validation:** Long holding periods (up to 204h) generated the bulk of alpha, re-confirming that time-based hold caps (e.g., rejected 72h limit) would be counter-productive.
* **Macro Regime:** BTC is coiling positively (4h: `+0.74%`, 24h: `+0.81%`). Baseline risk posture (`Risk Mult=1.0`, `SL Offset=0.0`) is appropriate.

---

### 3. Structural & Risk Management Proposals

#### A. Symbol Whitelist & Exchange Permission Guard (Immediate)
* **Action:** Permanently append `BNCBUSDT` to the static restricted pairs list (`restricted_pairs.json` / dynamic blacklist).
* **Structural Guard:** In the universe scanner, add a pre-flight check verifying exchange account permissions (`permissions` / `isSpotTradingAllowed` flags via Binance exchange info API) before generating order signals, preventing `-2010` rejection overhead.

#### B. Stop Loss & Take Profit Configuration
* **Stop Loss:** **Maintain baseline SL structure.** `TLMUSDT` was cleanly cut at -3.48%, demonstrating proper protection without prematurely choking high-volatility pairs. **Reject** any hard cap tightening below 3.5%, as past learnings show tighter caps induce premature liquidations during normal market noise.
* **Take Profit:** **Retain tiered target TP.** Both `ARBUSDT` (+15.6%) and `AVAUSDT` (+15.3%) achieved full target fills. Do not introduce aggressive trailing stops, which previously choked momentum decoupling runners.

#### C. Portfolio Risk Posture
* **Exposure Multiplier:** Keep `RISK_MULTIPLIER = 1.0` and `SL_OFFSET = 0.0` while BTC 24h return remains positive (`> 0.0%`).
* **Macro Escalation Thresholds:** Maintain existing trigger logic:
  * **BTC -1.0% to -3.0%:** Reduce risk multiplier to `0.75 - 0.50` with slight SL tightening.
  * **BTC < -3.0% or acute systemic risk:** Reduce risk multiplier to `0.40` with defensive eject offsets (`0.60`).
* **Time-Based Filters:** Maintain full rejection of Time-of-Day (TOD) and Day-of-Week (DOW) exclusions to avoid forward-test overfitting.

#### D. Tuner Promotion Guard
* Ensure parameters from Optuna's latest high-scoring run (17.60%) undergo mandatory out-of-sample forward-testing verification across contrasting market regimes before live parameter replacement.
