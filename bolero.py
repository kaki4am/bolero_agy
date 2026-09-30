import os
import subprocess
from blessed import Terminal

def main():
    term = Terminal()
    options = [
        "📈 Live Trading Bot (trades, entries, exits)",
        "🎯 Active Positions (Exact Entries & Price Variations)",
        "⚙️ Tuner Grid Search (runs continuously, optimizes params)",
        "🤖 AI Risk Manager (hourly tactical adjustments)",
        "🧬 Nightly AI Committee (Strategy, Trade, & Price Research)",
        "👀 Asset Tracking Dashboard (active & restricted pairs)",
        "💸 Forecast View (expected money based on last N days)",
        "❌ Exit"
    ]
    selected_idx = 0
    exit_idx = len(options) - 1

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
            print("  Use " + term.bold("UP/DOWN / [0-6]") + " to select, " + term.bold("ENTER") + " to open.\n")

            # Options list
            for idx, opt in enumerate(options):
                num_tag = f"[{idx}] " if idx < exit_idx else "[Q] "
                if idx == selected_idx:
                    print(term.black_on_red(f" ➔  {num_tag}{opt} "))
                else:
                    print(f"    {term.dim}{num_tag}{term.normal}{opt} ")

            # Footer
            print(term.move_xy(0, term.height - 2) + term.red("Press Q or choose Exit to close. 💃"))

            # Read keyboard input
            key = term.inkey()
            trigger_action = False

            if key.code == term.KEY_UP:
                selected_idx = (selected_idx - 1) % len(options)
            elif key.code == term.KEY_DOWN:
                selected_idx = (selected_idx + 1) % len(options)
            elif key.isdigit() and int(key) < len(options) - 1:
                selected_idx = int(key)
                trigger_action = True
            elif key.code == term.KEY_ENTER or key == '\n' or key == '\r':
                trigger_action = True
            elif key.lower() == 'q' or key.code == term.KEY_ESCAPE:
                break

            if trigger_action:
                if selected_idx == exit_idx:  # Exit option
                    break
                
                print(term.clear)
                try:
                    if selected_idx in (0, 1):
                        target = "dashboard" if selected_idx == 0 else "positions"
                        while target:
                            print(term.home + term.clear)
                            if target == "dashboard":
                                import dashboard
                                next_screen = dashboard.main()
                                if next_screen == "positions":
                                    target = "positions"
                                else:
                                    target = None
                            elif target == "positions":
                                import positions_dashboard
                                next_screen = positions_dashboard.main()
                                if next_screen == "dashboard":
                                    target = "dashboard"
                                else:
                                    target = None

                    elif selected_idx == 2:
                        # Tuner grid search dashboard
                        subprocess.run(["/root/venv/bin/python", "/root/backtest_dashboard.py"])
                    elif selected_idx == 3:
                        # AI Risk Manager logs (hourly)
                        log_path = "/root/ai_manager.log"
                        if os.path.exists(log_path):
                            subprocess.run(["less", "+G", log_path])
                        else:
                            print(term.bold_red("AI Manager log not found. Runs hourly via cron."))
                            term.inkey(timeout=3)
                    elif selected_idx == 4:
                        # Nightly AI Committee logs
                        log_path = "/root/strategy_evolver.log"
                        if os.path.exists(log_path):
                            subprocess.run(["less", "+G", log_path])
                        else:
                            print(term.bold_red("Committee log not found."))
                            term.inkey(timeout=3)
                    elif selected_idx == 5:
                        # View blacklist
                        import view_blacklist
                        view_blacklist.main()
                    elif selected_idx == 6:
                        # Forecast View
                        import forecast_dashboard
                        forecast_dashboard.main()
                except Exception as e:
                    print(term.red(f"Error executing action: {e}"))
                    term.inkey(timeout=3)

    print(term.clear + term.home, end='')

if __name__ == "__main__":
    main()
