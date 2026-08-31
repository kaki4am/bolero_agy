# Strategy V149 - Trend-Filtered BB Squeeze Breakout

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy
- *Current Primary Setup (Trend_BB_Squeeze):* Close > SMA(30), BB Squeeze Active (Bandwidth < SMA(20) Bandwidth), and Close > Upper BB.
- *Time & Day Filters:* Do not trade during hours 13, 17, 18, 20, 22 or Days 1-3.
- *Trend Filters:* 15m BTC Trend Filter applies.

## Exit Logic
- ATR-based trailing stop loss (3.0 * 1H ATR)
- Take Profit at TAKE_PROFIT%
- Time-based exit: positions held > 24 hours auto-closed
- Portfolio Guard: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown