### Price Action Analysis: 30-Day Market Regime

#### 1. Market Data Diagnostics
* **Extreme Compression in Anchors vs. Dispersion in High-Beta**:
  * **BTCUSDT & ETHUSDT**: Trapped in prolonged volatility squeezes (`bb_squeeze_count`: 561 and 482; >67–78% of all hourly bars) with modest 30d trends (+9.8% and +12.7%) and tight daily ranges (12.2% and 16.8%).
  * **NEARUSDT & LINKUSDT**: Generating massive decoupling and trend expansion (NEAR: **+164.8% trend**, **58.97% avg daily range**, **1.62% hourly vol**; LINK: **+28.59% trend**, **29.61% daily range**).
  * **The Structural Paradox**: Winning assets like NEAR experienced virtually zero Bollinger squeezes (`bb_squeeze_count`: **5**). They moved in sustained trend momentum rather than recurring coil-and-break cycles.

#### 2. Root Cause of Negative Baseline (-0.1979)
Under Strategy V160, entries trigger when `Altcoin 4h ROC > BTC 4h ROC + 3%`, `RVOL > 1.5x`, and `Price closes outside upper Bollinger Band`.
* In high-volatility environments (daily ranges of 30%–59%), an unconstrained close outside the upper Bollinger Band frequently triggers on **late-stage exhaustion spikes** or **bear-market relief bounces**.
* With a wide initial stop (-6.0% to -7.0%) and trailing stops only activating after +6.0% to +8.0% profit cushion, entering at overextended climax tops causes immediate 4%–7% mean-reversion drawdowns, triggering full initial stops before winners can mature.

---

### Proposed Signals / Filters

To avoid previous failure modes (strict time-of-day filters, brittle candlestick patterns, or premature trailing stops), these two filters directly target entry quality and trend structure:

```
                                 [ Entry Setup Evaluation ]
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
         [ Filter 1: Trend Alignment ]                   [ Filter 2: Momentum Corridor ]
            1h Close > 50 EMA                               52.0 <= 1h RSI(14) <= 75.0
          50 EMA Slope >= Flat                            Avoids Overextended Blow-Offs
                     |                                               |
                     +-----------------------+-----------------------+
                                             |
                                  [ Execute Spot Entry ]
```

#### Proposal 1: 1-Hour Intermediate Trend Alignment Filter (Entry Filter)
* **Rationale**: Eliminates counter-trend fakeouts. Altcoins frequently produce 4-hour relative volume spikes during macro downtrends that promptly fail at structural overhead resistance. Requiring price to hold above an ascending intermediate moving average ensures breakouts occur within established momentum regimes (as observed in NEAR +164% and LINK +28%).
* **Specification**:
  * **Indicator**: 50-period Exponential Moving Average (`EMA_50`) on 1h candles.
  * **Condition**:
    1. $\text{Close}_{\text{1h}} > \text{EMA}_{50}$
    2. $\text{EMA}_{50} \ge \text{EMA}_{50}[1]$ (non-negative slope)
* **Why it avoids past rejections**: It is a continuous, causal structural filter—not a restrictive time/day filter or brittle multi-wick pattern.

#### Proposal 2: RSI Momentum Expansion Corridor (Entry Filter)
* **Rationale**: Prevents buying parabolic climax candles. In high-beta assets with 30%–60% daily ranges, an upper Bollinger Band breach with $\text{RSI} > 75$ represents peak exhaustion, where the statistical probability of an immediate 5%–8% retracement is elevated. Conversely, $\text{RSI} < 52$ lacks legitimate thrust.
* **Specification**:
  * **Indicator**: 14-period Relative Strength Index (`RSI_14`) on 1h close.
  * **Condition**:
    $$52.0 \le \text{RSI}_{14} \le 75.0$$
  * **Floor ($52.0$)**: Confirms buyer dominance and positive momentum velocity.
  * **Ceiling ($75.0$)**: Filters out extreme blow-off wicks, ensuring trades enter during the accumulation/expansion phase rather than the exhaustion climax.
* **Why it avoids past rejections**: Unlike the rejected "Range Expansion" constraint or "Candle Location Ratio", the standard 14-period RSI corridor maintains robust trade frequency while shielding the wide -6% to -7% stop architecture from immediate mean-reversion wicks.
