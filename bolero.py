import os
import subprocess
from blessed import Terminal

def main():
    term = Terminal()
    options = [
        "📈 Live Trading Bot (trades, entries, exits)",
        "⚙️ Tuner Grid Search (runs continuously, optimizes params)",
        "🤖 AI Risk Manager (hourly tactical adjustments)",
        "🧬 Strategy Evolver (nightly code evolution at 1am)",
        "🔬 Weekly Trade Research (Sundays 3am, mines trade DB)",
        "📊 Price Data Research (bi-weekly, tests new signals)",
        "📋 Research Reports (view latest findings)",
        "❌ Exit"
    ]
    selected_idx = 0

    with term.fullscreen(), term.cbreak(), term.hidden_cursor():
        while True:
            # Clear screen and draw menu
            print(term.home + term.clear)
            
            # Header - Bolero branded with flamenco dancer
            print(term.bold_red(""))
            print(term.bold_red("    ╔══════════════════════════════╗"))
            print(term.bold_red("    ║  ") + term.bold_yellow("💃 B O L E R O") + term.bold_red("              ║"))
            print(term.bold_red("    ╚══════════════════════════════╝"))
            print("")
            print("  Use " + term.bold("UP/DOWN") + " to select, " + term.bold("ENTER") + " to open.\n")

            # Options list
            for idx, opt in enumerate(options):
                if idx == selected_idx:
                    print(term.black_on_red(f" ➔  {opt} "))
                else:
                    print(f"    {opt} ")

            # Footer
            print(term.move_xy(0, term.height - 2) + term.red("Press Q or choose Exit to close. 💃"))

            # Read keyboard input
            key = term.inkey()
            if key.code == term.KEY_UP:
                selected_idx = (selected_idx - 1) % len(options)
            elif key.code == term.KEY_DOWN:
                selected_idx = (selected_idx + 1) % len(options)
            elif key.code == term.KEY_ENTER or key == '\n' or key == '\r':
                if selected_idx == 7:  # Exit option
                    break
                
                print(term.clear)
                try:
                    if selected_idx == 0:
                        # Live Trading Bot dashboard
                        subprocess.run(["/root/venv/bin/python", "/root/dashboard.py"])
                    elif selected_idx == 1:
                        # Tuner grid search dashboard
                        subprocess.run(["/root/venv/bin/python", "/root/backtest_dashboard.py"])
                    elif selected_idx == 2:
                        # AI Risk Manager logs (hourly)
                        log_path = "/root/ai_manager.log"
                        if os.path.exists(log_path):
                            subprocess.run(["tail", "-f", log_path])
                        else:
                            print(term.bold_red("AI Manager log not found. Runs hourly via cron."))
                            term.inkey(timeout=3)
                    elif selected_idx == 3:
                        # Strategy Evolver logs (nightly optimize.sh)
                        log_path = "/root/strategy_evolver.log"
                        if os.path.exists(log_path):
                            subprocess.run(["less", "+G", log_path])
                        else:
                            print(term.bold_red("Strategy evolver log not found."))
                            term.inkey(timeout=3)
                    elif selected_idx == 4:
                        # Weekly trade research log
                        log_path = "/root/weekly_research.log"
                        if os.path.exists(log_path):
                            subprocess.run(["tail", "-f", log_path])
                        else:
                            print(term.bold_yellow("Weekly research log not found. Runs Sundays at 3am."))
                            term.inkey(timeout=3)
                    elif selected_idx == 5:
                        # Price data research (live output)
                        log_path = "/root/price_research.log"
                        if os.path.exists(log_path):
                            subprocess.run(["tail", "-f", log_path])
                        else:
                            print(term.bold_yellow("Price research log not found. It may not have run yet."))
                            print(term.bold_yellow("Showing strategy_evolver.log instead (Ctrl+C to exit)..."))
                            term.inkey(timeout=2)
                            subprocess.run(["tail", "-f", "/root/strategy_evolver.log"])
                    elif selected_idx == 6:
                        # View research reports
                        reports = []
                        if os.path.exists("/root/price_research.html"):
                            reports.append("/root/price_research.html")
                        if os.path.exists("/root/weekly_research.html"):
                            reports.append("/root/weekly_research.html")
                        if os.path.exists("/root/daily_opinion.html"):
                            reports.append("/root/daily_opinion.html")
                        if reports:
                            subprocess.run(["less"] + reports)
                        else:
                            print(term.bold_red("No research reports found yet. They generate on schedule."))
                            term.inkey(timeout=3)
                except Exception as e:
                    print(term.red(f"Error executing action: {e}"))
                    term.inkey(timeout=3)
            elif key.lower() == 'q':
                break
    print(term.clear + term.home, end='')

if __name__ == "__main__":
    main()
