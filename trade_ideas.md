Based on the statistical data provided, here are the proposed filters to improve the overall win rate and profitability:

### 1. Time-of-Day Filters (Exclude Specific Hours)
*   **Filter out hours 13, 17, 20, and 22.**
    *   **Hour 22** is severely underperforming: 26.0% win rate and -0.764 average PnL.
    *   **Hours 13, 17, and 20** all show win rates below 40% (34.9%, 38.1%, 34.1%) with significant negative average PnL. Avoid initiating trades during these windows.

### 2. Day-of-Week Filters
*   **Prioritize DOW 4 / Reduce risk on other days.**
    *   **DOW 4** is a massive outlier for profitability, generating a 55.4% win rate and +0.218 avg PnL. All other days yield negative average PnL. Consider increasing position sizes on DOW 4 and using stricter entry criteria on days 1, 2, 3, and 5.

### 3. Hold Time Limits
*   **Implement a 24-hour Time Stop.**
    *   Profitability peaks in the **12-24h bucket** (61.2% win rate, +0.485 avg PnL). However, holding beyond 24 hours results in average PnL dropping into the negative (-0.065). If a trade has not played out within 24 hours, automatically close it to free up capital and prevent drag.

### 4. Pair Exclusions (Blacklist)
*   **Exclude Meme Coins with high volume and low win rates:**
    *   `PEPEUSDT`: 22.7% win rate, -42.69 Total PnL (88 trades)
    *   `DOGEUSDT`: 37.8% win rate, -56.24 Total PnL (98 trades)
    *   `SHIBUSDT`: 31.3% win rate (32 trades)
*   **Exclude structural underperformers:**
    *   `PENDLEUSDT`: 33.9% win rate, -40.35 Total PnL (59 trades)
*   **Exclude "Win Small, Lose Big" Pairs:**
    *   `SOLUSDT`: Despite a high win rate (64.9%), it has one of the worst total all-time PnL profiles (-98.56 USDT) and a -0.325 average PnL per trade, indicating disastrous risk-to-reward metrics. Ensure this is blacklisted.
