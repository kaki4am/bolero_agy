### Price Action Analysis: Raw Market Data Characteristics (30d)

1. **Extreme Volatility & Daily Range Dispersion (3.6x Spread)**
   - **Mega-Caps (BTC, ETH):** Low hourly volatility (0.41%–0.55%), tight daily ranges (13.5%–18.5%), and moderate 30d trends (+7.1% to +9.4%).
   - **High-Beta Outliers (NEAR, SOL):** Massive range expansion (NEAR: 48.42% daily range, 1.35% hourly vol; SOL: 24.49% daily range, 0.70% hourly vol) coupled with outsized directional trends (+92.09% and +20.42%).

2. **The Bollinger Band Squeeze Paradox**
   - BTC recorded **539 squeezes** (~18/day) and ETH recorded **440 squeezes** (~15/day).
   - In stark contrast, NEAR recorded only **19 squeezes** across the entire 30 days (<1/day). 
   - **Key Finding:** Once high-momentum altcoins enter an explosive trend regime, their bands remain continuously expanded. Squeeze-dependent entry setups (`Decoupled_Squeeze_Breakout`) severely bottleneck entry frequency into the market's strongest runners.

3. **Trend Efficiency vs. Range Chop**
   - **High Trend Efficiency (`30d Trend% / Daily Range%`):** NEAR (1.90) and SOL (0.83) convert range into net directional alpha.
   - **Low Trend Efficiency (Chop Risk):** LINK exhibits a high daily range (27.98%) but low net trend (+9.99%), yielding an efficiency ratio of only 0.36. Trading unconfirmed breakouts on high-range/low-trend pairs introduces false-breakout whipsaw risk.

4. **Static Volatility Cap Friction**
   - Current static entry cap `VOLATILITY_CAP = 0.015` (1.5%) collides directly with NEAR's baseline hourly volatility of 1.35%. During active breakout hours, legitimate setups on top momentum assets risk being artificially blocked.

---

### Proposed Signals & Filters

#### Proposal 1: Adaptive Relative Volatility Cap (Entry Filter)
* **Type:** Entry Filter (Adaptive Volatility Normalization)
* **Problem Addressed:** The static 1.5% ATR/price cap filters out high-beta leaders (like NEAR) during legitimate expansions, while over-admitting chop on lower-beta assets.
* **Logic:** Dynamically scale `VOLATILITY_CAP` using the asset’s Relative Daily Range ($\text{RDR} = \text{alt\_daily\_range\_pct} / \max(\text{btc\_daily\_range\_pct}, 1.0)$):
  $$\text{PAIR\_VOL\_CAP} = \text{BASE\_CAP} \times \text{clamp}\left(1.0,\, \frac{\text{alt\_daily\_range\_pct}}{\text{btc\_daily\_range\_pct}},\, 1.75\right)$$
* **Parameters:**
  - `BASE_CAP`: 0.015 (1.5%)
  - `MAX_ADAPTIVE_CAP`: 0.026 (2.6%)
  - `MIN_VOLATILITY`: 0.001 (0.1%)
* **Why It Works:** Calibrates risk boundaries to the asset's natural regime—allowing NEAR (1.35% baseline vol) to execute valid continuation setups up to 2.6% ATR without loosening the 1.5% guardrail on BTC and ETH.

---

#### Proposal 2: Trend-Efficiency Breakout (TEB) (Entry Signal)
* **Type:** Entry Signal (`Decoupled_Efficiency_Breakout`)
* **Problem Addressed:** Bypasses the 19-squeeze bottleneck on parabolic runners (NEAR, SOL) by substituting Bollinger Squeeze with Price Action 1h High Breakout + Trend Efficiency, avoiding choppy assets like LINK.
* **Trigger Conditions:**
  1. **Decoupling Regime:** BTC 4h return between -3.0% and +1.0%, with `alt_4h_ret > btc_4h_ret + 3.0%`.
  2. **Structural Alignment:** 1h EMA structure aligned (`cp > ema_20_1h > ema_50_1h`).
  3. **High-Beta & Efficiency Filter:** 
     - Relative Daily Range $\ge 1.6$.
     - Trend Efficiency: $\text{alt\_24h\_ret} / \max(\text{alt\_daily\_range\_pct}, 1.0) \ge 0.35$ (ensures the asset is translating range into directional expansion rather than choppy two-way wicks).
  4. **Price Action Breakout:** Current price crosses above prior 1h candle high (`cp > high_1h_prev`).
  5. **Volume Confirmation:** `hourly_vol > 1.5 * avg_vol`.
* **Parameters:**
  - `RDR_MIN`: 1.6
  - `MIN_TREND_EFFICIENCY`: 0.35
  - `VOL_THRESHOLD`: 1.5
* **Why It Works:** Respects all previous learnings: avoids restrictive candle location bottlenecks, enforces zero arbitrary time-of-day/day-of-week limits, and leaves the proven baseline trailing stop (8% trigger / 3.5% dist) and ATR stop loss (6%–7% band) completely unhindered to capture multi-day positive expectancy.
