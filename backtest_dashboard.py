import json
import os
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.layout import Layout
from blessed import Terminal

term = Terminal()
STATUS_FILE = 'backtest_status.json'

def get_status():
    if not os.path.exists(STATUS_FILE):
        return None
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def draw_histogram(scores, width=60, height=5):
    if not scores:
        return "No scores recorded yet. Waiting for optimizer iterations..."
    if len(scores) < 3:
        return "Collecting score data... waiting for more iterations to plot."
        
    mn, mx = min(scores), max(scores)
    if mn == mx:
        mn -= 1.0
        mx += 1.0
        
    num_bins = width - 12
    if num_bins < 10:
        num_bins = 10
        
    bins = [0] * num_bins
    bin_size = (mx - mn) / num_bins
    
    for s in scores:
        bin_idx = int((s - mn) / bin_size) if bin_size > 0 else 0
        if bin_idx >= num_bins:
            bin_idx = num_bins - 1
        elif bin_idx < 0:
            bin_idx = 0
        bins[bin_idx] += 1
        
    max_bin_count = max(bins)
    if max_bin_count == 0:
        max_bin_count = 1
        
    rows = []
    for r in range(height):
        rows.append([" "] * num_bins)
        
    for col_idx, count in enumerate(bins):
        scaled = int(count / max_bin_count * (height - 1)) if max_bin_count > 0 else 0
        for r in range(height - 1 - scaled, height):
            rows[r][col_idx] = "█"
            
    lines = []
    for r in range(height):
        lines.append("  " + "".join(rows[r]))
        
    x_axis = "  +" + "-" * (num_bins - 2) + "+"
    lines.append(x_axis)
    
    label_line = f" {mn:+.1f}%" + " " * (num_bins // 2 - 5) + f"{mn + (mx-mn)/2:+.1f}%" + " " * (num_bins - num_bins // 2 - 6) + f"{mx:+.1f}%"
    lines.append(label_line)
    
    return "\n".join(lines)

def generate_dashboard():
    status = get_status()
    if not status:
        return Panel("No backtest data available yet. Waiting for optimizer to start...", title="Backtest Optimizer Dashboard", style="bold yellow")

    # Format relative "Last Run", "Run Started" and "Next Run"
    last_run_str = status.get('last_run')
    run_started_str = status.get('run_started', last_run_str)
    
    def format_relative_time(ts_str):
        if not ts_str or ts_str == "Unknown":
            return ""
        try:
            dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            diff = datetime.now() - dt
            total_seconds = int(diff.total_seconds())
            if total_seconds < 0:
                return " (just now)"
            elif total_seconds < 60:
                return " (less than a minute ago)"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                if hours > 0:
                    return f" ({hours}h {minutes}m ago)"
                else:
                    return f" ({minutes}m ago)"
        except:
            return ""

    relative_last_run = format_relative_time(last_run_str)
    relative_run_started = format_relative_time(run_started_str)

    # With continuous optimization, there is no next run time.
    next_run_str = "Continuous Loop"
    relative_next_run = "Running 24/7"

    # Header Panel
    eta_text = f" | ETA: [bold yellow]{status.get('eta', 'N/A')}[/bold yellow]" if status['status'] != "Idle" else ""
    
    if last_run_str and run_started_str and last_run_str != run_started_str:
        if run_started_str == "Unknown":
            time_text = f"Started: Unknown (Resumed) | Resumed: {last_run_str}{relative_last_run}"
        else:
            time_text = f"Started: {run_started_str}{relative_run_started} | Resumed: {last_run_str}{relative_last_run}"
    else:
        time_text = f"Last Run: {last_run_str}{relative_last_run}"
        
    header_text = f"Status: [bold {'green' if status['status'] == 'Idle' else 'cyan'}]{status['status']}[/bold {'green' if status['status'] == 'Idle' else 'cyan'}] | {time_text} | Execution Mode: {next_run_str} ({relative_next_run}){eta_text}"
    header = Panel(header_text, title="Optimizer Status", style="bold white")

    # Progress Bar
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})")
    )
    progress.add_task("Optimization Progress", completed=status['progress'], total=status['total_combinations'])
    progress_panel = Panel(progress, title="Scanning Parameter Space")

    # Chart Panel
    all_scores = status.get('all_scores', [])
    term_width = term.width or 80
    chart_width = max(20, int(term_width * 0.6) - 15)
    chart_text = draw_histogram(all_scores, width=chart_width, height=5)
    chart_panel = Panel(chart_text, title="Distribution of Combination Returns (Bell Curve)", style="bold green")

    # Best Params Table
    best_params = status.get('best_params')
    if best_params:
        table = Table(title=f"Best Results (Avg Profit: [bold green]{status['best_profit']:.2f}%[/bold green])", expand=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in best_params.items():
            table.add_row(k, str(v))
        results_panel = Panel(table)
    else:
        results_panel = Panel("Searching for best parameters...", title="Best Results")

    # Log Panel
    logs = status.get('logs', [])
    log_text = "\n".join(logs[-8:]) if logs else "Waiting for events..."
    log_panel = Panel(log_text, title="Recent Events", style="dim white")

    # Pairs Panel
    pairs_text = ", ".join(status.get('pairs', []))
    pairs_panel = Panel(f"Testing against top 50 volume pairs: [bold cyan]{pairs_text}[/bold cyan]", title="Target Portfolio")

    layout = Layout()
    layout.split_column(
        Layout(header, size=3),
        Layout(name="main"),
        Layout(log_panel, size=10),
        Layout(pairs_panel, size=3),
        Layout(Panel("Q: Quit", style="dim"), size=3)
    )
    
    layout["main"].split_row(
        Layout(name="main_left", ratio=2),
        Layout(results_panel, ratio=1)
    )
    
    layout["main_left"].split_column(
        Layout(progress_panel, size=5),
        Layout(chart_panel)
    )
    
    return layout

def main():
    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        with Live(generate_dashboard(), refresh_per_second=2, screen=True) as live:
            while True:
                live.update(generate_dashboard())
                key = term.inkey(timeout=0.5)
                if key.lower() == 'q':
                    return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
