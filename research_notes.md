- Rejected Volatility-Adjusted ADX Trailing Stop: tightening the stop loss in low ADX caused premature exits and dropped the backtest score from 10.39 to negative.
- Rejected Time-of-Day Filters (excluding hours 13, 17, 20, 22): restricting these hours excluded highly profitable trades, dropping performance significantly.
- Rejected Hard Stop-Loss Cap at -3.0%: Capping the SL at 3% caused premature liquidations during routine volatility, lowering the validation score.
- Rejected lowering BTC down-trend risk exposure to 0.2: backtest showed 0.5 performs better in capturing sudden reversals.

2026-09-06: Rejected ATR-Based Dynamic Stop-Loss (3.0*ATR), DOW/Hour Entry Filters, 72h Hold Limits, 15% Cash Reserve, and new Optuna parameters because they severely degraded out-of-sample forward testing performance compared to the baseline.
