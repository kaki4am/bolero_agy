from trading_utils import get_trade_data, calculate_detailed_pnl, get_binance_client

def main():
    client = get_binance_client()
    all_trades_df = get_trade_data()

    realized, unrealized, positions = calculate_detailed_pnl(all_trades_df, client=client)
    
    print(f"Realized PnL:   ${realized:.2f}")
    print(f"Unrealized PnL: ${unrealized:.2f}")
    print(f"Total Net PnL:  ${(realized + unrealized):.2f}")
    
    if positions:
        print("\nOpen Positions:")
        for p in positions:
            print(f"{p['pair']}: Qty: {p['qty']:.6f}, Cost: ${p['cost']:.2f}, Value: ${p['value']:.2f}, PnL: ${p['pnl']:.2f}")

if __name__ == "__main__":
    main()
