### Market Data Characteristics Analysis

1. **Compression vs. Expansion Polarization**:
   - **BTC (514 squeezes, 0.45% hourly vol)** and **ETH (417 squeezes, 0.64% hourly vol)** spend significant time in tight Bollinger Band coiling regimes with low daily ranges (~14–19%).
   - In stark contrast, high-beta altcoins show extreme momentum divergence: **NEAR** exhibits an explosive **111.14% 30d trend** with only **19 BB squeezes** and **45.8% avg daily range**, showing that alpha is overwhelmingly concentrated in continuous directional expansions rather than mean-reversion chop.
2. **Failure Modes from Past Learnings**:
   - Time/day filters and arbitrary tight trailing stops (e.g., ADX-tightening, -3.0% hard SL cap, ATR 3.0 SL) consistently failed by truncating high-volatility runners like NEAR/SOL during standard cyclical swings.
   - Successful alpha capture in flat-to-consolidating BTC conditions relies on mechanical, price-action-based expansion confirmation and momentum exhaustion exits, rather than temporal or rigid percentage boundaries.

---

### Proposed Signals & Filters

#### 1. Range Expansion & Relative Volume Filter (Entry Confirmation)
* **Goal**: Prevent false breakouts during heavy compression regimes (500+ BTC/ETH squeezes) while immediately seizing high-conviction runner momentum (e.g., NEAR-style breakouts).
* **Price Action Logic**: Require an entry bar to demonstrate definitive directional expansion rather than low-volume drift inside a squeeze.
* **Conditions**:
  1. **Expansion Candle**: $\text{Bar Range } (\text{High} - \text{Low}) > 1.5 \times \text{ATR}_{14}(1\text{h})$.
  2. **Close Position Strength**: $\frac{\text{Close} - \text{Low}}{\text{High} - \text{Low}} \ge 0.70$ (bar closes in the top 30% of its range, confirming directional buyer control).
  3. **Volume Confirmation**: $\text{Volume} > 1.8 \times \text{SMA}(\text{Volume}, 20)$.
* **Advantage**: Bypasses temporal overfitting (TOD/DOW) by conditioning trades strictly on institutional liquidity influx and true volatility expansion.

---

#### 2. Climax Wick Rejection Exit (Price Action Take-Profit / Exhaustion Signal)
* **Goal**: Lock in gains on parabolic decoupling runners without premature trailing stop-outs during routine mid-trend pullbacks.
* **Price Action Logic**: High-beta trend runners (+30% to +110%) often terminate in high-volume exhaustion blow-offs where buyers fail to maintain upper-range price levels (shooting star / rejection prints).
* **Conditions**:
  1. **New Local High**: $\text{High} \ge \text{Highest}(\text{High}, 24)$.
  2. **Exhaustion Wick**: $\frac{\text{High} - \max(\text{Open}, \text{Close})}{\text{High} - \text{Low}} \ge 0.55$ (upper wick accounts for $>55\%$ of the total bar range).
  3. **Climax Volume**: $\text{Volume} > 2.5 \times \text{SMA}(\text{Volume}, 20)$.
* **Execution**: Trigger immediate full position close or 75% profit-taking exit on candle close when all three conditions are satisfied.
* **Advantage**: Replaces tight trailing stops with an objective price-rejection trigger, letting positions run uninterrupted until genuine institutional distribution or exhaustion appears.
