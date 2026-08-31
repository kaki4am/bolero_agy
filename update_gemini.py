import re

with open('/root/GEMINI.md', 'r') as f:
    text = f.read()

text = text.replace("# Strategy V148 - Trend Pullback & Downtrend Scalp", "# Strategy V149 - Trend-Filtered BB Squeeze Breakout")

new_strategy = """## Current Active Strategy
- *Current Primary Setup (Trend_BB_Squeeze):* Close > SMA(30), BB Squeeze Active (Bandwidth < SMA(20) Bandwidth), and Close > Upper BB.
- *Time & Day Filters:* Do not trade during hours 13, 17, 18, 20, 22 or Days 1-3.
- *Trend Filters:* 15m BTC Trend Filter applies.

## Exit Logic
- ATR-based trailing stop loss (3.0 * 1H ATR)
- Take Profit at TAKE_PROFIT%
- Time-based exit: positions held > 24 hours auto-closed
- Portfolio Guard: Global Eject at PORTFOLIO_EJECT%, Global Harvest at PORTFOLIO_HARVEST%, Circuit Breaker 4H Pause on >3 Fails or >1% 1H Drawdown"""

text = re.sub(r"## Current Active Strategy.*?## Exit Logic.*?(?=\n\n|\Z)", new_strategy, text, flags=re.DOTALL)

with open('/root/GEMINI.md', 'w') as f:
    f.write(text)

