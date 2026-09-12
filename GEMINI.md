# Strategy V156 - Volatile Momentum & Decoupling Squeeze

## Overview
Binance spot trading bot managed by an autonomous AI agent. The AI has full authority to research, discover, and deploy any statistically profitable entry setups (e.g., trend following, momentum breakouts, capitulation bounces) to maximize PnL and outperform a Bitcoin Buy-and-Hold baseline.

## AI Evolution Mandate (DO NOT REMOVE)
- The AI is authorized to dynamically add, modify, or remove entry setups based on statistical backtest performance and current market regimes.
- The AI must NOT restrict itself to capitulation bounces if momentum or trend strategies offer a higher expectancy.
- Continuous Market Exposure & Capital Rotation: The bot must ALWAYS be active and in at least one trade, but this does NOT mean buying and holding indefinitely. The bot must actively take profits and cut losses to maximize PnL, but it must immediately rotate that capital into new high-probability setups so the portfolio is never sitting 100% in cash.
- The AI is responsible for keeping the "Current Active Strategy" section below updated, but MUST ALWAYS preserve this "AI Evolution Mandate" section so future AIs do not lock themselves into a single strategy.

## Current Active Strategy
- *Primary Setup (Decoupled Squeeze Breakout):* Targets altcoins that exhibit relative strength against BTC and volume anomalies during periods of BTC consolidation.
  - **Entry Filter**: BTC 4h ROC is between -3.0% and +1.0%, while Altcoin 4h ROC > 3.0%.
  - **Entry Signal**: Altcoin RVOL > 2.0x AND price closes outside the upper Bollinger Band while Bands are expanding.
  - **Risk Scaling**: Risk multiplier scales down to 0.75x if BTC 4h drop is >1.5%, and 0.9x if >1.0%. 1.0x maintained for sub-1% dips.
- *Filters:* Expanded blacklist includes low win-rate pairs like ENS, VET, PEOPLE, HFT, ONG, DEXE, SYN, HEI, COTI in addition to previous structural bleeders. Time-of-Day and Day-of-Week filters rejected to prevent overfitting.

## Exit Logic
- **Profit-Activated Trailing Stop**: Initial stops are kept wide (-6.0% to -7.0%). Trailing stops (-3.5%) only activate once a profit cushion of +6.0% to +8.0% is established.
- **Time-Decay Momentum Check**: Trades held > 48h must maintain positive 24h momentum and strong volume relative to their 7-day average, or else they are gracefully closed for capital rotation.
- **Dynamic Drawdown Floor**: Absolute portfolio-level structural floor (-7.0%) specifically for extended-duration trades (>24h).
- **Portfolio Guard**: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown.
