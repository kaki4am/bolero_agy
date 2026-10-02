# Strategy V161 - Volatile Momentum & Decoupling Squeeze

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy (V161)
- *Primary Setup (Decoupled Squeeze Breakout & Trend Continuation):* Targets altcoins that exhibit relative strength against BTC and volume anomalies during periods of BTC consolidation.
  - **Trend Alignment Filter**: 1h Close > 50 EMA and 50 EMA Slope >= Flat.
  - **Momentum Filter**: 1h RSI(14) between 52.0 and 75.0 to prevent exhaustion entries.
  - **Entry Signal**: Altcoin RVOL > 1.8x, Body-to-Range > 0.40, AND price closes outside the upper Bollinger Band while Bands are expanding.
  - **Risk Scaling**: Risk multiplier scales based on BTC 24h return. Initial stop loss max 7.0%.
- *Filters:* Expanded Tier 1/2/3 statistically validated blacklist. Added highly illiquid and high-frequency churn pairs. Time-of-Day, Day-of-Week, and hard hold-time limits explicitly rejected.

## Exit Logic
- **Profit-Activated Trailing Stop**: Initial stops are kept wide (-6.0% to -7.0%). Trailing stops (-3.5%) only activate once a profit cushion of +6.0% to +8.0% is established.
- **Time-Decay Momentum Check**: Trades held > 48h must maintain positive 24h momentum and strong volume relative to their 7-day average, or else they are gracefully closed for capital rotation.
- **Dynamic Drawdown Floor**: Absolute portfolio-level structural floor (-7.0%) specifically for extended-duration trades (>24h).
- **Portfolio Guard**: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >3.5% 1H Drawdown.
