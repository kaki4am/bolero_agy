"""
Autonomous Reflection Engine (reflect.py)
Analyzes live bot trading history, equity trajectory, fee burn, and backtest drift.
Produces a structured reflection diagnostic report (reflection_autopsy.json & reflection_autopsy.md)
used by the Nightly AI Committee to self-diagnose and fix strategy leaks.
"""

import sqlite3
import json
import os
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = '/root/trading_bot.db'
POSITIONS_PATH = '/root/active_positions.json'
CONFIG_PATH = '/root/config.json'
AUTOPSY_JSON = '/root/reflection_autopsy.json'
AUTOPSY_MD = '/root/reflection_autopsy.md'

def run_reflection():
    if not os.path.exists(DB_PATH):
        return {"error": "Database not found"}

    conn = sqlite3.connect(DB_PATH)
    trades_df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    conn.close()

    if trades_df.empty:
        return {"status": "No trades to reflect upon"}

    # Pair round-trip trades with full FIFO fee accounting
    symbol_inventory = {}
    realized_trades = []

    for _, row in trades_df.iterrows():
        sym = row['pair']
        side = row['side']
        price = float(row['price'])
        amount = float(row['quantity'])
        fee = float(row['fee']) if row['fee'] is not None else 0.0
        ts = row['timestamp']

        if sym not in symbol_inventory:
            symbol_inventory[sym] = []

        if side == 'BUY':
            symbol_inventory[sym].append({'price': price, 'amount': amount, 'fee': fee, 'ts': ts})
        elif side == 'SELL':
            rem_amt = amount
            cost_basis = 0.0
            buy_fee = 0.0
            entry_ts = None
            while rem_amt > 1e-6 and symbol_inventory[sym]:
                first = symbol_inventory[sym][0]
                if entry_ts is None:
                    entry_ts = first['ts']
                if first['amount'] <= rem_amt + 1e-6:
                    cost_basis += first['amount'] * first['price']
                    buy_fee += first['fee']
                    rem_amt -= first['amount']
                    symbol_inventory[sym].pop(0)
                else:
                    cost_basis += rem_amt * first['price']
                    frac = rem_amt / first['amount']
                    buy_fee += first['fee'] * frac
                    first['amount'] -= rem_amt
                    first['fee'] -= first['fee'] * frac
                    rem_amt = 0.0

            actual_sold = amount - rem_amt
            if actual_sold > 0 and cost_basis > 0:
                proceeds = actual_sold * price
                gross_pnl = proceeds - cost_basis
                net_pnl = gross_pnl - fee - buy_fee
                pnl_pct = (proceeds / cost_basis - 1.0) * 100
                entry_dt = pd.to_datetime(entry_ts)
                exit_dt = pd.to_datetime(ts)
                holding_hours = (exit_dt - entry_dt).total_seconds() / 3600.0

                realized_trades.append({
                    'pair': sym,
                    'entry_ts': entry_ts,
                    'exit_ts': ts,
                    'holding_hours': holding_hours,
                    'cost': cost_basis,
                    'proceeds': proceeds,
                    'gross_pnl': gross_pnl,
                    'fees': fee + buy_fee,
                    'net_pnl': net_pnl,
                    'pnl_pct': pnl_pct
                })

    rdf = pd.DataFrame(realized_trades)
    now = datetime.now()
    cutoff_7d = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cutoff_30d = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

    df_7d = rdf[rdf['exit_ts'] >= cutoff_7d].copy() if not rdf.empty else pd.DataFrame()
    df_30d = rdf[rdf['exit_ts'] >= cutoff_30d].copy() if not rdf.empty else pd.DataFrame()

    def get_stats(df):
        if df.empty:
            return {"trades": 0, "net_pnl": 0.0, "gross_pnl": 0.0, "fees": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "avg_win": 0.0, "avg_loss": 0.0}
        wins = df[df['net_pnl'] > 0]
        losses = df[df['net_pnl'] <= 0]
        win_sum = wins['net_pnl'].sum()
        loss_sum = abs(losses['net_pnl'].sum())
        pf = round(win_sum / loss_sum, 2) if loss_sum > 0 else (999.0 if win_sum > 0 else 0.0)
        return {
            "trades": len(df),
            "net_pnl": round(float(df['net_pnl'].sum()), 2),
            "gross_pnl": round(float(df['gross_pnl'].sum()), 2),
            "fees": round(float(df['fees'].sum()), 2),
            "win_rate": round(float((df['net_pnl'] > 0).mean() * 100), 1),
            "profit_factor": pf,
            "avg_win": round(float(wins['net_pnl'].mean()), 2) if len(wins) else 0.0,
            "avg_loss": round(float(losses['net_pnl'].mean()), 2) if len(losses) else 0.0,
            "avg_hold_h": round(float(df['holding_hours'].mean()), 1)
        }

    stats_7d = get_stats(df_7d)
    stats_30d = get_stats(df_30d)

    # Detect Specific Capital Leaks
    leaks = []
    
    # Leak 1: Excessive Fee Burn
    if stats_30d['trades'] > 50 and stats_30d['fees'] > 15.0:
        leaks.append({
            "code": "LEAK_EXCESSIVE_FEE_BURN",
            "severity": "HIGH",
            "evidence": f"Paid ${stats_30d['fees']} in Binance fees over {stats_30d['trades']} trades in 30d (avg {stats_30d['trades']/30:.1f} trades/day). Gross PnL was ${stats_30d['gross_pnl']}.",
            "recommended_action": "Reduce trade churn. Require higher relative volume confirmation (e.g., VOL_THRESHOLD >= 1.8), wider minimum take profit targets, and filter out low-expectancy chop."
        })

    # Leak 2: Chronic Bleeding Pairs
    worst_pairs = []
    if not df_30d.empty:
        pair_agg = df_30d.groupby('pair').agg(
            trades=('net_pnl', 'count'),
            net_pnl=('net_pnl', 'sum'),
            win_rate=('net_pnl', lambda x: (x > 0).mean() * 100)
        ).sort_values('net_pnl')
        bleeders = pair_agg[(pair_agg['net_pnl'] < -5.0) & (pair_agg['win_rate'] < 35.0)]
        for p, row in bleeders.iterrows():
            worst_pairs.append({"pair": p, "trades": int(row['trades']), "net_pnl": round(row['net_pnl'], 2), "win_rate": round(row['win_rate'], 1)})
        if worst_pairs:
            leaks.append({
                "code": "LEAK_CHRONIC_BLEEDING_PAIRS",
                "severity": "HIGH",
                "evidence": f"Specific pairs consistently generating heavy losses: {worst_pairs}",
                "recommended_action": "Add these chronic underperformers to the blacklist in restricted_pairs.json."
            })

    # Leak 3: Premature Staleness / Time-Stops
    if not df_30d.empty:
        h18_24 = df_30d[(df_30d['holding_hours'] >= 17.5) & (df_30d['holding_hours'] <= 24.5)]
        h18_losses = h18_24[h18_24['net_pnl'] < 0]
        if len(h18_losses) >= 5:
            leaks.append({
                "code": "LEAK_TIME_DECAY_PREMATURE_EXITS",
                "severity": "MEDIUM",
                "evidence": f"{len(h18_losses)} trades exited around 18-24 hours at a net loss (total loss: ${h18_losses['net_pnl'].sum():.2f}).",
                "recommended_action": "Ensure profit locks do not trigger on losing trades. Allow high-conviction trades breathing room rather than arbitrary calendar cutoff."
            })

    # Leak 4: Uncalibrated Risk & Position Sizing
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as cf:
                config = json.load(cf)
        except Exception:
            pass

    max_risk = config.get('MAX_RISK_PER_TRADE_PERCENT', 15.0)
    if max_risk > 22.0:
        leaks.append({
            "code": "LEAK_OVERSIZED_POSITIONS",
            "severity": "CRITICAL",
            "evidence": f"MAX_RISK_PER_TRADE_PERCENT is {max_risk}%. A single 6% stop loss loses {max_risk * 0.06:.2f}% of total account equity.",
            "recommended_action": "Immediately cap MAX_RISK_PER_TRADE_PERCENT <= 18.0% to prevent rapid portfolio drawdowns."
        })

    # Determine System State & Recommended Stance
    if stats_7d['net_pnl'] < -10.0 or stats_30d['profit_factor'] < 0.9:
        recommended_stance = "CAPITAL_PRESERVATION"
        posture_summary = "Bot is in drawdown. Tighten entry filters, cap risk to 15%, restrict chronic bleeders, and focus on high-expectancy trend setups."
    elif stats_7d['net_pnl'] > 10.0 and stats_7d['profit_factor'] > 1.3:
        recommended_stance = "EXPANSION"
        posture_summary = "Strategy is performing well with positive expectancy. Maintain strict discipline on fee drag."
    else:
        recommended_stance = "SELECTIVE_ROTATION"
        posture_summary = "Neutral market conditions. Maintain standard risk caps and focus on filtering noise."

    report = {
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "recommended_stance": recommended_stance,
        "posture_summary": posture_summary,
        "performance_7d": stats_7d,
        "performance_30d": stats_30d,
        "active_leaks_detected": leaks,
        "chronic_bleeding_pairs": worst_pairs,
        "total_lifetime_trades": len(rdf)
    }

    # Write JSON for committee consumption
    with open(AUTOPSY_JSON, 'w') as f:
        json.dump(report, f, indent=4)

    # Write Markdown for human and LLM reading
    md_lines = [
        f"# Nightly Strategic Reflection ({report['timestamp']})",
        "",
        f"**Recommended Stance:** `{recommended_stance}`  ",
        f"**Posture:** {posture_summary}",
        "",
        "## Realized Account Performance",
        f"- **Last 7 Days**: Net PnL: **${stats_7d['net_pnl']}** | Win Rate: **{stats_7d['win_rate']}%** | Profit Factor: **{stats_7d['profit_factor']}** | Fees: **${stats_7d['fees']}** ({stats_7d['trades']} trades)",
        f"- **Last 30 Days**: Net PnL: **${stats_30d['net_pnl']}** | Win Rate: **{stats_30d['win_rate']}%** | Profit Factor: **{stats_30d['profit_factor']}** | Fees: **${stats_30d['fees']}** ({stats_30d['trades']} trades)",
        "",
        "## Diagnosed Capital Leaks & Required Fixes"
    ]

    if not leaks:
        md_lines.append("- No critical capital leaks currently detected. System invariants intact.")
    else:
        for idx, l in enumerate(leaks, 1):
            md_lines.append(f"### {idx}. [{l['severity']}] {l['code']}")
            md_lines.append(f"- **Evidence**: {l['evidence']}")
            md_lines.append(f"- **Required Action**: {l['recommended_action']}")
            md_lines.append("")

    with open(AUTOPSY_MD, 'w') as f:
        f.write("\n".join(md_lines))

    print(f"Reflection completed. Stance: {recommended_stance}. Found {len(leaks)} leaks.")
    return report

def apply_defensive_fixes(report):
    """Auto-heals diagnosed leaks by updating configuration and blacklists."""
    print("Applying autonomous defensive fixes based on reflection...")
    actions_taken = []
    
    # 1. Blacklist chronic bleeders that are not actively held
    active_held = set()
    if os.path.exists(POSITIONS_PATH):
        try:
            with open(POSITIONS_PATH) as pf:
                pdata = json.load(pf)
                active_held = set(pdata.get('active_positions', {}).keys())
        except Exception:
            pass

    restricted_path = '/root/restricted_pairs.json'
    restricted = set()
    if os.path.exists(restricted_path):
        try:
            with open(restricted_path) as rf:
                restricted = set(json.load(rf))
        except Exception:
            pass

    new_blacklist = []
    for bleeder in report.get('chronic_bleeding_pairs', []):
        pair = bleeder['pair']
        if pair not in restricted and pair not in active_held:
            restricted.add(pair)
            new_blacklist.append(pair)

    if new_blacklist:
        with open(restricted_path, 'w') as rf:
            json.dump(sorted(list(restricted)), rf, indent=4)
        actions_taken.append(f"Auto-blacklisted {len(new_blacklist)} chronic bleeding pairs: {', '.join(new_blacklist)}")

    # 2. If in CAPITAL_PRESERVATION, enforce safe risk parameters
    if report.get('recommended_stance') == 'CAPITAL_PRESERVATION':
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as cf:
                    cfg = json.load(cf)
                modified = False
                if cfg.get('MAX_RISK_PER_TRADE_PERCENT', 20.0) > 18.0:
                    cfg['MAX_RISK_PER_TRADE_PERCENT'] = 18.0
                    modified = True
                if cfg.get('BASE_RISK_PERCENT', 2.0) > 1.5:
                    cfg['BASE_RISK_PERCENT'] = 1.5
                    modified = True
                if cfg.get('PROFIT_LOCK_PCT', 0.0025) < 0.005:
                    cfg['PROFIT_LOCK_PCT'] = 0.0075
                    modified = True
                if modified:
                    with open(CONFIG_PATH, 'w') as cf:
                        json.dump(cfg, cf, indent=4)
                    actions_taken.append("Enforced conservative risk caps in config.json (MAX_RISK=18%, BASE_RISK=1.5%, PROFIT_LOCK=0.75%)")
            except Exception as e:
                print(f"Error updating config in defensive fixes: {e}")

    for act in actions_taken:
        print(f"  [HEALED] {act}")
    return actions_taken

if __name__ == "__main__":
    import sys
    report = run_reflection()
    if len(sys.argv) > 1 and sys.argv[1] in ('--auto-heal', '--apply-fixes'):
        apply_defensive_fixes(report)
