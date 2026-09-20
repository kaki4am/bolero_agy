import re

with open('/root/portfolio_backtester.py', 'r') as f:
    content = f.read()

# 1. Add altcoin_24h_return and high_1h_prev
content = content.replace("df_1h['altcoin_4h_return'] = (df_1h['close'] - df_1h['close'].shift(4)) / df_1h['close'].shift(4) * 100",
"""df_1h['altcoin_4h_return'] = (df_1h['close'] - df_1h['close'].shift(4)) / df_1h['close'].shift(4) * 100
            df_1h['altcoin_24h_return'] = (df_1h['close'] - df_1h['close'].shift(24)) / df_1h['close'].shift(24) * 100
            df_1h['high_1h_prev'] = df_1h['high'].shift(1)""")

content = content.replace("indicators['altcoin_4h_return'] = df_1h_idx['altcoin_4h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)",
"""indicators['altcoin_4h_return'] = df_1h_idx['altcoin_4h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['altcoin_24h_return'] = df_1h_idx['altcoin_24h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['high_1h_prev'] = df_1h_idx['high_1h_prev'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)""")

content = content.replace("'altcoin_4h_return': ind['altcoin_4h_return'].values,",
"""'altcoin_4h_return': ind['altcoin_4h_return'].values,
                'altcoin_24h_return': ind['altcoin_24h_return'].values,
                'high_1h_prev': ind['high_1h_prev'].values,""")

# 2. active_positions init
content = content.replace("'last_close_time': -99999, 'last_loss': False}",
"'last_close_time': -99999, 'last_loss': False, 'last_large_win_time': -99999}")

# 3. Global eject update active_positions
content = content.replace("'last_close_time': idx, 'last_loss': pnl < 0}",
"'last_close_time': idx, 'last_loss': pnl < 0, 'last_large_win_time': pos.get('last_large_win_time', -99999)}")

# 4. Zombie Exit & Staleness removal
content = re.sub(r"if hold_time_m > params\.get\('STALENESS_TIME_H', 24\) \* 60:\n\s*if params\.get\('STALENESS_EXIT_MIN', -0\.005\) <= current_profit_pct <= params\.get\('STALENESS_EXIT_MAX', 0\.005\):\n\s*exit_reason = \"StalenessExit\"\n\s*exit_price = price \* \(1\.0 - slippage_pct\)",
"""if hold_time_m > 120 * 60:
                        if pos['max_p'] < pos['entry_price'] * 1.01 and s_data['hourly_volume'][idx] < s_data['vol_1h_avg_24h'][idx]:
                            exit_reason = "ZombieExit"
                            exit_price = price * (1.0 - slippage_pct)""", content)

# 5. Exit trade update active_positions
content = content.replace("'last_close_time': idx, 'last_loss': pnl < 0}",
"'last_close_time': idx, 'last_loss': pnl < 0, 'last_large_win_time': idx if pnl > 5.0 else pos.get('last_large_win_time', -99999)}")

# 6. Re-entry cooldown
content = content.replace("cooldown_min = params.get('COOLDOWN_PERIOD', 600) / 60.0",
"""if (idx - pos.get('last_large_win_time', -99999)) < 120 and price > s_data['ema_20_1h'][idx]:
                        continue
                    cooldown_min = params.get('COOLDOWN_PERIOD', 600) / 60.0""")

# 7. Setup & Adaptive Vol & TEB
setup_logic = """setup = None
                    
                    bb_upper = s_data['bb_upper'][idx]
                    
                    btc_4h_ret = s_data['btc_4h_return'][idx]
                    alt_4h_ret = s_data['altcoin_4h_return'][idx]
                    alt_24h_ret = s_data['altcoin_24h_return'][idx]
                    is_macro_decoupled = params.get('DECOUPLE_BTC_MIN', -3.0) <= btc_4h_ret <= params.get('DECOUPLE_BTC_MAX', 1.0) and alt_4h_ret > (btc_4h_ret + params.get('DECOUPLE_ALT_RET', 3.0))
                    hourly_vol = s_data['hourly_volume'][idx]
                    avg_vol = s_data['vol_1h_avg_24h'][idx]
                    
                    if is_macro_decoupled:
                        if hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout"  
                                
                    relative_range = s_data['alt_daily_range_pct'][idx] / max(s_data['btc_daily_range_pct'][idx], 1.0)
                    is_high_beta = relative_range >= params.get('RDR_MIN', 1.6)
                    ema20, ema50 = s_data['ema_20_1h'][idx], s_data['ema_50_1h'][idx]
                    trend_aligned = price > ema20 > ema50 if ema50 > 0 else False
                    
                    if is_high_beta and is_macro_decoupled and trend_aligned and hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:
                        setup = "Decoupled_Trend_Continuation"

                    if is_macro_decoupled and trend_aligned:
                        trend_efficiency = alt_24h_ret / max(s_data['alt_daily_range_pct'][idx], 1.0)
                        if relative_range >= 1.6 and trend_efficiency >= 0.35:
                            if price > s_data['high_1h_prev'][idx] and hourly_vol > params.get('VOL_THRESHOLD', 1.5) * avg_vol:
                                setup = "Decoupled_Efficiency_Breakout"

                    if setup:
                        volatility = atr / price
                        base_vol_cap = params.get('VOLATILITY_CAP', 0.015)
                        dynamic_vol_cap = base_vol_cap * min(max(relative_range, 1.0), 1.75)
                        min_vol = params.get('MIN_VOLATILITY', 0.0010)
                        if volatility > dynamic_vol_cap: setup = None
                        if volatility < min_vol: setup = None"""

content = re.sub(r"setup = None\s+bb_upper = .*?if volatility < min_vol: setup = None", setup_logic, content, flags=re.DOTALL)

# 8. Risk cap
content = content.replace("risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength",
"""risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                            risk_pct = min(risk_pct, 0.015)""")


with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(content)
