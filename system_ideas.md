Based on the current health and performance data, here are the structural and risk management proposals:

**1. Portfolio Guards (Circuit Breaker & Market Filter)**
*   **Halt / Reduce Exposure:** The BTC 15m trend is DOWN and the past 24H PnL is severely negative (-$12.09). Pause new trades or reduce the `Risk Mult` further (e.g., from 0.8 to 0.2 or 0.0) until the broader market trend turns positive.
*   **Daily Max Drawdown:** Implement a hard daily drawdown limit (e.g., halt all trading for 24h if daily PnL hits -5%). 

**2. Stop-Loss & Risk Adjustments**
*   **Tighten Hard Stop-Loss:** The worst trade (LPTUSDT) lost -8.44%. Cap the absolute maximum stop-loss per trade at -2.5% or -3.0% to prevent catastrophic single-trade drawdowns.
*   **Trailing Stop Sensitivity:** Breakout strategies in downtrends often result in false breakouts. Tighten the trailing stop activation threshold to lock in profits earlier before price reverses.

**3. Take-Profit & Risk-Reward**
*   **Asymmetric R:R Requirement:** Your losers are currently far outpacing your winners (e.g., -8.44% loss vs +0.40% gain). Enforce a minimum Risk:Reward ratio before entry, or scale out of positions in fractions (e.g., sell 50% at +1% profit) to ensure winning trades cover the costs of false breakouts.

**4. Operational / Structural**
*   **Restricted Pairs Update:** Add `MITOUSDT` and `MARSCOINUSDT` to the restricted pairs list immediately to prevent repeated API `-2010` (symbol not permitted) errors.
