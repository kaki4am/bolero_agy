import asyncio
import os
import sys

from portfolio_backtester import PortfolioBacktester

async def main():
    import json
    # Use pairs from bot config
    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT", "MATICUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT", "FILUSDT", "NEARUSDT", "AAVEUSDT", "ALGOUSDT", "VETUSDT"]
    
    # We load config
    config = {
        'EMA_FAST': 50,
        'EMA_SLOW': 200,
        'BB_LENGTH': 20,
        'BB_STD': 2.5,
        'ADX_THRESHOLD': 25.0,
        'CHOP_THRESHOLD': 50,
        'VOL_TREND': 1.5,
        'VOL_BREAKOUT': 1.8,
        'MIN_VOLATILITY': 0.001,
        'BASE_RISK_PERCENT': 1.7,
        'MAX_RISK_PER_TRADE_PERCENT': 15.0,
        'COOLDOWN_PERIOD': 600,
        'MAX_PAIRS': 40,
        'PORTFOLIO_EJECT': -5.5,
        'PORTFOLIO_HARVEST': 4.0,
        'VOL_MULT_LOW': 1.4,
        'VOL_MULT_MED': 1.8,
        'VOL_MULT_HIGH': 2.5,
        'BTC_RSI_THRESHOLD': 30.0,
        'VOL_SPIKE_MULTIPLIER': 1.7,
        'SL_MIN_PCT': 0.015,
        'SL_MAX_PCT': 0.03,
        'BE_TRIGGER': 0.02,
        'BE_LOCK': 0.002,
        'TRAILING_TRIGGER': 0.04,
        'TRAILING_DIST': 0.02,
        'VOLATILITY_CAP': 0.015,
        'VOLUME_SMA_WINDOW': 20,
        'SCALE_1_POS': 0.8,
        'SCALE_2_POS': 0.6,
        'SCALE_3_POS': 0.4,
        'ATR_SL_MULT': 2.75
    }

    backtester = PortfolioBacktester(symbols=pairs, interval='1m', lookback='5 days ago UTC')
    
    def status(msg):
        print(msg)
        
    await backtester.fetch_data(status_callback=status)
    backtester.precalculate_all(config, status_callback=status)
    
    # Original logic test
    print("\n--- Original Logic (RSI Pullback) ---")
    pnl = backtester.run(config)
    print(f"PnL: {pnl:.2f}%")
    
    # Let's monkeypatch run method to test new logic
    original_run = backtester.run
    
    def new_run(self, params):
        balance = 1000.0
        initial_balance = balance
        active_positions = {s: {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': -99999} for s in self.pair_data.keys()}
        trades = []
        slippage_pct = params.get('SLIPPAGE_PCT', 0.0007)
        
        # Determine common time range
        all_timestamps = []
        for s in self.pair_data:
            all_timestamps.extend(self.pair_data[s]['1m']['timestamp'].tolist())
        unique_ts = sorted(list(set(all_timestamps)))
        if not unique_ts: return 0.0
        symbol_indices = {s: {ts: i for i, ts in enumerate(self.pair_data[s]['1m']['timestamp'])} for s in self.pair_data}

        np_data = {}
        for s in self.pair_data:
            df = self.pair_data[s]['1m']
            ind = self.precalculated_indicators[s]
            np_data[s] = {
                'close': df['close'].values,
                'volume': df['volume'].values,
                'rsi': ind['rsi'].values,
                'atr': ind['atr'].values,
                'adx': ind['adx'].values,
                'macd': ind['macd'].values,
                'macdh': ind['macdh'].values,
                'vwap': ind['vwap'].values,
                'vol_sma': ind['vol_sma'].values,
                'btc_rsi': ind['btc_safe']['rsi'].values,
                'btc_uptrend': ind['btc_safe']['uptrend'].values,
                'btc_uptrend_15m': ind['btc_safe']['uptrend_15m'].values,
                'pair_safe': ind['pair_safe'].values
            }

        for ts in unique_ts:
            total_unrealized_pnl = 0.0
            active_count = 0
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None: continue
                pos = active_positions[s]
                if pos['qty'] > 0:
                    active_count += 1
                    price = np_data[s]['close'][idx]
                    total_unrealized_pnl += (price - pos['entry_price']) * pos['qty']
            
            current_equity = balance
            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None: continue
                pos = active_positions[s]
                if pos['qty'] > 0:
                    current_equity += pos['qty'] * np_data[s]['close'][idx]
                    
            portfolio_pnl_pct = (total_unrealized_pnl / current_equity) * 100 if current_equity > 0 else 0

            global_exit_reason = None
            if portfolio_pnl_pct <= params.get('PORTFOLIO_EJECT', -5.0): global_exit_reason = "GlobalEject"
            elif portfolio_pnl_pct >= params.get('PORTFOLIO_HARVEST', 4.0): global_exit_reason = "GlobalHarvest"

            if global_exit_reason:
                for s in self.pair_data:
                    idx = symbol_indices[s].get(ts)
                    if idx is None: continue
                    pos = active_positions[s]
                    if pos['qty'] > 0:
                        exit_price = np_data[s]['close'][idx] * (1.0 - slippage_pct)
                        pnl = ((exit_price / pos['entry_price']) - 1) * 100
                        trades.append({'pair': s, 'pnl': pnl, 'reason': global_exit_reason, 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx}
                continue

            for s in self.pair_data:
                idx = symbol_indices[s].get(ts)
                if idx is None or idx < 250: continue
                pos = active_positions[s]
                s_data = np_data[s]
                price = s_data['close'][idx]

                if pos['qty'] > 0:
                    pos['max_p'] = max(pos['max_p'], price)
                    profit_pct = (price - pos['entry_price']) / pos['entry_price']
                    
                    trail_trigger = params.get('TRAILING_TRIGGER', 0.040)
                    trail_dist = params.get('TRAILING_DIST', 0.020)
                    be_trigger = params.get('BE_TRIGGER', 0.020)
                    be_lock = params.get('BE_LOCK', 0.002)
                    
                    if profit_pct > trail_trigger:
                        pos['sl'] = max(pos['sl'], price * (1.0 - trail_dist))
                    elif profit_pct > be_trigger:
                        pos['sl'] = max(pos['sl'], pos['entry_price'] * (1.0 + be_lock))

                    if price <= pos['sl']:
                        exit_price = price * (1.0 - slippage_pct)
                        pnl = ((exit_price / pos['entry_price']) - 1) * 100
                        trades.append({'pair': s, 'pnl': pnl, 'reason': 'SL', 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})
                        balance += pos['qty'] * exit_price * 0.999
                        active_positions[s] = {'qty': 0.0, 'entry_price': 0.0, 'sl': 0.0, 'max_p': 0.0, 'time': 0, 'last_close_time': idx}

                else:
                    cooldown_min = params.get('COOLDOWN_PERIOD', 600) / 60.0
                    if (idx - pos.get('last_close_time', -99999)) < cooldown_min: continue
                    
                    setup = None
                    btc_uptrend = s_data['btc_uptrend'][idx]
                    btc_uptrend_15m = s_data['btc_uptrend_15m'][idx]
                    btc_rsi = s_data['btc_rsi'][idx]
                    pair_safe = s_data['pair_safe'][idx]
                    
                    # NEW STRATEGY LOGIC: V100 Optimized Momentum Breakout
                    if btc_uptrend and btc_uptrend_15m and btc_rsi > 30 and pair_safe:
                        if price > s_data['vwap'][idx]:
                            adx = s_data['adx'][idx]
                            vol = s_data['volume'][idx]
                            vol_sma = s_data['vol_sma'][idx]
                            rsi = s_data['rsi'][idx]
                            macdh = s_data['macdh'][idx]
                            macdh_prev = s_data['macdh'][idx-1] if idx > 0 else 0.0
                            
                            if adx > params.get('ADX_THRESHOLD', 25.0) and rsi < 70:
                                if macdh > 0 and macdh_prev <= 0:
                                    if vol > vol_sma * 1.5:
                                        setup = "V100_Momentum"
                                        
                    # Alternative test: Mean Reversion
                    # if not setup and btc_uptrend and pair_safe:
                    #     if price > s_data['vwap'][idx]:
                    #         rsi = s_data['rsi'][idx]
                    #         rsi_prev = s_data['rsi'][idx-1]
                    #         if rsi > 35 and rsi_prev <= 35:
                    #             setup = "V99_Pullback"

                    if setup:
                        atr = s_data['atr'][idx]
                        volatility = atr / price
                        if params.get('MIN_VOLATILITY', 0.0010) <= volatility <= params.get('VOLATILITY_CAP', 0.015):
                            if balance > 10.1:
                                size_strength = params.get('SCALE_1_POS', 0.8) if active_count == 0 else (params.get('SCALE_2_POS', 0.6) if active_count == 1 else params.get('SCALE_3_POS', 0.4))
                                risk_usd = current_equity * (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                                sl_dist_price = min(max(params.get('ATR_SL_MULT', 2.5) * atr, price * params.get('SL_MIN_PCT', 0.015)), price * params.get('SL_MAX_PCT', 0.030))
                                trade_amount = min((risk_usd / sl_dist_price) * price, current_equity * (params.get('MAX_RISK_PER_TRADE_PERCENT', 15.0) / 100.0) * size_strength)
                                trade_amount = max(trade_amount, 10.1)

                                if trade_amount <= balance:
                                    entry_price = price * (1.0 + slippage_pct)
                                    pos['qty'] = (trade_amount * 0.999) / entry_price
                                    pos['entry_price'] = entry_price
                                    pos['max_p'] = entry_price
                                    pos['sl'] = entry_price - sl_dist_price
                                    pos['time'] = idx
                                    pos['setup'] = setup
                                    balance -= trade_amount
                                    active_count += 1

        final_balance = balance
        for s in active_positions:
            pos = active_positions[s]
            if pos['qty'] > 0:
                final_price = np_data[s]['close'][-1]
                exit_price = final_price * (1.0 - slippage_pct)
                final_balance += pos['qty'] * exit_price * 0.9985
                trades.append({'pair': s, 'pnl': ((exit_price / pos['entry_price']) - 1) * 100, 'reason': 'EOD', 'entry': pos['entry_price'], 'exit': exit_price, 'setup': pos.get('setup', 'Unknown')})

        self.trades = trades
        wins = len([t for t in trades if t['pnl'] > 0])
        losses = len([t for t in trades if t['pnl'] <= 0])
        print(f"Total Trades: {len(trades)} | Wins: {wins} | Losses: {losses}")
        if trades: print(f"Average Win: {sum([t['pnl'] for t in trades if t['pnl'] > 0])/max(1,wins):.2f}% | Average Loss: {sum([t['pnl'] for t in trades if t['pnl'] <= 0])/max(1,losses):.2f}%")
        return ((final_balance - initial_balance) / initial_balance) * 100

    backtester.run = new_run.__get__(backtester, PortfolioBacktester)
    
    print("\n--- New Logic (V100 Momentum Breakout) ---")
    pnl = backtester.run(config)
    print(f"PnL: {pnl:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
