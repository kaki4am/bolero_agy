### 1. Market Data & Price Action Analysis

* **Compression vs. Trend Regimes:** High-cap majors (**BTC** at 506 squeezes, **ETH** at 421 squeezes) spend prolonged periods in low-volatility Bollinger Band squeezes with moderate daily ranges (14%–19%). Conversely, high-beta momentum assets (**NEAR** with only 19 squeezes, +60.07% 30d trend, 44.59% daily range; **SOL** with +31.10% trend) operate in sustained volatility expansion regimes.
* **Volume/Range Decoupling:** Assets with lower squeeze counts and high hourly volatility ($1.26\%$ on NEAR) achieve massive trend outperformance. When majors compress, capital concentrates into localized altcoin momentum breakouts.
* **Prior Learning Alignment:** Previous rejections confirm that time-based filters (TOD/DOW), hard stop-loss caps ($\le 3\%$), and tight ADX/ATR trailing stops choke valid trades during routine crypto chop. Adjustments must focus on **volume-confirmed expansion at entry** and **volatility-exhaustion scaling at exit** rather than premature stop-loss tightening.

---

### 2. Proposed Signals & Filters

#### Proposal 1: Relative Volume Expansion Breakout Filter (Entry Confirmation)
* **Objective:** Differentiate between low-liquidity false breakouts during major squeeze regimes (BTC/ETH) and genuine decoupled momentum expansions (SOL/NEAR).
* **Price Action Logic:**
  * Require the breakout candle to demonstrate institutional volume participation relative to its recent baseline, preventing entries into low-volume chop during high squeeze counts.
* **Indicators & Formulation:**
  * **Relative Volume (RVOL):** $\text{RVOL}_{20} = \frac{\text{Volume}}{\text{SMA}(\text{Volume}, 20)}$
  * **Condition for Long Entry:**
    1. $\text{Close} > \text{Highest}(\text{High}, 20)[1]$ (20-period Donchian breakout / Upper Band break).
    2. $\text{RVOL}_{20} \ge 1.75$ (volume expansion at least $75\%$ above the 20-bar baseline).
    3. $\text{Close} - \text{Open} \ge 0.5 \times (\text{High} - \text{Low})$ (bullish candle body dominance, ensuring buyers closed near the highs rather than printing long upper wicks/rejections).
* **Parameters:**
  * `rvol_window`: `20`
  * `rvol_threshold`: `1.75`
  * `min_body_ratio`: `0.50`

---

#### Proposal 2: Volatility-Climax Exhaustion Exit (Take-Profit Filter)
* **Objective:** Lock in outsized alpha during parabolic expansions (e.g., NEAR's 44.6% daily range runs) without triggering premature stop-outs during normal consolidation.
* **Price Action Logic:**
  * Rather than tightening the underlying stop loss (which previously caused negative backtest scores), trigger a **scaled take-profit (e.g., 50% position close)** when price extends beyond normal statistical distribution boundaries into blow-off territory.
* **Indicators & Formulation:**
  * **Bollinger Bands:** 20-period SMA, 2.0 Standard Deviations ($\sigma$).
  * **RSI (Relative Strength Index):** 14-period.
  * **Climax Condition for Partial Exit:**
    1. $\text{Close} > \text{Upper\_BB}(20, 2.0) + (0.5 \times \text{ATR}(14))$
    2. $\text{RSI}(14) \ge 78$
    3. The current candle prints a rejection signature: $\text{Close} < \text{High} - 0.35 \times (\text{High} - \text{Low})$ (upper wick showing profit-taking after extreme extension).
* **Parameters:**
  * `bb_window`: `20`, `bb_std`: `2.0`
  * `climax_atr_mult`: `0.5`
  * `rsi_threshold`: `78`
  * `partial_exit_size`: `0.50` (leaves remaining 50% to ride trend with baseline trail)

---

### 3. Summary of Expected Benefits
1. **Reduces False Breakout Rate:** The RVOL and body-dominance filter filters out whipsaws that frequently occur when BTC/ETH are in deep squeezes ($>400$ count).
2. **Monetizes High-Beta Outliers:** Safely harvests parabolic gains on assets exhibiting extreme daily ranges (NEAR/SOL) without interfering with the baseline stop-loss architecture.
