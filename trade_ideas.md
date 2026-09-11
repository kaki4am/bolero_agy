Based on the provided historical trade data and previous learnings, here are the recommended filters to improve the win rate:

**1. Pair Exclusions (Highly Recommended)**
Exclude the following pairs, which have statistically significant trade counts but persistently terrible win rates and large negative PnL:
*   **PEPEUSDT**: 88 trades, 22.7% Win Rate, -42.69 PnL
*   **DOGEUSDT**: 98 trades, 37.8% Win Rate, -56.24 PnL
*   **PENDLEUSDT**: 59 trades, 33.9% Win Rate, -40.35 PnL
*   **VETUSDT**: 16.7% Win Rate (Worst performer in both 30-day and all-time metrics)
*(Note: Do not exclude SOLUSDT despite its all-time negative PnL, as its win rate is high (64.9%) and it is actively being used as a successful decoupled momentum asset in current forward testing).*

**2. Time-of-Day & Day-of-Week Filters (Reject)**
*   **Recommendation**: Do not implement any TOD or DOW filters. 
*   **Reasoning**: Previous learnings from 2026-09-06 through 2026-09-09 explicitly state that these filters cause severe overfitting and significantly degrade out-of-sample forward testing performance. 

**3. Hold Time Limits (Reject)**
*   **Recommendation**: Do not implement a maximum hold time limit.
*   **Reasoning**: The longest hold time bucket (`24h+`) actually maintains a strong win rate of 57.8%. The majority of losses and the lowest win rates occur in the `0-2h` bucket (43.8% WR), indicating premature stop-outs due to volatility rather than drawn-out holding periods. Enforcing a strict hold time limit (like the previously rejected 72h limit) would likely cut off delayed winners and artificially lower the win rate.
