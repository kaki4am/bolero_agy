# Nightly Strategic Reflection (2026-10-07 09:09:44)

**Recommended Stance:** `SELECTIVE_ROTATION`  
**Posture:** Neutral market conditions. Maintain standard risk caps and focus on filtering noise.

## Realized Account Performance
- **Last 7 Days**: Net PnL: **$-7.49** | Win Rate: **44.4%** | Profit Factor: **0.12** | Fees: **$0.23** (9 trades)
- **Last 30 Days**: Net PnL: **$-17.55** | Win Rate: **47.7%** | Profit Factor: **0.94** | Fees: **$17.1** (197 trades)

## Diagnosed Capital Leaks & Required Fixes
### 1. [HIGH] LEAK_EXCESSIVE_FEE_BURN
- **Evidence**: Paid $17.1 in Binance fees over 197 trades in 30d (avg 6.6 trades/day). Gross PnL was $-0.44.
- **Required Action**: Reduce trade churn. Require higher relative volume confirmation (e.g., VOL_THRESHOLD >= 1.8), wider minimum take profit targets, and filter out low-expectancy chop.

### 2. [HIGH] LEAK_CHRONIC_BLEEDING_PAIRS
- **Evidence**: Specific pairs consistently generating heavy losses: [{'pair': 'POLYXUSDT', 'trades': 2, 'net_pnl': np.float64(-14.06), 'win_rate': np.float64(0.0)}, {'pair': 'ARKUSDT', 'trades': 2, 'net_pnl': np.float64(-12.13), 'win_rate': np.float64(0.0)}, {'pair': 'PUNDIXUSDT', 'trades': 3, 'net_pnl': np.float64(-9.5), 'win_rate': np.float64(0.0)}, {'pair': 'ICPUSDT', 'trades': 3, 'net_pnl': np.float64(-8.89), 'win_rate': np.float64(0.0)}, {'pair': 'RUNEUSDT', 'trades': 3, 'net_pnl': np.float64(-8.64), 'win_rate': np.float64(33.3)}, {'pair': 'AVAUSDT', 'trades': 3, 'net_pnl': np.float64(-8.39), 'win_rate': np.float64(33.3)}, {'pair': 'KAVAUSDT', 'trades': 1, 'net_pnl': np.float64(-7.82), 'win_rate': np.float64(0.0)}, {'pair': 'ILVUSDT', 'trades': 1, 'net_pnl': np.float64(-7.42), 'win_rate': np.float64(0.0)}, {'pair': 'STXUSDT', 'trades': 2, 'net_pnl': np.float64(-7.36), 'win_rate': np.float64(0.0)}, {'pair': 'ALGOUSDT', 'trades': 3, 'net_pnl': np.float64(-6.83), 'win_rate': np.float64(33.3)}, {'pair': 'ARPAUSDT', 'trades': 1, 'net_pnl': np.float64(-6.03), 'win_rate': np.float64(0.0)}, {'pair': 'API3USDT', 'trades': 1, 'net_pnl': np.float64(-5.7), 'win_rate': np.float64(0.0)}]
- **Required Action**: Add these chronic underperformers to the blacklist in restricted_pairs.json.

### 3. [MEDIUM] LEAK_TIME_DECAY_PREMATURE_EXITS
- **Evidence**: 9 trades exited around 18-24 hours at a net loss (total loss: $-24.79).
- **Required Action**: Ensure profit locks do not trigger on losing trades. Allow high-conviction trades breathing room rather than arbitrary calendar cutoff.
