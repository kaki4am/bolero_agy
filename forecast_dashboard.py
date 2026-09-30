from blessed import Terminal
from trading_utils import get_account_snapshot_data
from daily_signal_brief import get_performance_stats, calculate_capital_projections

def main():
    term = Terminal()
    print(term.home + term.clear)
    print(term.bold_green("    💸 Financial View (30-Day PnL & Multi-Year Forecast)"))
    print(term.bold_green("    ═════════════════════════════════════════════════════\n"))
    
    print(term.yellow("  Fetching live API & performance data (this takes a moment)..."))
    
    try:
        data = get_account_snapshot_data()
        stats = get_performance_stats()
        
        print(term.clear + term.home)
        print(term.bold_green("    💸 Financial View (30-Day PnL & Multi-Year Forecast)"))
        print(term.bold_green("    ═════════════════════════════════════════════════════\n"))
        
        if not data:
            print("  No snapshot data available from Binance.")
        else:
            print("Binance Equity 30-Day PnL:")
            print(f"Starting Equity ({data['start_date']}): ${data['start_val']:,.2f}")
            print(f"Current Equity: ${data['current_total']:,.2f}")
            print(f"Total Net PnL: ${data['abs_pnl']:+,.2f} ({data['pct_pnl']:+.2f}%)")
            print(f"BTC Benchmark: {data['btc_pct']:+.2f}%")
            print(f"Bot Alpha (vs BTC): {data['alpha']:+.2f}%\n")
            
            import asciichartpy
            print("Portfolio Equity Curve (Last 30 Days):")
            vals = data['vals']
            stretched_vals = []
            for i in range(len(vals) - 1):
                stretched_vals.append(vals[i])
                stretched_vals.append(vals[i] + (vals[i+1] - vals[i]) / 3)
                stretched_vals.append(vals[i] + (vals[i+1] - vals[i]) * 2 / 3)
            if vals:
                stretched_vals.append(vals[-1])
            
            if stretched_vals:
                print(asciichartpy.plot(stretched_vals, {'height': 10}))
                print()
            
            current_eq = data['current_total']
            
            # Use deterministic Signal briefing engine as single source of truth
            projections_data, formatted_block = calculate_capital_projections(current_eq, stats)
            
            print(term.bold_yellow("  [ 🔭 Long-Term Capital Projections (Signal Source of Truth) ]"))
            print(f"    Starting Baseline: ${current_eq:,.2f} (Live Spot Equity)\n")
            
            for line in formatted_block.split('\n')[2:]:
                if line.startswith('•'):
                    print("  " + term.bold_yellow(line))
                elif any(line.strip().startswith(h) for h in ['1 Year:', '2 Years:', '3 Years:', '5 Years:', '10 Years:']):
                    parts = line.strip().split(':', 1)
                    print(f"    {parts[0]:<10}: {term.bold_green(parts[1].strip())}")
                else:
                    print("  " + line)
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(term.red(f"  Error fetching PnL: {e}"))
        
    print("\n\n" + term.red("Press any key to return..."))
    term.inkey()

if __name__ == "__main__":
    main()
