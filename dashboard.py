from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from blessed import Terminal
import json
import os
from trading_utils import get_trade_data, calculate_detailed_pnl, get_binance_client, humanize_time

term = Terminal()

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

def main():
    client = get_binance_client()
    scroll_offset = 0
    layout = generate_layout()
    
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        with Live(layout, refresh_per_second=2, screen=True):
            while True:
                # 1. Fetch Data
                trades_df = get_trade_data(limit=100) # Recent for table
                all_trades_df = get_trade_data()      # All for PnL
                realized, unrealized, positions = calculate_detailed_pnl(all_trades_df, client=client)
                
                # 2. Update Header
                layout["header"].update(Panel(f"Binance Trading Bot - [bold green]Live Dashboard[/bold green] | Time: {datetime.now().strftime('%H:%M:%S')}", style="bold cyan"))
                
                # 3. Update Trades Table
                table = Table(title=f"Recent Trades (Offset: {scroll_offset})")
                table.add_column("Pair")
                table.add_column("Side")
                table.add_column("Price")
                table.add_column("Total (USDT)")
                table.add_column("Fee")
                table.add_column("When")
                
                visible_trades = trades_df.iloc[scroll_offset:]
                
                for _, row in visible_trades.iterrows():
                    color = "green" if row['side'] == 'BUY' else "red"
                    total_usdt = row['price'] * row['quantity']
                    
                    fee = row.get('fee', 0) or 0
                    fee_asset = row.get('fee_asset') or ''
                    if fee > 0:
                        fee_text = f"{fee:.8f} {fee_asset}" if fee < 0.0001 else f"{fee:.4f} {fee_asset}"
                    else:
                        fee_text = "0.0000"
                    
                    time_text = humanize_time(row['timestamp'])
                    table.add_row(
                        row['pair'], f"[{color}]{row['side']}[/{color}]", f"{row['price']:.4f}",
                        f"${total_usdt:.2f}", fee_text, time_text
                    )
                
                layout["trades"].update(Panel(table))
                
                # 4. Update PnL Summary
                r_color = "green" if realized >= 0 else "red"
                u_color = "green" if unrealized >= 0 else "red"
                t_color = "green" if (realized + unrealized) >= 0 else "red"
                
                pnl_text = f"Realized PnL:   [{r_color}]${realized:.2f}[/{r_color}]\n"
                pnl_text += f"Unrealized PnL: [{u_color}]${unrealized:.2f}[/{u_color}]\n"
                pnl_text += "--------------------------------\n"
                pnl_text += f"Total Net PnL:  [bold {t_color}]${(realized + unrealized):.2f}[/bold {t_color}]\n\n"
                
                if positions:
                    pnl_text += "[bold underline]Open Positions:[/bold underline]\n"
                    
                    dashboard_data = {}
                    if os.path.exists('/root/dashboard_data.json'):
                        try:
                            with open('/root/dashboard_data.json', 'r') as f:
                                dashboard_data = json.load(f)
                        except:
                            pass

                    for p in positions:
                        p_color = "green" if p['pnl'] >= 0 else "red"
                        asset_name = p['pair'].replace('USDT', '')
                        pnl_text += f"{asset_name}: {p['qty']:.6f} (${p['value']:.2f}) [PnL: [{p_color}]${p['pnl']:.2f}[/{p_color}]]\n"
                        
                        pair_inds = dashboard_data.get(p['pair'])
                        if pair_inds:
                            rsi = pair_inds.get('rsi', 0)
                            adx = pair_inds.get('adx_1h', 0)
                            pu = "UP" if pair_inds.get('pair_uptrend') else "DOWN"
                            bu = "UP" if pair_inds.get('btc_uptrend') else "DOWN"
                            sqz = "YES" if pair_inds.get('bb_squeeze') else "NO"
                            sma = pair_inds.get('sma30', 0)
                            bbu = pair_inds.get('bb_upper', 0)
                            pnl_text += f"  ↳ Squeeze: {sqz} | SMA30: {sma:.4f} | BBU: {bbu:.4f}\n"
                            pnl_text += f"  ↳ RSI: {rsi:.1f} | 1h ADX: {adx:.1f} | Pair 15m: {pu} | BTC 15m: {bu}\n"
                

                
                layout["pnl_summary"].update(Panel(pnl_text, title="Financial Performance"))
                layout["footer"].update(Panel("ARROWS: Scroll | Q: Quit", style="dim"))
                
                # 5. Handle Input
                key = term.inkey(timeout=0.1)
                if key.code == term.KEY_DOWN:
                    scroll_offset = min(scroll_offset + 1, max(0, len(trades_df) - 5))
                elif key.code == term.KEY_UP:
                    scroll_offset = max(0, scroll_offset - 1)
                elif key.lower() == 'q':
                    return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
