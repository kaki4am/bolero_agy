#!/root/venv/bin/python3
"""
daily_signal_brief.py
Generates an AI-synthesized executive brief of Bolero trading performance,
active positions, AI Manager sentiment, and Nightly Committee governance,
and delivers it via Signal Messenger (or terminal preview).
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv

load_dotenv('/root/.env')

sys.path.append('/root')

CONFIG_FILE = '/root/config.json'
ACTIVE_POS_FILE = '/root/active_positions.json'
TACTICAL_FILE = '/root/tactical_overrides.json'
AUTOPSY_FILE = '/root/reflection_autopsy.md'
RESEARCH_NOTES_FILE = '/root/research_notes.md'
EVOLVER_LOG = '/root/strategy_evolver.log'
CREDIT_GATE_LOG = '/root/gemini_credit_gate.log'
DB_FILE = '/root/trading_bot.db'

def get_live_account_data():
    """Retrieve official Binance Spot balances, active bags, and equity."""
    data = {
        'total_equity': 0.0,
        'usdt_cash': 0.0,
        'positions_value': 0.0,
        'positions': []
    }
    try:
        from trading_utils import get_binance_client
        client = get_binance_client()
        acc = client.get_account()
        
        usdt_free = float([b['free'] for b in acc['balances'] if b['asset'] == 'USDT'][0])
        data['usdt_cash'] = usdt_free
        
        active_positions = {}
        if os.path.exists(ACTIVE_POS_FILE):
            try:
                with open(ACTIVE_POS_FILE) as f:
                    ap_data = json.load(f)
                    active_positions = ap_data.get('active_positions', {})
            except Exception:
                pass

        total_pos_val = 0.0
        for sym, pos in active_positions.items():
            qty = float(pos.get('qty', 0.0))
            ep = float(pos.get('entry_price', 0.0))
            sl = float(pos.get('sl', 0.0))
            setup = pos.get('setup', 'Breakout')
            entry_time = float(pos.get('time', 0.0))
            hold_hours = (datetime.now().timestamp() - entry_time) / 3600.0 if entry_time > 0 else 0.0
            
            try:
                t = client.get_symbol_ticker(symbol=sym)
                cp = float(t['price'])
            except Exception:
                cp = ep
                
            val = qty * cp
            pnl_pct = ((cp - ep) / ep * 100.0) if ep > 0 else 0.0
            total_pos_val += val
            
            data['positions'].append({
                'symbol': sym,
                'qty': qty,
                'entry_price': ep,
                'current_price': cp,
                'val_usdt': val,
                'pnl_pct': pnl_pct,
                'sl_price': sl,
                'hold_hours': hold_hours,
                'setup': setup
            })
            
        data['positions_value'] = total_pos_val
        data['total_equity'] = usdt_free + total_pos_val
    except Exception as e:
        data['error'] = str(e)
        
    return data

def get_performance_stats():
    """Calculate realized PnL and trade metrics for last 24h and 7d from SQLite."""
    stats = {
        'pnl_24h': 0.0,
        'gross_24h': 0.0,
        'fees_24h': 0.0,
        'trades_24h': 0,
        'wins_24h': 0,
        'losses_24h': 0,
        'pnl_7d': 0.0,
        'fees_7d': 0.0,
        'trades_7d': 0,
        'win_rate_7d': 0.0,
        'pnl_30d': 0.0,
        'fees_30d': 0.0,
        'trades_30d': 0,
        'win_rate_30d': 0.0,
        'pnl_v160': 0.0,
        'fees_v160': 0.0,
        'trades_v160': 0,
        'win_rate_v160': 0.0,
        'days_v160': 9.0,
        'recent_exits': []
    }
    
    if not os.path.exists(DB_FILE):
        return stats
        
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY timestamp ASC", conn)
        conn.close()
        
        if df.empty:
            return stats
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        bnb_price = 600.0
        
        # Realized FIFO trades
        realized = []
        for pair in df['pair'].unique():
            pair_trades = df[df['pair'] == pair].sort_values('timestamp')
            buys = []
            for _, row in pair_trades.iterrows():
                raw_fee = float(row['fee']) if row['fee'] is not None else 0.0
                fee_asset = row.get('fee_asset') or 'USDT'
                if fee_asset == 'BNB':
                    fee_usdt = raw_fee * bnb_price
                elif fee_asset != 'USDT' and fee_asset:
                    fee_usdt = raw_fee * float(row['price'])
                else:
                    fee_usdt = raw_fee
                fee_usdt = min(fee_usdt, float(row['price']) * float(row['quantity']) * 0.01)

                if row['side'] == 'BUY':
                    buys.append({
                        'qty': float(row['quantity']),
                        'price': float(row['price']),
                        'fee': fee_usdt,
                        'timestamp': row['timestamp']
                    })
                elif row['side'] == 'SELL':
                    sell_qty = float(row['quantity'])
                    sell_price = float(row['price'])
                    sell_fee = fee_usdt
                    sell_ts = row['timestamp']
                    cycle_qty = 0
                    cycle_cost = 0
                    cycle_buy_fee = 0
                    first_buy_ts = None
                    
                    while sell_qty > 0 and buys:
                        buy = buys[0]
                        match_qty = min(sell_qty, buy['qty'])
                        cycle_qty += match_qty
                        cycle_cost += match_qty * buy['price']
                        frac = match_qty / buy['qty'] if buy['qty'] > 0 else 1.0
                        cycle_buy_fee += buy.get('fee', 0.0) * frac
                        if first_buy_ts is None:
                            first_buy_ts = buy['timestamp']
                        buy['qty'] -= match_qty
                        buy['fee'] = buy.get('fee', 0.0) * (1.0 - frac)
                        sell_qty -= match_qty
                        if buy['qty'] <= 0.0001:
                            buys.pop(0)

                    if cycle_qty > 0:
                        avg_buy = cycle_cost / cycle_qty
                        gross = (sell_price - avg_buy) * cycle_qty
                        tot_fees = cycle_buy_fee + sell_fee
                        net = gross - tot_fees
                        pnl_pct = ((sell_price - avg_buy) / avg_buy) * 100.0
                        hold_h = (sell_ts - first_buy_ts).total_seconds() / 3600.0 if first_buy_ts else 0.0
                        realized.append({
                            'pair': pair,
                            'sell_ts': sell_ts,
                            'net': net,
                            'gross': gross,
                            'fees': tot_fees,
                            'pnl_pct': pnl_pct,
                            'hold_hours': hold_h
                        })

        if not realized:
            return stats
            
        rdf = pd.DataFrame(realized)
        rdf['sell_ts'] = pd.to_datetime(rdf['sell_ts'])
        now = datetime.now()
        
        # 24 hours
        sub24 = rdf[rdf['sell_ts'] >= (now - timedelta(days=1))]
        if not sub24.empty:
            stats['pnl_24h'] = float(sub24['net'].sum())
            stats['gross_24h'] = float(sub24['gross'].sum())
            stats['fees_24h'] = float(sub24['fees'].sum())
            stats['trades_24h'] = len(sub24)
            stats['wins_24h'] = len(sub24[sub24['net'] > 0])
            stats['losses_24h'] = len(sub24[sub24['net'] <= 0])
            
        # 7 days
        sub7 = rdf[rdf['sell_ts'] >= (now - timedelta(days=7))]
        if not sub7.empty:
            stats['pnl_7d'] = float(sub7['net'].sum())
            stats['fees_7d'] = float(sub7['fees'].sum())
            stats['trades_7d'] = len(sub7)
            w7 = len(sub7[sub7['net'] > 0])
            stats['win_rate_7d'] = (w7 / len(sub7) * 100.0)

        # 30 days
        sub30 = rdf[rdf['sell_ts'] >= (now - timedelta(days=30))]
        if not sub30.empty:
            stats['pnl_30d'] = float(sub30['net'].sum())
            stats['fees_30d'] = float(sub30['fees'].sum())
            stats['trades_30d'] = len(sub30)
            w30 = len(sub30[sub30['net'] > 0])
            stats['win_rate_30d'] = (w30 / len(sub30) * 100.0)

        # Since Strategy V160 deployment (Sep 21, 2026 11:28:35 UTC)
        v160_start = pd.to_datetime('2026-09-21 11:28:35')
        sub_v160 = rdf[rdf['sell_ts'] >= v160_start]
        stats['days_v160'] = max((now - v160_start).total_seconds() / 86400.0, 1.0)
        if not sub_v160.empty:
            stats['pnl_v160'] = float(sub_v160['net'].sum())
            stats['fees_v160'] = float(sub_v160['fees'].sum())
            stats['trades_v160'] = len(sub_v160)
            w_v160 = len(sub_v160[sub_v160['net'] > 0])
            stats['win_rate_v160'] = (w_v160 / len(sub_v160) * 100.0)
            
        # Recent 5 exits
        for _, r in rdf.sort_values('sell_ts', ascending=False).head(5).iterrows():
            stats['recent_exits'].append({
                'pair': r['pair'],
                'net': r['net'],
                'pnl_pct': r['pnl_pct'],
                'hold_h': r['hold_hours'],
                'time': r['sell_ts'].strftime('%m-%d %H:%M')
            })
            
    except Exception as e:
        stats['error'] = str(e)
        
    return stats

def calculate_capital_projections(total_equity: float, stats: dict) -> tuple:
    """
    Computes deterministic multi-year compounding projections (1, 2, 3, 5, 10 years)
    based on empirical Bolero performance across:
    1. 30-Day Sustained Pace (full cycle baseline)
    2. V160 Decoupled Squeeze (since Sep 21 inception)
    3. 7-Day Sprint Pace
    """
    equity = max(float(total_equity), 1.0)
    pnl_30d = stats.get('pnl_30d', 0.0)
    pnl_v160 = stats.get('pnl_v160', 0.0)
    days_v160 = stats.get('days_v160', 9.0)
    pnl_7d = stats.get('pnl_7d', 0.0)

    # 1. 30-day rate & CAGR
    r30 = pnl_30d / equity
    cagr_30 = ((1.0 + r30) ** 12.0) - 1.0 if r30 > -1.0 else 0.0

    # 2. V160 normalized monthly rate & tempered CAGR
    r_v160_raw = pnl_v160 / equity
    # Tempered realistic cycle CAGR (15% monthly to account for bear markets/consolidation):
    cagr_v160_tempered = ((1.0 + 0.15) ** 12.0) - 1.0

    # 3. 7-day rate & annual run-rate
    r7 = pnl_7d / equity
    cagr_7 = ((1.0 + r7) ** 52.14) - 1.0 if r7 > -1.0 else 0.0

    # Project years [1, 2, 3, 5, 10]
    years = [1, 2, 3, 5, 10]
    proj_30d = {y: equity * ((1.0 + cagr_30) ** y) for y in years}
    proj_v160 = {y: equity * ((1.0 + cagr_v160_tempered) ** y) for y in [1, 2, 3, 5]}
    proj_7d = {y: equity * ((1.0 + min(cagr_7, 10.0)) ** y) for y in [1, 2]}

    projections_data = {
        'starting_equity': equity,
        'rate_30d': r30,
        'cagr_30d': cagr_30,
        'proj_30d': proj_30d,
        'rate_v160_raw': r_v160_raw,
        'days_v160': days_v160,
        'cagr_v160_tempered': cagr_v160_tempered,
        'proj_v160': proj_v160,
        'rate_7d': r7,
        'proj_7d': proj_7d
    }

    # Format strictly for Signal & Email (no asterisks, clean bullets, uppercase headers, spyglass emoji)
    block_lines = [
        "🔭 LONG-TERM CAPITAL PROJECTIONS",
        f"Starting Baseline: ${equity:,.2f} (Live Spot Equity)",
        "",
        f"• 30-DAY SUSTAINED PACE (+{r30*100:.1f}%/mo | +{cagr_30*100:.1f}% Annual CAGR):",
        f"  1 Year:   ${proj_30d[1]:,.0f}",
        f"  2 Years:  ${proj_30d[2]:,.0f}",
        f"  3 Years:  ${proj_30d[3]:,.0f}",
        f"  5 Years:  ${proj_30d[5]:,.0f}",
        f"  10 Years: ${proj_30d[10]:,.0f}",
        "",
        f"• V160 DECOUPLED SQUEEZE (+{r_v160_raw*100:.1f}% in {days_v160:.0f}d | Tempered 15%/mo):",
        f"  1 Year:   ${proj_v160[1]:,.0f}",
        f"  2 Years:  ${proj_v160[2]:,.0f}",
        f"  3 Years:  ${proj_v160[3]:,.0f}",
        f"  5 Years:  ${proj_v160[5]:,.0f}",
        "  10 Years: Spot altcoin liquidity ceiling reached ($500k-$1M max pool)",
        "",
        f"• 7-DAY SPRINT (+{r7*100:.1f}% in 7d):",
        f"  1 Year:   ${proj_7d[1]:,.0f}",
        f"  2 Years:  ${proj_7d[2]:,.0f}"
    ]
    formatted_block = "\n".join(block_lines)

    return projections_data, formatted_block

def get_market_and_system_health():
    """Inspect BTC market regime, systemd daemon states, and circuit breaker."""
    health = {
        'btc_4h_ret': 0.0,
        'btc_24h_ret': 0.0,
        'trading_bot_service': 'unknown',
        'optimizer_service': 'unknown',
        'active_version': 'V160'
    }
    
    # Read GEMINI.md active version
    try:
        with open('/root/GEMINI.md') as f:
            for line in f:
                if 'Strategy V' in line:
                    health['active_version'] = line.strip().replace('#', '').strip()
                    break
    except Exception:
        pass

    # Check systemd services
    try:
        res = subprocess.run(['systemctl', 'is-active', 'trading-bot.service'], capture_output=True, text=True)
        health['trading_bot_service'] = res.stdout.strip()
        res2 = subprocess.run(['systemctl', 'is-active', 'backtest-optimizer.service'], capture_output=True, text=True)
        health['optimizer_service'] = res2.stdout.strip()
    except Exception:
        pass

    # Get recent BTC return from bot logs
    try:
        j_res = subprocess.run(['journalctl', '-u', 'trading-bot.service', '-n', '25', '--no-pager'], capture_output=True, text=True)
        for line in j_res.stdout.splitlines()[::-1]:
            if 'BTC 4h Return:' in line:
                health['btc_status_line'] = line.split('python')[-1].strip() if 'python' in line else line.strip()
                break
    except Exception:
        pass

    return health

def get_ai_governance_intel():
    """Gather what the AI Manager and Nightly Committee have been doing."""
    intel = {
        'ai_manager': {},
        'nightly_committee': {}
    }
    
    # 1. AI Manager tactical overrides & sentiment
    if os.path.exists(TACTICAL_FILE):
        try:
            with open(TACTICAL_FILE) as f:
                t_data = json.load(f)
                intel['ai_manager']['risk_multiplier'] = t_data.get('RISK_MULTIPLIER', 1.0)
                intel['ai_manager']['rationale'] = t_data.get('rationale', 'Normal market posture.')
                intel['ai_manager']['whitelist'] = t_data.get('whitelist_add', [])
                intel['ai_manager']['confidence'] = t_data.get('confidence', 0.8)
        except Exception:
            pass

    # 2. Nightly Committee autopsy & latest findings
    if os.path.exists(AUTOPSY_FILE):
        try:
            with open(AUTOPSY_FILE) as f:
                lines = f.readlines()[:25]
                intel['nightly_committee']['autopsy_summary'] = "".join(lines)
        except Exception:
            pass

    # Check credit gate status
    if os.path.exists(CREDIT_GATE_LOG):
        try:
            with open(CREDIT_GATE_LOG) as f:
                last_line = f.readlines()[-1].strip()
                intel['nightly_committee']['credit_gate'] = last_line
        except Exception:
            pass

    # Check strategy evolver recent lines
    if os.path.exists(EVOLVER_LOG):
        try:
            with open(EVOLVER_LOG) as f:
                tail = f.readlines()[-30:]
                intel['nightly_committee']['recent_evolver_log'] = "".join(tail)
        except Exception:
            pass

    return intel

def clean_for_signal(text: str) -> str:
    """Strip markdown asterisks, enforce spyglass emoji instead of magic balls, and format cleanly."""
    import re
    # Enforce spyglass emoji instead of crystal ball
    cleaned = text.replace('🔮', '🔭')
    # Remove markdown bold/italic asterisks
    cleaned = cleaned.replace('**', '').replace('*', '')
    # Remove header hashes if any
    cleaned = re.sub(r'^#+\s*', '', cleaned, flags=re.MULTILINE)
    # Normalize multiple blank lines to at most two
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def generate_ai_narrative(context_json: str, formatted_projections: str = "") -> str:
    """Invokes agy to write an insightful, executive Signal briefing."""
    prompt = f"""You are the Chief AI Officer managing the Bolero Binance spot trading bot.
Write a concise, insightful daily update for the fund owner delivered over Signal Messenger.

STRICT FORMATTING RULES:
- DO NOT USE ASTERISKS (*) OR DOUBLE ASTERISKS (**) ANYWHERE IN YOUR OUTPUT. Signal displays them as literal characters and they look messy.
- DO NOT USE MAGIC CRYSTAL BALL EMOJIS (🔮). If referring to projections or future horizons, use the SPYGLASS EMOJI (🔭).
- Use EMOJIS and UPPERCASE for headers and emphasis (e.g. 🤖 EXECUTIVE SUMMARY, 💰 PORTFOLIO & 24H PERFORMANCE).
- Use clean unicode bullet points (•) for lists.
- Avoid markdown hashes (#).

REQUIRED SECTIONS IN YOUR BRIEF:
1. 🤖 EXECUTIVE SUMMARY & OPINION: A 2-3 sentence punchy takeaway on current performance, risk posture, and your assessment of current market conditions.
2. 💰 PORTFOLIO & 24H PERFORMANCE: Total spot equity, free cash vs bag deployment %, 24h realized PnL (net & gross), fees paid, win rate, and 7-day trend.
3. 🎯 ACTIVE BAGS & RISK EXPOSURE: Breakdown of current positions (coin, hold time, unrealized PnL %, setup, stop-loss).
4. 🧠 AI MANAGER INTEL: What the hourly AI Manager discovered (Reddit/market sentiment, risk multiplier, whitelisted narrative coins, confidence).
5. 🏛️ NIGHTLY COMMITTEE & STRATEGY STATUS: What the committee concluded (diagnosed leaks, reflection stance, whether evolutions passed or were gated/rolled back, active version).
6. 🔭 24H FORWARD OUTLOOK: 1-2 key things to monitor today (e.g. BTC breakout levels, fee discipline, trailing stops).
7. 🔭 LONG-TERM CAPITAL PROJECTIONS: Multi-year compounding projections (1, 2, 3, 5, 10 years) based on Bolero's empirical performance across 30-day pace, V160 deployment, and 7-day sprint. Present the projections using the exact figures from RAW SYSTEM DATA under capital_projections.

RAW SYSTEM DATA:
{context_json}
"""
    try:
        # Run agy to synthesize the brief
        cmd = [
            '/root/.local/bin/agy',
            '--dangerously-skip-permissions',
            '--print-timeout', '3m0s',
            '--print', prompt
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode == 0 and res.stdout.strip():
            cleaned = clean_for_signal(res.stdout.strip())
            if "LONG-TERM CAPITAL PROJECTIONS" not in cleaned and formatted_projections:
                cleaned += f"\n\n{formatted_projections}"
            return cleaned
        else:
            sys.stderr.write(f"agy error: {res.stderr}\n")
    except Exception as e:
        sys.stderr.write(f"Failed to generate agy narrative: {e}\n")

    # Fallback template if agy is unavailable
    fallback = "Bolero Daily Briefing: Raw data collected but AGY synthesis was unavailable."
    if formatted_projections:
        fallback += f"\n\n{formatted_projections}"
    return fallback

def send_signal_message(message_text: str, recipient: str = None, sender_account: str = None) -> bool:
    """Dispatches the generated briefing via signal-cli."""
    # Check environment or config
    recipient = recipient or os.getenv('SIGNAL_RECIPIENT')
    sender_account = sender_account or os.getenv('SIGNAL_ACCOUNT')

    if not recipient or not sender_account:
        print("[!] SIGNAL_RECIPIENT or SIGNAL_ACCOUNT not specified.")
        print("[!] Set them in /root/.env or pass as arguments.")
        return False

    cmd = [
        '/usr/local/bin/signal-cli',
        '-a', sender_account,
        'send',
        '-m', message_text,
        recipient
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            print("[+] Signal message successfully sent!")
            return True
        else:
            print(f"[-] signal-cli send failed: {res.stderr}")
            return False
    except Exception as e:
        print(f"[-] Signal execution error: {e}")
        return False

def send_email_message(subject: str, message_text: str, recipient: str = None) -> bool:
    """Dispatches the generated briefing via Gmail SMTP."""
    user = os.getenv('GMAIL_USER')
    password = os.getenv('GMAIL_PASS')
    recipient = recipient or os.getenv('GMAIL_RECIPIENT') or user

    if not user or not password:
        print("[!] GMAIL_USER or GMAIL_PASS not specified in /root/.env")
        return False

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Bolero Chief AI Officer <{user}>"
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(message_text, 'plain', 'utf-8'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
        server.login(user, password)
        server.sendmail(user, [recipient], msg.as_string())
        server.quit()
        print(f"[+] Email briefing successfully sent to {recipient}!")
        return True
    except Exception as e:
        print(f"[-] Gmail send failed: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bolero Daily Briefing & Projections Generator")
    parser.add_argument('--send', action='store_true', help="Send the message via Signal (requires configured recipient)")
    parser.add_argument('--email', action='store_true', help="Send the message via Gmail (requires configured GMAIL_USER/PASS)")
    parser.add_argument('--recipient', type=str, help="Signal recipient phone number (e.g. +1234567890)")
    parser.add_argument('--email-to', type=str, help="Email recipient address (defaults to GMAIL_USER in .env)")
    parser.add_argument('--sender', type=str, help="Signal sender account/number registered in signal-cli")
    parser.add_argument('--preview', action='store_true', default=True, help="Print message to stdout")
    args = parser.parse_args()

    print("[*] Gathering Bolero live portfolio metrics...")
    account_data = get_live_account_data()
    
    print("[*] Calculating trade performance from SQLite database...")
    perf_data = get_performance_stats()

    print("[*] Calculating multi-year capital compounding projections...")
    projections_data, formatted_projections = calculate_capital_projections(
        account_data.get('total_equity', 0.0), perf_data
    )
    
    print("[*] Inspecting market regime and system health...")
    health_data = get_market_and_system_health()
    
    print("[*] Reading AI Manager sentiment & Nightly Committee logs...")
    gov_data = get_ai_governance_intel()

    full_context = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'portfolio': account_data,
        'performance': perf_data,
        'capital_projections': projections_data,
        'health_and_market': health_data,
        'governance': gov_data
    }

    print("[*] Invoking agy to generate executive narrative and projections...")
    narrative = generate_ai_narrative(json.dumps(full_context, indent=2), formatted_projections)

    if args.preview or (not args.send and not args.email):
        print("\n" + "="*50 + " GENERATED BRIEF " + "="*50)
        print(narrative)
        print("="*124 + "\n")

    if args.send:
        send_signal_message(narrative, recipient=args.recipient, sender_account=args.sender)

    if args.email:
        subject = f"Bolero Daily Executive Brief - {datetime.now().strftime('%Y-%m-%d')}"
        send_email_message(subject, narrative, recipient=args.email_to)

if __name__ == '__main__':
    main()
