# Strategy V100 - Multi-Setup Momentum

## Overview
Binance spot trading bot using multi-timeframe momentum strategy with two entry setups.

## Entry Setups
1. **RSI Pullback**: RSI(14) crosses above 30 from below, price > SMA200, all trend filters aligned
2. **MACD Histogram Reversal**: MACD histogram turns positive from negative, RSI < 60, all trend filters aligned

## Trend Filters (ALL must be true)
- BTC 1h: price > EMA200 (uptrend)
- BTC 15m: price > EMA200 (uptrend)
- Pair 15m: EMA50 > EMA200 with positive slope

## Exit Logic
- ATR-based stop loss (clamped between SL_MIN_PCT and SL_MAX_PCT)
- Breakeven lock at BE_TRIGGER profit
- Trailing stop at TRAILING_TRIGGER profit with TRAILING_DIST distance
- Time-based exit: positions held > 48 hours auto-closed
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
- V100 (2026-07-16): Multi-setup momentum (RSI pullback + MACD reversal), 48h time exit, parallelized EMA fetches
- V99 (2026-07-16): RSI pullback only (agy evolution)
- V93 (2026-07-15): agy evolution
- V91 (2026-07-12): agy evolution
- V90 (2026-07-01): Baseline strategy
