### Market Data Analysis (30-Day Characteristics)

1. **Volatility & Squeeze Polarization**:
   - **BTCUSDT & ETHUSDT**: Low hourly volatility (0.45% and 0.64%) and extreme consolidation frequency (**506 and 418 BB squeezes**). They spend significant time coiling in tight ranges.
   - **High-Beta Altcoins (SOL, LINK, NEAR)**: Daily ranges expand rapidly (24.5% to 44.8%), while squeeze occurrences collapse dramatically (SOL: 255, LINK: 181, **NEAR: only 19 squeezes** despite a **+68.69% 30d trend**).
2. **Current Strategy Bottleneck**:
   - The existing entry setup requires a Bollinger Band squeeze expansion (`cp > bb_upper and bb_width > bb_width_prev`).
   - Because premier trend runners (like NEAR) trend persistently without coiling, they register almost zero squeezes (19 in 30 days). A squeeze-only trigger misses high-beta momentum continuation and structural decoupling.
   - Furthermore, NEAR’s average hourly volatility (1.27%) sits near the current 1.5% volatility cap (`VOLATILITY_CAP = 0.015`), frequently blocking valid breakout signals on high-beta leaders.

---

### Proposed Signals & Filters

#### Proposal 1: Relative Range Decoupled Trend Continuation (RRD-TC Entry Signal)
*Bypasses the BB squeeze requirement specifically for confirmed high-beta decouplers that are already in persistent upward expansion.*

* **Objective**: Capture strong momentum trends in assets with high daily range (e.g., SOL, NEAR) that do not form classic BB squeezes.
* **Indicators**:
  - `alt_daily_range_pct` & `btc_daily_range_pct` (24h high-low range %).
  - `EMA(20)` and `EMA(50)` on the 1-hour timeframe.
  - `hourly_volume` vs `vol_1h_avg_24h`.
  - Macro Decoupling: `alt_4h_ret` vs `btc_4h_ret`.
* **Entry Logic**:
  ```python
  # 1. Macro & Beta Decoupling
  relative_range = alt_daily_range_pct / max(btc_daily_range_pct, 1.0)
  is_high_beta_decoupler = relative_range >= 1.6  # (e.g., SOL ~1.75x, NEAR ~3.2x BTC range)
  is_macro_decoupled = (-3.0 <= btc_4h_ret <= 1.0) and (alt_4h_ret > btc_4h_ret + 3.0)

  # 2. Trend & Volume Continuation (No Squeeze Required)
  trend_aligned = cp > ema_20_1h > ema_50_1h
  volume_confirmed = hourly_vol > 1.5 * avg_vol_24h

  # Trigger Setup
  if is_high_beta_decoupler and is_macro_decoupled and trend_aligned and volume_confirmed:
      setup = "Decoupled_Trend_Continuation"
  ```
* **Parameters**:
  - `RDR_MIN = 1.6` (Relative Daily Range threshold)
  - `EMA_FAST = 20`, `EMA_SLOW = 50` (1h trend filter)
  - `VOL_THRESHOLD = 1.5` (Volume confirmation multiplier)

---

#### Proposal 2: Parabolic Volume Climax Take-Profit (PVE-TP Exit Signal)
*Secures gains into peak rotational liquidity on high-range runners before violent mean-reversion pullbacks occur.*

* **Objective**: High-beta assets with >25% daily ranges often experience blow-off tops that retrace 10–15% before the trailing stop (triggered at 8% with 3.5% trail) or the 24h hard time-limit can lock in maximum equity.
* **Indicators**:
  - `profit_pct = (cp - entry_price) / entry_price`
  - Bollinger Band Upper (`length=20, std=2.0`) on 1h timeframe.
  - Hourly Volume Ratio: `hourly_vol / vol_1h_avg_24h`.
  - Candle Rejection: Close relative to high/low range on the completed 1h candle.
* **Exit Logic**:
  ```python
  # 1. Profit qualification (only active once in substantial profit; does not tighten stops early)
  in_profit = profit_pct >= 0.10  # >= +10.0% gain

  # 2. Overextended above Upper Bollinger Band
  price_stretched = cp >= bb_upper_20_2 * 1.02  # 2% above upper band

  # 3. Climax Volume & Upper Wick Exhaustion
  volume_climax = hourly_vol >= 2.5 * avg_vol_24h
  exhaustion_candle = (high_1h - close_1h) > (close_1h - low_1h)  # Upper wick > body/lower range

  if in_profit and price_stretched and volume_climax and exhaustion_candle:
      exit_reason = "Volume_Climax_Harvest"
      # Execute SELL (Take Profit)
  ```
* **Parameters**:
  - `MIN_PROFIT_TRIGGER = 0.10` (+10% threshold)
  - `BB_EXTENSION_PCT = 1.02` (2% band overshoot)
  - `CLIMAX_VOL_MULT = 2.5` (2.5x 24h hourly average volume)
