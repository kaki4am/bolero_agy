import os
import json
import time
from datetime import datetime, timezone
from blessed import Terminal
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import asciichartpy

from trading_utils import get_binance_client

# In-memory klines cache to keep UI responsive: {pair: (timestamp, klines)}
KLINES_CACHE = {}
CACHE_TTL = 30.0  # seconds

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

def fetch_klines_for_pair(client, pair, limit=60):
    now = time.time()
    if pair in KLINES_CACHE:
        cached_time, cached_klines = KLINES_CACHE[pair]
        if now - cached_time < CACHE_TTL:
            return cached_klines

    if not client:
        return []

    try:
        # Fetch 15m klines for ~15 hours of context
        klines = client.get_historical_klines(pair, '15m', f"{limit * 15} minutes ago UTC")
        if len(klines) > limit:
            klines = klines[-limit:]
        KLINES_CACHE[pair] = (now, klines)
        return klines
    except Exception:
        if pair in KLINES_CACHE:
            return KLINES_CACHE[pair][1]
        return []

def generate_position_chart(pair, pos, ticker, client, width=80, height=10):
    entry_time = float(pos.get('time', 0.0))
    entry_price = float(pos.get('entry_price', 0.0))
    curr_price = float(ticker.get('price', entry_price))
    sl = float(pos.get('sl', 0.0))
    max_p = float(pos.get('max_p', entry_price))

    klines = fetch_klines_for_pair(client, pair, limit=max(30, min(80, width - 18)))
    if not klines or len(klines) < 5:
        return "[dim]Insufficient historical price data for chart.[/dim]"

    closes = [float(k[4]) for k in klines]
    times = [k[0] / 1000 for k in klines]

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

        # Look for the actual line character on column x_pos to snap the dot directly on the curve
        LINE_CHARS = set('╶╴─╰╭╮╯│')
        candidates = [
            r for r in range(len(lines))
            if x_pos < len(lines[r]) and lines[r][x_pos] in LINE_CHARS
        ]

        if candidates:
            chosen_row = min(candidates, key=lambda r: abs(r - target_row))
        else:
            chosen_row = target_row

        # Determine dot color: Green if current price >= entry, Red if in loss
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

def render_dashboard(term, console, client, selected_pair_idx=0, view_mode="single"):
    # 1. Read Active Positions
    active_positions = {}
    if os.path.exists('/root/active_positions.json'):
        try:
            with open('/root/active_positions.json', 'r') as f:
                raw = json.load(f)
                active_positions = raw.get('active_positions', {})
        except Exception:
            pass

    # 2. Read live tickers
    ticker_map = {}
    if client and active_positions:
        for pair in active_positions.keys():
            try:
                t = client.get_ticker(symbol=pair)
                ticker_map[pair] = {
                    'price': float(t.get('lastPrice', 0.0)),
                    'change_24h': float(t.get('priceChangePercent', 0.0)),
                }
            except Exception:
                pass

    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')

    # Header
    header_text = Text()
    header_text.append("💃 BOLERO ", style="bold red")
    header_text.append("• Active Position Visualizer (Time-Series & Entry Dot ●)\n", style="bold yellow")
    header_text.append(f"Current UTC: {now_str} | Controls: LEFT/RIGHT (change asset) | TAB (view mode) | 'r' refresh | 'q' exit", style="dim")
    console.print(Panel(header_text, style="bold cyan"))

    if not active_positions:
        console.print(Panel("[yellow]No active positions currently open in Bolero.[/yellow]", title="Portfolio Status"))
        return 0

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
        # Render all charts
        for pair in pairs:
            pos = active_positions[pair]
            ticker = ticker_map.get(pair, {})
            chart_content = generate_position_chart(pair, pos, ticker, client, width=chart_width, height=7)
            console.print(Panel(chart_content, title=f"[bold cyan]{pair} Price History & Entry Dot ●[/bold cyan]", border_style="cyan"))
    else:
        # Render focused chart for selected asset
        pos = active_positions[active_pair]
        ticker = ticker_map.get(active_pair, {})
        chart_content = generate_position_chart(active_pair, pos, ticker, client, width=chart_width, height=10)
        title = f"[bold cyan]{active_pair}[/bold cyan] • [bold yellow]Time-Series Chart with Entry Marker (●)[/bold yellow] [{selected_pair_idx + 1}/{len(pairs)}]"
        console.print(Panel(chart_content, title=title, border_style="yellow"))

    return len(pairs)

def main():
    term = Terminal()
    console = Console()
    client = None
    try:
        client = get_binance_client()
    except Exception as e:
        print(f"Warning: Could not connect to Binance client: {e}")

    selected_idx = 0
    view_mode = "single"  # or "all"

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        while True:
            print(term.home + term.clear)
            try:
                num_pairs = render_dashboard(term, console, client, selected_pair_idx=selected_idx, view_mode=view_mode)
            except Exception as e:
                console.print(f"[red]Error rendering chart dashboard: {e}[/red]")
                num_pairs = 1

            # Wait for user input without flashing/auto-reloading
            key = term.inkey()
            if key:
                if key.lower() == 'q' or key.code == term.KEY_ESCAPE or key == '\n' or key == '\r':
                    break
                elif key.code == term.KEY_RIGHT or key.code == term.KEY_DOWN:
                    if num_pairs > 0:
                        selected_idx = (selected_idx + 1) % num_pairs
                elif key.code == term.KEY_LEFT or key.code == term.KEY_UP:
                    if num_pairs > 0:
                        selected_idx = (selected_idx - 1) % num_pairs
                elif key.code == term.KEY_TAB or key == '\t':
                    view_mode = "all" if view_mode == "single" else "single"
                elif key.lower() == 'r':
                    # Invalidate cache so 'r' forces a fresh fetch from Binance
                    KLINES_CACHE.clear()
                    continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
