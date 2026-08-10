# Strategy V114 - MACD Momentum

## Overview
Binance spot trading bot using MACD crossover momentum strategy aligned with trend filters.

## Entry Setups
1. **MACD Momentum**: MACD crosses above Signal Line while MACD > 0, ADX > 25, RSI > 40 and < 70, price > SMA200, volume > vol_sma * 2.0, all trend filters aligned

## Trend Filters (ALL must be true)
- BTC 1h: price > EMA200 (uptrend)
- BTC 15m: price > EMA200 (uptrend)
- Pair 15m: EMA50 > EMA200 with positive slope

## Exit Logic
- ATR-based stop loss (clamped between SL_MIN_PCT and SL_MAX_PCT)
- Take Profit at TAKE_PROFIT%
- Breakeven lock at BE_TRIGGER profit (after 6h min hold)
- Trailing stop at TRAILING_TRIGGER profit with TRAILING_DIST distance
- Time-based exit: positions held > 12 hours auto-closed
- Portfolio Guard: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%

## Risk Management
- Position sizing: risk_pct * equity / SL_distance
- Portfolio scaling: reduces size as concurrent positions grow (SCALE_1/2/3_POS)
- Max trade cap: MAX_RISK_PER_TRADE_PERCENT per position
- Cooldown: COOLDOWN_PERIOD seconds between trades per pair

## Architecture
- `bot.py`: Live trading via WebSocket streams (1m klines)
- `portfolio_backtester.py`: Aligned backtester for parameter optimization
- `tuner.py`: Grid search optimizer (50% recent + 50% historical weighting)
- `ai_manager.py`: Hourly tactical risk adjustments via LLM
- `optimize.sh`: Nightly AI evolution with backtest gate guardrail

## Version History
- V114 (2026-08-09): Critical Fixes & Logic Alignment: Aligned `portfolio_backtester.py` with `bot.py` by incorporating the missing `adx > 25`, `rsi > 40`, and `vol > vol_sma * 2.0` constraints into the MACD Momentum setup, and fixing the adaptive cooldown logic to properly enforce a 4-hour timeout after a losing trade (`last_loss`). These fixes restore 100% logic alignment between the live bot and the backtester.
- V113 (2026-08-08): Critical Fixes & Evolution: Aligned 15m trend filter shift logic (`shift(4)`) and `TAKE_PROFIT` default in `portfolio_backtester.py` to match `bot.py`. Evolved strategy by reducing `TimeExit` to 12 hours and applying stricter entry conditions (`adx > 25`, `rsi > 40`, `vol > vol_sma * 2.0`) to improve simulated PnL from 1.48% to 4.75% (+3.27% absolute improvement).
- V112 (2026-08-07): Critical Fixes & Evolution: Fixed disk I/O error on sqlite WAL pragma. Aligned backtester with live bot by adding missing TAKE_PROFIT logic, fixing TimeExit to 24h instead of 48h, and renaming vwap to sma200. Evolved strategy to require volume > vol_sma * 1.5 for entry breakout confirmation, improving 5-day simulated PnL from -0.73% to +3.68%.
- V111 (2026-08-05): Critical Fix (Logic Alignment): Aligned 15m and 1h macro trend calculations in `bot.py` to exclude unclosed klines, matching the backtester's behavior and avoiding repainting bias.
- V110 (2026-08-04): Critical Fix (Logic Alignment): Aligned `portfolio_backtester.py` ADX filter logic with `bot.py` by removing an outdated `adx < 25` constraint. This discrepancy was artificially depressing simulated backtest returns (-0.69%). After alignment, backtest simulation returns improved significantly (+1.24% PnL over 5-day main test).
- V109 (2026-08-03): Strategy Evolution: Removed restrictive time/day filters to increase trade volume, relaxed ADX momentum filter to > 20, and added RSI < 70 filter to avoid buying local overbought tops.
- V108 (2026-08-01): Critical Fix: Aligned 15m trend filter logic between `bot.py` and `portfolio_backtester.py`. The backtester was using `shift(5)` while the bot used `iloc[-5]`, representing a 1-interval misalignment. Bumped version to V108 to enforce the audited state.
- V107 (2026-07-31): Critical Fixes: Removed the 1.5% hard cap on `TAKE_PROFIT` that was unintentionally crippling the parameterized trailing stop logic. Aligned logic between `portfolio_backtester.py` and `bot.py` by removing legacy `btc_rsi` and volume filters. Resolved logic misalignment in trailing stops where trades were forced to hit TP before trailing could engage, effectively breaking the strategy's risk-reward ratio.
- V106 (2026-07-30): Evolved to V106 MACD Momentum setup. Shifted from mean-reversion pullbacks to strict MACD Momentum crossovers in trending markets. Added ADX filter (>25) and capped TAKE_PROFIT at 1.5% to secure quicker wins. Aligned indicator unpacking and added ADX/MACD calculation in bot.py.
- V105 (2026-07-28): Critical Fixes: Offloaded blocking pandas indicator calculations to an asynchronous thread pool to resolve `BinanceWebsocketQueueOverflow`. Strictly removed restrictive time/day filters from both bot and backtester to fully capture 24/7 momentum. Improved state persistence by using atomic file writes for `active_positions.json`.
- V104 (2026-07-23): Critical Fixes: Moved 24h time-based exit to centralized portfolio guard loop to prevent stuck trades on websocket drops. Fixed DB timezone state persistence bug in `sync_positions_from_db`. Aligned `max_concurrent` risk logic in backtester.
- V103 (2026-07-22): Critical Fix: Added `timestamp` fallback in `sync_positions_from_db` to fix state persistence bug where DB reloads without cache reset the 24-hour time-exit clocks.
- V102 (2026-07-21): Critical logic alignment fixes: Added missing `TAKE_PROFIT` logic to the backtester, aligned 24h time-exit between bot and backtester, and removed day-of-week constraints to capture 24/7 crypto momentum.
- V101 (2026-07-19): Fixed logic misalignment (min_hold_passed) between bot and backtester, resolved TIME EXIT loop for restricted pairs, and improved state persistence for adaptive cooldowns.
- V100 (2026-07-16): Multi-setup momentum (RSI pullback + MACD reversal), 48h time exit, parallelized EMA fetches
- V93 (2026-07-15): agy evolution
- V91 (2026-07-12): agy evolution
- V90 (2026-07-01): Baseline strategy

