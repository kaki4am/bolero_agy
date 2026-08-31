from blessed import Terminal
from trading_utils import get_account_snapshot_data

def main():
    term = Terminal()
    print(term.home + term.clear)
    print(term.bold_green("    💸 Financial View (30-Day PnL)"))
    print(term.bold_green("    ═══════════════════════════════\n"))
    
    print(term.yellow("  Fetching live API data (this takes a moment)..."))
    
    try:
        data = get_account_snapshot_data()
        
        print(term.clear + term.home)
        print(term.bold_green("    💸 Financial View (30-Day PnL)"))
        print(term.bold_green("    ═══════════════════════════════\n"))
        
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
                print(asciichartpy.plot(stretched_vals, {'height': 12}))
                print()
            
            current_eq = data['current_total']
            monthly_yield = data['pct_pnl'] / 100.0
            
            print(term.bold_yellow("  [ 🔮 Future Projections (Compounding at current 30-day rate) ]"))
            print(f"    Current Capital: ${current_eq:,.2f}  |  30-Day Rate: {monthly_yield*100:.2f}%\n")
            
            for months, label in [(1, "30 Days"), (3, "90 Days"), (6, "6 Months"), (12, "1 Year")]:
                projected = current_eq * ((1 + monthly_yield) ** months)
                profit = projected - current_eq
                print(f"    {label}: {term.bold_green('$' + format(projected, ',.2f'))} (+${profit:,.2f})")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(term.red(f"  Error fetching PnL: {e}"))
        
    print("\n\n" + term.red("Press any key to return..."))
    term.inkey()

if __name__ == "__main__":
    main()
