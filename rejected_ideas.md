# Rejected / Tried Ideas Ledger

This is the institutional memory of strategy ideas that have already been TRIED and
REJECTED, with the reason. The nightly committee reads this in full so it does NOT
re-propose ideas that have already failed. Keep entries concise (one line each) and
only append genuinely new rejected ideas.

- Rejected Volatility-Adjusted ADX Trailing Stop: tightening the stop loss in low ADX caused premature exits and dropped the backtest score from 10.39 to negative.
- Rejected Time-of-Day Filters (excluding hours 13, 17, 20, 22): restricting these hours excluded highly profitable trades, dropping performance significantly.
- Rejected Hard Stop-Loss Cap at -3.0%: Capping the SL at 3% caused premature liquidations during routine volatility, lowering the validation score.
- Rejected lowering BTC down-trend risk exposure to 0.2: backtest showed 0.5 performs better in capturing sudden reversals.
- Rejected ATR-Based Dynamic Stop-Loss (3.0*ATR), DOW/Hour Entry Filters, 72h Hold Limits, 15% Cash Reserve, and new Optuna parameters (2026-09-06): severely degraded out-of-sample forward testing performance compared to the baseline.
- Rejected day-of-week and time-of-day filters to avoid overfitting as previously evidenced by out-of-sample forward testing degradation.
- Rejected Time-of-Day and Day-of-Week filters: found to cause severe overfitting and degrade out-of-sample forward testing performance.
- Rejected 4h DRS/Squeeze filters, aggressive trailing stops, and risk multiplier reductions (2026-09-11): severely constrained win rates and degraded relative out-of-sample backtest scores.
- Rejected Time-of-Day filters (hours 13, 17, 20, 22) and Day-of-Week filters: prevent severe overfitting on sparse data; broad time filters fail to adapt to shifting market regimes.
- [Chief Architect] Rejected Tactical Risk Reduction (15m trend), Portfolio Guards, Structural Entry Filters, and TOD/DOW filters to prevent logic contradictions and statistical overfitting.
- Rejected TOD (Time-of-Day) Soft Size Reduction: binary or soft temporal exclusions consistently underperform in forward testing by missing major trend-reversal outliers.
- Rejected Range Expansion entry constraint and Climax Wick Rejection exit (Price Committee): overly constrained the system and degraded the quick validation score from 4.9469 to 3.6730.
- Rejected Candle Location Ratio for entries: backtesting revealed it acted as a severe bottleneck, reducing trade frequency to statistically insignificant levels.
- Rejected Mid-Flight Profit Lock: tightening the trailing stop during high volatility prematurely exits trades before macro trend targets are met.
- Rejected Hold Time caps and TOD/DOW binary filters: cut off positive expectancy generated in 24+ hour holds and risk overfitting.
