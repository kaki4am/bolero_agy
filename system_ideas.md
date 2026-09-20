# System & Risk Analyst Report

**Timestamp:** `2026-09-20 03:00:25`  
**System Status:** **OK** (All core daemons active; Optuna running IS trials; 0 recent 1h execution failures).  
**Account Equity:** ~$338.61 USDT | **24h Realized PnL:** -$21.57 USDT (~ -6.0% account drawdown).

---

## 1. Key Performance & Operational Findings

1. **BTC Rapid Deterioration into Risk Band:**
   * BTC has slipped rapidly between 02:30 and 03:00 UTC (4h return dropped from `-0.10%` to `-1.14%`, 24h return to `-1.20%`).
   * The bot is still operating at full risk (`Risk Mult=1.0, SL Offset=0.0`), violating established macro guidelines for the `-1.0%` to `-3.0%` BTC retracement band.

2. **Immediate Churn / Whipsaw Giveback:**
   * **XTZUSDT:** Captured a +$11.81 (+9.73%) gain over 3h 33m (exit at 06:52), but re-entered just 29 minutes later at 07:22 at a higher peak price (0.3725 vs 0.3564), stopping out at -7.68% (-$8.25) in 1h 9m. This single trade gave back 70% of the session’s best win.

3. **Zombie Positions & Capital Inefficiency:**
   * `ICPUSDT` (held 472h / ~19.7 days) and `STXUSDT` (held 466h / ~19.4 days) tied up capital for nearly three weeks only to exit at -4.56% and -4.38%. 
   * While hard hold-time caps (e.g., 72h) were previously rejected for cutting off long runners, unmanaged dead capital severely drags liquidity.

4. **Inconsistent Loss Clustering & Account Sizing:**
   * Average stops triggered around -4.1% to -4.5% (ALGO, ICP, ZEN, STX), but `ARUSDT` (-8.07%, -$4.01) and `XTZUSDT` (-7.68%, -$8.25) suffered oversized percentage excursions, indicating stop distance variance or slippage.

5. **Permission Failure:**
   * `PROVEUSDT` failed with error `code=-2010: this symbol is not permitted for this account`.

---

## 2. Structural & Risk Management Proposals

### Proposal 1: Tactical Macro Risk Reduction (Immediate)
* **Trigger:** BTC 4h/24h return crossed below `-1.0%` (`-1.14%` / `-1.20%`).
* **Action:** Shift tactical overrides from `Risk Mult=1.0` to **`Risk Mult=0.75`** and apply a modest portfolio eject offset (**`+0.25`**) until BTC 4h return stabilizes back above `-0.50%`.
* *Rationale:* Adheres to proven playbook for mild sub-threshold pullbacks without inducing premature liquidation.

### Proposal 2: Post-Win Re-Entry Cooldown (Anti-Whipsaw Guard)
* **Problem:** Momentum chasing back into the same asset immediately following a take-profit exit.
* **Proposal:** Enforce a **120-minute re-entry cooldown** on any pair that triggered a full take-profit or large gain (>5%), *unless* price pulls back to at least the 20 EMA or forms a fresh higher-low consolidation.
* *Rationale:* Directly prevents the exact failure mode seen on `XTZUSDT` without restricting unrelated market opportunities.

### Proposal 3: Dynamic Thesis Invalidation for Stagnant Trades
* **Problem:** Month-long zombie positions (`ICPUSDT` 472h, `STXUSDT` 466h) locking capital.
* **Proposal:** Rather than arbitrary time limits (which were rejected), implement a **Volume & Momentum Decay Exit**:
  * If a trade has been open >120 hours AND has failed to touch within 1.0% of its initial entry price or make a higher high for 48 consecutive hours, allow a graceful breakeven/market exit when volume drops below the 20-period moving average.
* *Rationale:* Respects positive expectancy of genuine 24h+ trend runners while pruning inactive capital.

### Proposal 4: Account-Level Notional Risk Cap per Trade
* **Proposal:** Normalize position sizing so that initial Stop-Loss risk strictly caps maximum realized loss at **1.5% of total equity** (~$5.00 on current $338.61 equity). 
* *Rationale:* Prevents wide-stop assets like `XTZ` (-$8.25) from inflicting disproportionate damage to the account balance.

### Proposal 5: Account Restriction Sanitation
* **Action:** Immediately append **`PROVEUSDT`** to the restricted/blacklisted pairs list to eliminate rejected API calls and avoid thread latency.
