import os
import subprocess
from blessed import Terminal

def main():
    term = Terminal()
    options = [
        "📈 Live Trading Bot (trades, entries, exits)",
        "⚙️ Tuner Grid Search (runs continuously, optimizes params)",
        "🤖 AI Risk Manager (hourly tactical adjustments)",
        "🧬 Nightly AI Committee (Strategy, Trade, & Price Research)",
        "👀 Asset Tracking Dashboard (active & restricted pairs)",
        "💸 Forecast View (expected money based on last N days)",
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
                if selected_idx == 6:  # Exit option
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
                            subprocess.run(["less", "+G", log_path])
                        else:
                            print(term.bold_red("AI Manager log not found. Runs hourly via cron."))
                            term.inkey(timeout=3)
                    elif selected_idx == 3:
                        # Nightly AI Committee logs
                        log_path = "/root/strategy_evolver.log"
                        if os.path.exists(log_path):
                            subprocess.run(["less", "+G", log_path])
                        else:
                            print(term.bold_red("Committee log not found."))
                            term.inkey(timeout=3)
                    elif selected_idx == 4:
                        # View blacklist
                        subprocess.run(["/root/venv/bin/python", "/root/view_blacklist.py"])
                    elif selected_idx == 5:
                        # Forecast View
                        subprocess.run(["/root/venv/bin/python", "/root/forecast_dashboard.py"])
                    elif selected_idx == 6:
                        # View blacklist
                        subprocess.run(["/root/venv/bin/python", "/root/view_blacklist.py"])
                    elif selected_idx == 7:
                        # Forecast View
                        subprocess.run(["/root/venv/bin/python", "/root/forecast_dashboard.py"])
                except Exception as e:
                    print(term.red(f"Error executing action: {e}"))
                    term.inkey(timeout=3)
            elif key.lower() == 'q':
                break
    print(term.clear + term.home, end='')

if __name__ == "__main__":
    main()
