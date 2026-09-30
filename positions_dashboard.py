import os
import json
import time
import threading
from datetime import datetime, timezone
from blessed import Terminal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import asciichartpy

from trading_utils import get_binance_client, atomic_json_dump

CACHE_FILE = '/root/.positions_cache.json'

# In-memory thread-safe state
positions_state = {
    'active_positions': {},
    'ticker_map': {},
    'klines_map': {},
    'status': 'Initializing...',
    'last_updated': None
}
positions_lock = threading.Lock()
force_refresh_event = threading.Event()
_worker_thread = None

def format_delta(current, entry):
    if entry <= 0:
        return "0.00%", "$0.00", "white"
    diff = current - entry
    pct = (diff / entry) * 100.0
    color = "green" if diff >= 0 else "red"
    sign = "+" if diff >= 0 else ""
    return f"{sign}{pct:.2f}%", f"{sign}${diff:.4f}", color

def format_pct(val):
    color = "green" if val >= 0 else "red"
    sign = "+" if val >= 0 else ""
    return f"[{color}]{sign}{val:.2f}%[/{color}]"

def load_initial_cache():
    """Load persistent disk cache immediately on startup for instant 0ms first-frame render."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cdata = json.load(f)
                with positions_lock:
                    positions_state['active_positions'] = cdata.get('active_positions', {})
                    positions_state['ticker_map'] = cdata.get('ticker_map', {})
                    positions_state['klines_map'] = cdata.get('klines_map', {})
                    positions_state['last_updated'] = cdata.get('last_updated')
                    positions_state['status'] = f"Cached ({cdata.get('last_updated', 'recent')})"
        except Exception:
            pass

    # Merge fresh active_positions.json if available
    if os.path.exists('/root/active_positions.json'):
        try:
            with open('/root/active_positions.json', 'r') as f:
                raw = json.load(f)
                active = raw.get('active_positions', {})
                if active:
                    with positions_lock:
                        positions_state['active_positions'] = active
        except Exception:
            pass

    # Fallback price lookups from dashboard_data.json if ticker missing
    if os.path.exists('/root/dashboard_data.json'):
        try:
            with open('/root/dashboard_data.json', 'r') as f:
                ddata = json.load(f)
                with positions_lock:
                    for pair in positions_state['active_positions'].keys():
                        if pair not in positions_state['ticker_map'] and pair in ddata:
                            info = ddata[pair]
                            ep = positions_state['active_positions'][pair].get('entry_price', 0.0)
                            positions_state['ticker_map'][pair] = {
                                'price': ep,
                                'change_24h': float(info.get('alt_4h_ret', 0.0))
                            }
        except Exception:
            pass

# Pre-load cache at import time so first frame is instant
load_initial_cache()

def positions_worker():
    """Background daemon worker to query Binance REST endpoints without blocking the UI thread."""
    client = None
    while True:
        try:
            if client is None:
                try:
                    client = get_binance_client()
                except Exception as e:
                    with positions_lock:
                        positions_state['status'] = f"Client: {str(e)[:12]}"
                    time.sleep(5)
                    continue

            # 1. Read live active positions
            active = {}
            if os.path.exists('/root/active_positions.json'):
                try:
                    with open('/root/active_positions.json', 'r') as f:
                        active = json.load(f).get('active_positions', {})
                except Exception:
                    pass

            if not active:
                with positions_lock:
                    positions_state['active_positions'] = {}
                    positions_state['status'] = "No Open Positions"
                force_refresh_event.wait(timeout=10.0)
                force_refresh_event.clear()
                continue

            pairs = list(active.keys())
            new_ticker_map = {}
            for p in pairs:
                try:
                    t = client.get_ticker(symbol=p)
                    new_ticker_map[p] = {
                        'price': float(t.get('lastPrice', 0.0)),
                        'change_24h': float(t.get('priceChangePercent', 0.0)),
                    }
                except Exception:
                    pass

            # 2. Pre-fetch 15m klines for active pairs
            new_klines = {}
            for p in pairs:
                try:
                    kl = client.get_historical_klines(p, '15m', "15 hours ago UTC")
                    if len(kl) > 80:
                        kl = kl[-80:]
                    new_klines[p] = kl
                except Exception:
                    pass

            now_str = datetime.now(timezone.utc).strftime('%H:%M:%S')
            with positions_lock:
                positions_state['active_positions'] = active
                if new_ticker_map:
                    positions_state['ticker_map'].update(new_ticker_map)
                if new_klines:
                    positions_state['klines_map'].update(new_klines)
                positions_state['status'] = f"Live ({now_str})"
                positions_state['last_updated'] = now_str

            # 3. Persist atomically to disk cache
            atomic_json_dump({
                'active_positions': active,
                'ticker_map': positions_state['ticker_map'],
                'klines_map': positions_state['klines_map'],
                'last_updated': now_str
            }, CACHE_FILE)

        except Exception as e:
            with positions_lock:
                positions_state['status'] = f"Sync: {str(e)[:12]}"

        # Sleep or wait for force refresh
        force_refresh_event.wait(timeout=12.0)
        force_refresh_event.clear()

def start_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=positions_worker, daemon=True)
        _worker_thread.start()

def generate_position_chart(pair, pos, ticker, klines, width=80, height=10):
    entry_time = float(pos.get('time', 0.0))
    entry_price = float(pos.get('entry_price', 0.0))
    curr_price = float(ticker.get('price', entry_price))
    sl = float(pos.get('sl', 0.0))
    max_p = float(pos.get('max_p', entry_price))

    if not klines or len(klines) < 5:
        return "[dim]Loading time-series price data in background...[/dim]"

    limit = max(30, min(80, width - 18))
    usable_klines = klines[-limit:] if len(klines) > limit else klines

    closes = [float(k[4]) for k in usable_klines]
    times = [k[0] / 1000 for k in usable_klines]

    # Update last close with live current price
    if closes:
        closes[-1] = curr_price

    # Find the candle index closest to entry time
    entry_idx = min(range(len(times)), key=lambda i: abs(times[i] - entry_time))
    entry_idx = max(0, min(len(closes) - 1, entry_idx))

    # Base chart
    chart_str = asciichartpy.plot(closes, {'height': height})
    lines = chart_str.split('\n')

    # Find separator column index across lines
    sep_idx = -1
    for line in lines:
        for idx_char, ch in enumerate(line):
            if ch in ('┤', '┼'):
                sep_idx = idx_char
                break
        if sep_idx != -1:
            break

    if sep_idx != -1:
        x_pos = sep_idx + 1 + entry_idx
        # Estimate target row based on entry price
        min_p, max_p_series = min(closes), max(closes)
        span = max_p_series - min_p
        norm_y = (entry_price - min_p) / span if span > 0 else 0.5
        target_row = int(round((1.0 - norm_y) * height))
        target_row = max(0, min(len(lines) - 1, target_row))

        # Snap dot directly on curve characters
        LINE_CHARS = set('╶╴─╰╭╮╯│')
        candidates = [
            r for r in range(len(lines))
            if x_pos < len(lines[r]) and lines[r][x_pos] in LINE_CHARS
        ]

        if candidates:
            chosen_row = min(candidates, key=lambda r: abs(r - target_row))
        else:
            chosen_row = target_row

        dot_color_code = "\033[1;92m●\033[0m" if curr_price >= entry_price else "\033[1;91m●\033[0m"

        target_line = lines[chosen_row]
        if x_pos >= len(target_line):
            target_line = target_line.ljust(x_pos + 1)
        target_line = target_line[:x_pos] + dot_color_code + target_line[x_pos + 1:]
        lines[chosen_row] = target_line

    chart_output = '\n'.join(lines)

    # Time markers for start, entry, and now
    start_dt = datetime.fromtimestamp(times[0], tz=timezone.utc).strftime('%H:%M')
    entry_dt = datetime.fromtimestamp(entry_time, tz=timezone.utc).strftime('%H:%M')
    now_dt = datetime.now(timezone.utc).strftime('%H:%M')

    dot_legend = "[bold green]●[/bold green]" if curr_price >= entry_price else "[bold red]●[/bold red]"

    info_footer = (
        f"Timeline (UTC): {start_dt} "
        + "─" * max(2, entry_idx - 6)
        + f" {dot_legend} Entered [{entry_dt} @ ${entry_price:.4f}] "
        + "─" * max(2, (len(closes) - entry_idx) - 8)
        + f" [Now: {now_dt} @ ${curr_price:.4f}]\n"
        + f"[dim]Key Levels: Stop Loss: ${sl:.4f} | Peak Reached: ${max_p:.4f}[/dim]"
    )

    return f"{chart_output}\n{info_footer}"

def render_dashboard(term, console, selected_pair_idx=0, view_mode="single"):
    """Render frame purely from thread-safe local memory in <2ms with zero network I/O."""
    with positions_lock:
        active_positions = dict(positions_state['active_positions'])
        ticker_map = dict(positions_state['ticker_map'])
        klines_map = dict(positions_state['klines_map'])
        status_text = positions_state['status']

    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')

    # Read live total equity if available from dashboard cache
    total_eq = 0.0
    usdt_cash = 0.0
    if os.path.exists('/root/.dashboard_cache.json'):
        try:
            with open('/root/.dashboard_cache.json', 'r') as f:
                c = json.load(f)
                total_eq = c.get('total_equity', 0.0)
                usdt_cash = c.get('usdt_cash', 0.0)
        except Exception:
            pass

    eq_str = f" | Total Equity: [bold cyan]${total_eq:.2f}[/bold cyan] (Cash: ${usdt_cash:.2f})" if total_eq > 0 else ""

    # Header
    header_text = Text()
    header_text.append("💃 BOLERO ", style="bold red")
    header_text.append("• Active Position Visualizer (Time-Series & Entry Dot ●)\n", style="bold yellow")
    header_text.append(f"Current UTC: {now_str}{eq_str} | Feed: [cyan]{status_text}[/cyan] | Latency: [green]<2ms[/green]\n", style="dim")
    header_text.append("Controls: ◀/▶ (change asset) | TAB (view mode) | D (live bot) | Q/ESC (main menu) | R (refresh)", style="dim")
    console.print(Panel(header_text, style="bold cyan"))

    if not active_positions:
        console.print(Panel("[yellow]No active positions currently open in Bolero.[/yellow]", title="Portfolio Status"))
        return 0, None

    pairs = list(active_positions.keys())
    selected_pair_idx = selected_pair_idx % len(pairs)
    active_pair = pairs[selected_pair_idx]

    # Compact Summary Table
    table = Table(title="[bold white]Positions Overview[/bold white]", header_style="bold magenta", expand=True)
    table.add_column("Sel", justify="center", width=3)
    table.add_column("Asset", style="bold cyan", justify="left", no_wrap=True)
    table.add_column("Entered (UTC)", justify="left")
    table.add_column("Holding Time", justify="center")
    table.add_column("Entry Price", justify="right")
    table.add_column("Current Price", justify="right")
    table.add_column("Var (Since Entry)", justify="center")
    table.add_column("24h Var", justify="center")
    table.add_column("Unrealized PnL", justify="center")
    table.add_column("Setup", justify="left")

    for i, pair in enumerate(pairs):
        pos = active_positions[pair]
        asset = pair.replace("USDT", "")
        entry_price = float(pos.get('entry_price', 0.0))
        qty = float(pos.get('qty', 0.0))
        cost = entry_price * qty
        setup = pos.get('setup', 'N/A')

        t_raw = pos.get('time', 0.0)
        if isinstance(t_raw, (int, float)) and t_raw > 0:
            entry_dt = datetime.fromtimestamp(t_raw, tz=timezone.utc)
            entry_time_str = entry_dt.strftime('%H:%M:%S')
            diff_s = max(0, int((now_utc - entry_dt).total_seconds()))
            holding_str = f"{diff_s // 3600}h {(diff_s % 3600) // 60:02d}m"
        else:
            entry_time_str, holding_str = "Unknown", "Unknown"

        ticker = ticker_map.get(pair, {})
        curr_price = ticker.get('price', entry_price)
        change_24h = ticker.get('change_24h', 0.0)

        pct_str, diff_str, delta_color = format_delta(curr_price, entry_price)
        var_since_entry = f"[{delta_color}]{pct_str}[/{delta_color}] ({diff_str})"

        var_24h = format_pct(change_24h)

        current_val = curr_price * qty
        u_pnl = current_val - cost
        pnl_pct = (u_pnl / cost * 100.0) if cost > 0 else 0.0
        pnl_color = "green" if u_pnl >= 0 else "red"
        pnl_sign = "+" if u_pnl >= 0 else ""
        pnl_text = f"[{pnl_color}]{pnl_sign}${u_pnl:.2f} ({pnl_sign}{pnl_pct:.2f}%)[/{pnl_color}]"

        sel_marker = "➔" if i == selected_pair_idx else " "

        table.add_row(
            f"[bold yellow]{sel_marker}[/bold yellow]",
            asset,
            entry_time_str,
            holding_str,
            f"${entry_price:.4f}",
            f"${curr_price:.4f}",
            var_since_entry,
            var_24h,
            pnl_text,
            setup
        )

    console.print(table)

    # Render Chart(s)
    term_width = term.width if term.width and term.width > 40 else 80
    chart_width = min(term_width - 8, 85)

    if view_mode == "all":
        for pair in pairs:
            pos = active_positions[pair]
            ticker = ticker_map.get(pair, {})
            klines = klines_map.get(pair, [])
            chart_content = generate_position_chart(pair, pos, ticker, klines, width=chart_width, height=7)
            console.print(Panel(chart_content, title=f"[bold cyan]{pair} Price History & Entry Dot ●[/bold cyan]", border_style="cyan"))
    else:
        pos = active_positions[active_pair]
        ticker = ticker_map.get(active_pair, {})
        klines = klines_map.get(active_pair, [])
        chart_content = generate_position_chart(active_pair, pos, ticker, klines, width=chart_width, height=10)
        title = f"[bold cyan]{active_pair}[/bold cyan] • [bold yellow]Time-Series Chart with Entry Marker (●)[/bold yellow] [{selected_pair_idx + 1}/{len(pairs)}]"
        console.print(Panel(chart_content, title=title, border_style="yellow"))

    return len(pairs), active_pair

def main(term=None, console=None):
    start_worker()
    if term is None:
        term = Terminal()
    if console is None:
        console = Console()

    selected_idx = 0
    view_mode = "single"
    last_rendered_update = None
    last_selected_idx = None
    last_view_mode = None
    num_pairs = 1
    need_redraw = True

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        # Clean initial screen clear once
        print(term.home + term.clear, end='', flush=True)

        while True:
            # Check if background data has updated
            with positions_lock:
                current_last_updated = positions_state.get('last_updated')

            if (current_last_updated != last_rendered_update or 
                selected_idx != last_selected_idx or 
                view_mode != last_view_mode):
                need_redraw = True

            if need_redraw:
                # Capture entire frame in memory to prevent partial stdout paints
                with console.capture() as capture:
                    try:
                        num_pairs, _ = render_dashboard(term, console, selected_pair_idx=selected_idx, view_mode=view_mode)
                    except Exception as e:
                        console.print(f"[red]Error rendering chart dashboard: {e}[/red]")
                        num_pairs = 1

                frame_output = capture.get()
                # Overwrite screen atomically without full screen clear (zero flicker)
                print(term.home + frame_output + term.clear_eos, end='', flush=True)

                last_rendered_update = current_last_updated
                last_selected_idx = selected_idx
                last_view_mode = view_mode
                need_redraw = False

            # Non-blocking wait for input (0.5s timeout for background update responsiveness)
            key = term.inkey(timeout=0.5)
            if key:
                if key.lower() in ('q', 'm') or key.code == term.KEY_ESCAPE:
                    return "menu"
                elif key.lower() == 'd':
                    return "dashboard"
                elif key.code in (term.KEY_RIGHT, term.KEY_DOWN):
                    if num_pairs > 0:
                        selected_idx = (selected_idx + 1) % num_pairs
                        need_redraw = True
                elif key.code in (term.KEY_LEFT, term.KEY_UP):
                    if num_pairs > 0:
                        selected_idx = (selected_idx - 1) % num_pairs
                        need_redraw = True
                elif key.code == term.KEY_TAB or key == '\t':
                    view_mode = "all" if view_mode == "single" else "single"
                    need_redraw = True
                elif key.lower() == 'r':
                    force_refresh_event.set()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
