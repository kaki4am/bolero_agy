# Strategy V154 - Decoupled Altcoin Squeeze

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy
- *Primary Setup (Decoupled Squeeze Breakout):* Targets altcoins that exhibit relative strength against BTC and volume anomalies.
  - **Entry Filter**: Altcoin 24h Return > (BTC 24h Return + 2.5%) AND Altcoin 24h Volume > SMA(Altcoin 24h Volume, 7).
  - **Entry Signal**: Current Hourly Volume > 1.5x 24H Avg Hourly Volume AND price closes outside the upper Bollinger Band while Bands are expanding.
- *Filters:* Massive PnL bleeders and historically low win-rate pairs (DOGE, AVAX, PEPE, FET, PENDLE, NEAR) heavily blacklisted. No TOD/DOW filters to prevent overfitting. Maintain Defensive Baseline (0.5x risk if BTC 15m trend is DOWN).

## Exit Logic
- **Hold Time Dynamics**: Percent-based trailing stop loss and breakeven rules are ignored during the first 6 hours to prevent premature stop-outs and allow trades to mature.
- **Time-Decaying Take-Profit**: Gradually lower Take-Profit target threshold as hold duration increases beyond 48 hours to accelerate capital recycling.
- **Dynamic Drawdown Floor**: Absolute portfolio-level structural floor (-7.0%) specifically for extended-duration trades (>24h).
- **Stale Trend Exposure Guard**: If an asset is held for > 72 hours and its 1H momentum turns negative (Price < SMA20 1H), trigger an early exit.
- **Portfolio Guard**: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown.
