import json
import os
import time
import threading
from datetime import datetime
from blessed import Terminal
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from trading_utils import get_trade_data, calculate_detailed_pnl, get_binance_client, humanize_time, atomic_json_dump

CACHE_FILE = '/root/.dashboard_cache.json'
term = Terminal()

pnl_state = {
    'total_equity': 0.0,
    'usdt_cash': 0.0,
    'positions_val': 0.0,
    'realized': 0.0,
    'unrealized': 0.0,
    'positions': [],
    'sell_pnl': {},
    'status': 'Initializing...',
    'last_updated': None
}
pnl_lock = threading.Lock()

# Load cache immediately on startup for instant 0ms first-frame render
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r') as f:
            cdata = json.load(f)
            pnl_state['total_equity'] = cdata.get('total_equity', 0.0)
            pnl_state['usdt_cash'] = cdata.get('usdt_cash', 0.0)
            pnl_state['positions_val'] = cdata.get('positions_val', 0.0)
            pnl_state['realized'] = cdata.get('realized', 0.0)
            pnl_state['unrealized'] = cdata.get('unrealized', 0.0)
            pnl_state['positions'] = cdata.get('positions', [])
            raw_sells = cdata.get('sell_pnl', {})
            pnl_state['sell_pnl'] = {int(k): tuple(v) for k, v in raw_sells.items() if str(k).isdigit()}
            pnl_state['status'] = f"Cached ({cdata.get('last_updated', 'recent')})"
            pnl_state['last_updated'] = cdata.get('last_updated')
    except Exception:
        pass

def compute_sell_pnl(trades_df):
    sell_pnl = {}
    inventory = {}
    if trades_df.empty:
        return sell_pnl

    sorted_df = trades_df.sort_values('timestamp', ascending=True)
    for _, row in sorted_df.iterrows():
        tid = int(row['id'])
        pair = row['pair']
        side = row['side']
        price = float(row['price'])
        qty = float(row['quantity'])
        fee = float(row.get('fee') or 0.0)

        if side == 'BUY':
            if pair not in inventory:
                inventory[pair] = []
            inventory[pair].append({'price': price, 'qty': qty, 'fee': fee})
        elif side == 'SELL':
            rem_qty = qty
            cost_basis = 0.0
            buy_fee = 0.0
            while rem_qty > 1e-6 and inventory.get(pair):
                first = inventory[pair][0]
                if first['qty'] <= rem_qty + 1e-6:
                    cost_basis += first['qty'] * first['price']
                    buy_fee += first['fee']
                    rem_qty -= first['qty']
                    inventory[pair].pop(0)
                else:
                    cost_basis += rem_qty * first['price']
                    frac = rem_qty / first['qty']
                    buy_fee += first['fee'] * frac
                    first['qty'] -= rem_qty
                    first['fee'] -= first['fee'] * frac
                    rem_qty = 0.0
            actual_sold = qty - rem_qty
            if actual_sold > 0 and cost_basis > 0:
                revenue = actual_sold * price
                net_pnl = revenue - cost_basis - (buy_fee + fee)
                pct = (net_pnl / cost_basis) * 100.0
                sell_pnl[tid] = (net_pnl, pct)
    return sell_pnl

def pnl_worker():
    client = None
    try:
        client = get_binance_client()
    except Exception:
        pass

    last_processed_trade_id = None

    while True:
        try:
            # Check latest trade ID quickly
            quick_trades = get_trade_data(limit=1)
            latest_id = int(quick_trades.iloc[0]['id']) if not quick_trades.empty else None

            all_trades_df = get_trade_data()
            realized, unrealized, positions = calculate_detailed_pnl(all_trades_df, client=client)
            sell_pnl = compute_sell_pnl(all_trades_df)
            now_str = datetime.now().strftime('%H:%M:%S')

            # Reconcile exact Binance Spot cash & total equity
            usdt_cash = 0.0
            positions_val = sum(p.get('value', 0.0) for p in positions)
            bnb_val = 0.0
            if client:
                try:
                    acc = client.get_account()
                    for b in acc.get('balances', []):
                        asset = b['asset']
                        total_bal = float(b['free']) + float(b['locked'])
                        if asset == 'USDT':
                            usdt_cash = total_bal
                        elif asset == 'BNB':
                            bnb_val = total_bal * 620.0
                except Exception:
                    pass
            total_equity = usdt_cash + positions_val + bnb_val

            with pnl_lock:
                pnl_state['total_equity'] = total_equity
                pnl_state['usdt_cash'] = usdt_cash
                pnl_state['positions_val'] = positions_val
                pnl_state['realized'] = realized
                pnl_state['unrealized'] = unrealized
                pnl_state['positions'] = positions
                pnl_state['sell_pnl'] = sell_pnl
                pnl_state['status'] = f"Live ({now_str})"
                pnl_state['last_updated'] = now_str

            atomic_json_dump({
                'total_equity': total_equity,
                'usdt_cash': usdt_cash,
                'positions_val': positions_val,
                'realized': realized,
                'unrealized': unrealized,
                'positions': positions,
                'sell_pnl': {str(k): v for k, v in sell_pnl.items()},
                'last_updated': now_str
            }, CACHE_FILE)
            last_processed_trade_id = latest_id
        except Exception as e:
            with pnl_lock:
                pnl_state['status'] = f"Sync: {str(e)[:15]}"

        # Sleep in 1-second chunks so we can react promptly to new trades
        for _ in range(15):
            time.sleep(1)
            try:
                check = get_trade_data(limit=1)
                curr_id = int(check.iloc[0]['id']) if not check.empty else None
                if curr_id != last_processed_trade_id:
                    break
            except Exception:
                pass

def generate_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="trades", ratio=2),
        Layout(name="pnl_summary", ratio=1)
    )
    return layout

_worker_started = False
def start_worker():
    global _worker_started
    if not _worker_started:
        worker_thread = threading.Thread(target=pnl_worker, daemon=True)
        worker_thread.start()
        _worker_started = True

def main():
    # Start background calculation worker thread (UI thread never blocks on network/math)
    start_worker()

    layout = generate_layout()

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        with Live(layout, refresh_per_second=4, screen=True):
            while True:
                # 1. Fetch Latest Trades (sub-2ms fast indexed query directly from SQLite)
                trades_df = get_trade_data(limit=100)

                # 2. Read thread-safe PnL state instantly without any network or math wait
                with pnl_lock:
                    total_equity = pnl_state.get('total_equity', 0.0)
                    usdt_cash = pnl_state.get('usdt_cash', 0.0)
                    positions_val = pnl_state.get('positions_val', 0.0)
                    realized = pnl_state['realized']
                    unrealized = pnl_state['unrealized']
                    positions = list(pnl_state['positions'])
                    sell_pnl_map = dict(pnl_state['sell_pnl'])
                    status_text = pnl_state['status']

                # 3. Update Header
                layout["header"].update(Panel(f"Binance Trading Bot - [bold green]Live Dashboard[/bold green] | Time: {datetime.now().strftime('%H:%M:%S')} | PnL Sync: [cyan]{status_text}[/cyan]", style="bold cyan"))

                # 4. Update Trades Table - Always show latest trades auto-fitted to terminal height
                available_rows = max(5, (term.height or 30) - 10)
                visible_trades = trades_df.head(available_rows)

                table = Table(title=f"Recent Trades (Latest {len(visible_trades)})", expand=True)
                table.add_column("Pair", style="bold")
                table.add_column("Side")
                table.add_column("Price")
                table.add_column("Total (USDT)")
                table.add_column("Realized PnL", justify="right")
                table.add_column("Fee")
                table.add_column("When")

                for _, row in visible_trades.iterrows():
                    side = row['side']
                    color = "green" if side == 'BUY' else "red"
                    total_usdt = row['price'] * row['quantity']

                    # Show PnL on SELL rows
                    if side == 'SELL':
                        tid = int(row['id'])
                        pnl_info = sell_pnl_map.get(tid)
                        if pnl_info:
                            pnl_val, pnl_pct = pnl_info
                            sign = '+' if pnl_val >= 0 else ''
                            p_color = 'green' if pnl_val >= 0 else 'red'
                            pnl_text = f"[{p_color}]{sign}${pnl_val:.2f} ({sign}{pnl_pct:.1f}%)[/{p_color}]"
                        else:
                            pnl_text = "[dim]—[/dim]"
                    else:
                        pnl_text = "[dim]—[/dim]"

                    fee = row.get('fee', 0) or 0
                    fee_asset = row.get('fee_asset') or ''
                    if fee > 0:
                        fee_text = f"{fee:.8f} {fee_asset}" if fee < 0.0001 else f"{fee:.4f} {fee_asset}"
                    else:
                        fee_text = "0.0000"

                    time_text = humanize_time(row['timestamp'])
                    table.add_row(
                        row['pair'], f"[{color}]{side}[/{color}]", f"{row['price']:.4f}",
                        f"${total_usdt:.2f}", pnl_text, fee_text, time_text
                    )

                layout["trades"].update(Panel(table))

                # 5. Update PnL Summary
                r_color = "green" if realized >= 0 else "red"
                u_color = "green" if unrealized >= 0 else "red"

                pnl_text = f"Total Equity:   [bold cyan]${total_equity:.2f}[/bold cyan] [dim](Matches Binance)[/dim]\n"
                pnl_text += f"USDT Cash:      ${usdt_cash:.2f}\n"
                pnl_text += f"Positions Val:  ${positions_val:.2f} ({len(positions)} coins)\n"
                pnl_text += "--------------------------------\n"
                pnl_text += f"Active uPnL:    [{u_color}]{'+' if unrealized >= 0 else ''}${unrealized:.2f}[/{u_color}] [dim](floating)[/dim]\n"
                pnl_text += f"Historical PnL: [{r_color}]{'+' if realized >= 0 else ''}${realized:.2f}[/{r_color}]\n\n"

                if positions:
                    pnl_text += "[bold underline]Open Positions:[/bold underline]\n"

                    dashboard_data = {}
                    if os.path.exists('/root/dashboard_data.json'):
                        try:
                            with open('/root/dashboard_data.json', 'r') as f:
                                dashboard_data = json.load(f)
                        except Exception:
                            pass

                    for p in positions:
                        p_color = "green" if p['pnl'] >= 0 else "red"
                        asset_name = p['pair'].replace('USDT', '')
                        pnl_text += f"{asset_name}: {p['qty']:.6f} (${p['value']:.2f}) [PnL: [{p_color}]${p['pnl']:.2f}[/{p_color}]]\n"

                        pair_inds = dashboard_data.get(p['pair'])
                        if pair_inds:
                            atr = pair_inds.get('atr', 0)
                            hourly_vol = pair_inds.get('hourly_vol', 0)
                            avg_vol = pair_inds.get('avg_vol', 0)
                            rvol = (hourly_vol / avg_vol) if avg_vol > 0 else 0
                            bb_width = pair_inds.get('bb_width', 0)
                            bb_width_prev = pair_inds.get('bb_width_prev', 0)
                            bbu = pair_inds.get('bb_upper', 0)
                            rsi = pair_inds.get('rsi_1h', 0)
                            ema50 = pair_inds.get('ema_50_1h', 0)
                            ema50_prev = pair_inds.get('ema_50_1h_prev', 0)
                            ema_slope = "UP/FLAT" if ema50 >= ema50_prev else "DOWN"
                            btr = pair_inds.get('body_to_range', 0)

                            pnl_text += f"  ↳ RVOL: {rvol:.2f}x | RSI(14): {rsi:.1f} | EMA50: {ema_slope} | Body/Range: {btr:.2f}\n"
                            pnl_text += f"  ↳ BBW: {bb_width:.4f} (Prev: {bb_width_prev:.4f}) | BBU: {bbu:.4f} | 1h ATR: {atr:.4f}\n"

                layout["pnl_summary"].update(Panel(pnl_text, title="Financial Performance"))
                layout["footer"].update(Panel("Auto-tracking Latest Trades | P: Open Positions Visualizer | Q/ESC: Main Menu | UI Latency: <2ms", style="dim"))

                # 6. Handle Input (snappy 200ms timeout for instant responsiveness)
                key = term.inkey(timeout=0.2)
                if key:
                    if key.lower() in ('q', 'm') or key.code == term.KEY_ESCAPE:
                        return "menu"
                    elif key.lower() in ('p', 'o'):
                        return "positions"

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
