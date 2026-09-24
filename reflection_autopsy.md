# Nightly Strategic Reflection (2026-09-24 14:44:55)

**Recommended Stance:** `CAPITAL_PRESERVATION`  
**Posture:** Bot is in drawdown. Tighten entry filters, cap risk to 15%, restrict chronic bleeders, and focus on high-expectancy trend setups.

## Realized Account Performance
- **Last 7 Days**: Net PnL: **$73.47** | Win Rate: **52.1%** | Profit Factor: **1.96** | Fees: **$5.21** (48 trades)
- **Last 30 Days**: Net PnL: **$-43.1** | Win Rate: **38.6%** | Profit Factor: **0.89** | Fees: **$23.5** (272 trades)

## Diagnosed Capital Leaks & Required Fixes
### 1. [HIGH] LEAK_EXCESSIVE_FEE_BURN
- **Evidence**: Paid $23.5 in Binance fees over 272 trades in 30d (avg 9.1 trades/day). Gross PnL was $-19.6.
- **Required Action**: Reduce trade churn. Require higher relative volume confirmation (e.g., VOL_THRESHOLD >= 1.8), wider minimum take profit targets, and filter out low-expectancy chop.

### 2. [HIGH] LEAK_CHRONIC_BLEEDING_PAIRS
- **Evidence**: Specific pairs consistently generating heavy losses: [{'pair': 'POLYXUSDT', 'trades': 2, 'net_pnl': np.float64(-14.06), 'win_rate': np.float64(0.0)}, {'pair': 'ARKUSDT', 'trades': 2, 'net_pnl': np.float64(-12.13), 'win_rate': np.float64(0.0)}, {'pair': 'RUNEUSDT', 'trades': 4, 'net_pnl': np.float64(-9.77), 'win_rate': np.float64(25.0)}, {'pair': 'PUNDIXUSDT', 'trades': 3, 'net_pnl': np.float64(-9.5), 'win_rate': np.float64(0.0)}, {'pair': 'VETUSDT', 'trades': 6, 'net_pnl': np.float64(-9.36), 'win_rate': np.float64(16.7)}, {'pair': 'ICPUSDT', 'trades': 6, 'net_pnl': np.float64(-8.94), 'win_rate': np.float64(33.3)}, {'pair': 'AVAUSDT', 'trades': 3, 'net_pnl': np.float64(-8.39), 'win_rate': np.float64(33.3)}, {'pair': 'KAVAUSDT', 'trades': 1, 'net_pnl': np.float64(-7.82), 'win_rate': np.float64(0.0)}, {'pair': 'EGLDUSDT', 'trades': 2, 'net_pnl': np.float64(-7.65), 'win_rate': np.float64(0.0)}, {'pair': 'HEIUSDT', 'trades': 4, 'net_pnl': np.float64(-7.44), 'win_rate': np.float64(0.0)}, {'pair': 'ILVUSDT', 'trades': 1, 'net_pnl': np.float64(-7.42), 'win_rate': np.float64(0.0)}, {'pair': 'LPTUSDT', 'trades': 1, 'net_pnl': np.float64(-6.96), 'win_rate': np.float64(0.0)}, {'pair': 'CVCUSDT', 'trades': 1, 'net_pnl': np.float64(-6.85), 'win_rate': np.float64(0.0)}, {'pair': 'ALGOUSDT', 'trades': 3, 'net_pnl': np.float64(-6.83), 'win_rate': np.float64(33.3)}, {'pair': 'AAVEUSDT', 'trades': 4, 'net_pnl': np.float64(-6.21), 'win_rate': np.float64(25.0)}, {'pair': 'ARPAUSDT', 'trades': 1, 'net_pnl': np.float64(-6.03), 'win_rate': np.float64(0.0)}, {'pair': 'API3USDT', 'trades': 1, 'net_pnl': np.float64(-5.7), 'win_rate': np.float64(0.0)}, {'pair': 'TWTUSDT', 'trades': 2, 'net_pnl': np.float64(-5.57), 'win_rate': np.float64(0.0)}]
- **Required Action**: Add these chronic underperformers to the blacklist in restricted_pairs.json.

### 3. [MEDIUM] LEAK_TIME_DECAY_PREMATURE_EXITS
- **Evidence**: 13 trades exited around 18-24 hours at a net loss (total loss: $-23.79).
- **Required Action**: Ensure profit locks do not trigger on losing trades. Allow high-conviction trades breathing room rather than arbitrary calendar cutoff.
