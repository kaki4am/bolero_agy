### Market Data Characteristics Analysis

1. **Volatility & Dispersion Across Assets**:
   - **BTCUSDT & ETHUSDT**: Anchor assets characterized by lower hourly volatility (0.435% and 0.557%), moderate 30-day trends (~16.5% - 17.0%), and high Bollinger Band squeeze frequencies (519 and 422). These serve as the macro baseline.
   - **SOLUSDT & LINKUSDT**: Intermediate high-beta layer with daily ranges expanding to 24.58% - 28.10%, volatility at 0.69% - 0.80%, and squeeze counts dropping by more than half (252 and 179).
   - **NEARUSDT**: Represents extreme momentum outliers in the current regime: 121.71% 30-day trend, 47.25% daily range, and 1.34% hourly volatility. Crucially, **BB squeeze count collapsed to just 19 in 30 days**, demonstrating that sustained parabolic trends spend virtually no time in tight band compression. Strategies overly reliant on squeeze triggers miss the strongest trend continuations.

2. **Key Regime Insights & Past Failure Evaluation**:
   - **Why Previous Price Proposals Failed**: The *Range Expansion* entry constraint over-filtered entries during rapid momentum phases, while the *Climax Wick Rejection* prematurely choked winning trades during normal high-volatility pullbacks (score degraded from 4.9469 to 3.6730).
   - **Current Market Condition**: BTC is expanding strongly above $81,000 (+5.6% to +6.5%), driving aggressive capital rotation into high-beta alts. New proposals must preserve right-tail trend participation without adding restrictive entry bottlenecks or fragile time/wick filters.

---

### Proposed Price Action Logic

#### Proposal 1 (Entry Signal / Filter): Bullish Candle Close Location (CCL) for Trend Continuation
* **Objective**: Replace restrictive range-expansion filters with a lightweight price action filter that confirms buyers possess closing dominance, capturing high-velocity runners (e.g., NEAR, SOL) while filtering out exhaustive topping dojis.
* **Logic**:
  On an hourly candle triggering `Decoupled_Trend_Continuation`:
  $$\text{Candle Location Ratio (CLR)} = \frac{\text{Close}_{1h} - \text{Low}_{1h}}{\text{High}_{1h} - \text{Low}_{1h}}$$
  Require $\text{CLR} \ge \text{MIN\_CANDLE\_CLR}$ (i.e. close must finish in the upper third of the candle range).
* **Parameters**:
  - `MIN_CANDLE_CLR = 0.65` (Close within upper 35% of the 1h range)
  - `MIN_BODY_TO_RANGE = 0.35` (Excludes low-conviction neutral spinning tops / indecision dojis)
* **Rationale**: Strong momentum runners consistently close near bar highs. Unlike wick-rejection exits, requiring candle conviction at the entry point prevents buying into distribution wicks without constraining trade frequency on healthy impulse bars.

---

#### Proposal 2 (Exit Signal): Two-Stage Tiered Trailing Stop (Mid-Flight Profit Lock)
* **Objective**: Prevent mid-sized gains (+5% to +7%) in high-volatility assets (hourly vol > 1%) from round-tripping into stop-outs before reaching the existing 8% trailing trigger or 15.5% take profit.
* **Logic**:
  - **Tier 1 (Mid-Flight Lock)**: When unrealized profit reaches `MID_PROFIT_TRIGGER` (5.0%), ratchet stop loss to lock in modest profit:
    $$\text{SL} = \max(\text{SL}, \text{Entry Price} \times (1 + \text{MID_PROFIT_LOCK}))$$
  - **Tier 2 (Existing Full Trail)**: When unrealized profit reaches `TRAILING_TRIGGER` (8.0%), continue dynamic trailing at `TRAILING_DIST` (3.5% below high price).
* **Parameters**:
  - `MID_PROFIT_TRIGGER = 0.050` (+5.0% unrealized gain)
  - `MID_PROFIT_LOCK = 0.015` (+1.5% locked profit, providing a generous 3.5% cushion to survive routine intraday pullbacks)
* **Rationale**: Unlike the rejected ADX trailing stop (which tightened during low volatility and got whipsawed), this tier activates strictly *after* positive directional momentum is demonstrated, preserving capital against macro BTC reversals while allowing runners the room needed to achieve full 15%+ targets.
