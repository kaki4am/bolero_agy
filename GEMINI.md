# Strategy V153 - Altcoin Decoupling & Large-Cap Squeeze

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy
- *Primary Setup 1 (Altcoin Decoupling):* Aggressive entry into altcoins when BTC is in a mild consolidation (-3% to +1%). Triggered if Altcoin 1H USD Volume > 1.5x 24H Avg Volume and Price > SMA(20).
- *Primary Setup 2 (LargeCap BB Squeeze):* Targets BTC and ETH. Triggered if BB Width is below 30-period average, Price > Upper BB, and Hourly Volume > 1.5x 24H Avg Hourly Volume.
- *Filters:* Massive PnL bleeders and historically low win-rate pairs heavily blacklisted. No TOD/DOW filters to prevent overfitting. Maintain Defensive Baseline (0.5x risk if BTC 15m trend is DOWN).

## Exit Logic
- Percent-based trailing stop loss without rigid hard caps.
- Take Profit at TAKE_PROFIT%.
- Rejected Hold Limits: No strict time-based exits, allowing winners to run naturally.
- Portfolio Guard: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown.