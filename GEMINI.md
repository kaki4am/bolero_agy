# Strategy V161 - Volatile Momentum & Decoupling Squeeze

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy (V161)
- *Primary Setup (Decoupled Squeeze Breakout & Trend-Efficiency Breakout):* Targets altcoins that exhibit relative strength against BTC and volume anomalies during periods of BTC consolidation.
  - **Entry Filter**: BTC 4h ROC is between -3.0% and +1.0%, while Altcoin 4h ROC > (BTC 4h ROC + 3.0%).
  - **Entry Signal 1 (Squeeze Breakout)**: Altcoin RVOL > 1.5x AND price closes outside the upper Bollinger Band while Bands are expanding.
  - **Entry Signal 2 (Trend-Efficiency Breakout)**: Relative Daily Range >= 1.6, Trend Efficiency (24h ret / daily range) >= 0.35, aligned EMA trend (20 > 50), and price breaks above previous 1h high.
  - **Volatility Filter**: Adaptive Relative Volatility Cap dynamically scales max allowed volatility based on the asset's daily range vs BTC's daily range.
  - **Risk Scaling**: Risk multiplier scales based on BTC 24h return: 1.0x if >= -1.0%, 0.8x if -3.0% to -1.0%, and 0.5x if <= -3.0%. Hard risk cap enforces maximum 1.5% account equity risk per trade.
- *Filters:* Expanded Tier 1/2/3 statistically validated blacklist. 120-minute re-entry cooldown post-win (unless price pulls back to 20 EMA).

## Exit Logic
- **Profit-Activated Trailing Stop**: Initial stops are kept wide (-6.0% to -7.0%). Trailing stops (-3.5%) only activate once a profit cushion of +6.0% to +8.0% is established.
- **Zombie Exit**: Trades held > 120h that fail to move +1% from entry and suffer declining volume are gracefully closed.
- **Portfolio Guard**: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown.
