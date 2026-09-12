import re

with open('portfolio_backtester.py', 'r') as f:
    content = f.read()

# 1. Update Blacklist
content = re.sub(
    r"blacklist = \['PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'VETUSDT', 'LAPTOPUSDT', 'REZUSDT', 'ANIMEUSDT', 'SAGAUSDT'\]",
    "blacklist = ['PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'VETUSDT', 'LAPTOPUSDT', 'REZUSDT', 'ANIMEUSDT', 'SAGAUSDT', 'ENSUSDT', 'PEOPLEUSDT', 'HFTUSDT', 'ONGUSDT', 'DEXEUSDT', 'SYNUSDT', 'HEIUSDT', 'COTIUSDT']",
    content
)

# 2. Add altcoin_4h_return to precalculate_all
content = re.sub(
    r"df_1h\['altcoin_24h_return'\] = \(df_1h\['close'\] - df_1h\['close'\].shift\(24\)\) / df_1h\['close'\].shift\(24\) \* 100",
    "df_1h['altcoin_24h_return'] = (df_1h['close'] - df_1h['close'].shift(24)) / df_1h['close'].shift(24) * 100\n            df_1h['altcoin_4h_return'] = (df_1h['close'] - df_1h['close'].shift(4)) / df_1h['close'].shift(4) * 100",
    content
)
content = re.sub(
    r"indicators\['altcoin_24h_return'\] = df_1h_idx\['altcoin_24h_return'\].reindex\(df_1m_idx.index\).ffill\(\).bfill\(\).fillna\(0\)",
    "indicators['altcoin_24h_return'] = df_1h_idx['altcoin_24h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)\n            indicators['altcoin_4h_return'] = df_1h_idx['altcoin_4h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)",
    content
)

# 3. Add to np_data
content = re.sub(
    r"'altcoin_24h_return': ind\['altcoin_24h_return'\].values,",
    "'altcoin_24h_return': ind['altcoin_24h_return'].values,\n                'altcoin_4h_return': ind['altcoin_4h_return'].values,",
    content
)

# 4. ProfitGuard & TimeDecay
# Replace ProfitGuard logic block
old_profit_guard = """                    # Minimum hold: 360 candles (6h) before tightening to breakeven
                    hold_time_m = idx - pos['time']
                    min_hold_passed = hold_time_m > 360
                    
                    high_profit_pct = (high_price - pos['entry_price']) / pos['entry_price']
                    current_profit_pct = (price - pos['entry_price']) / pos['entry_price']
                    old_sl = pos['sl']
                    entry = pos['entry_price']
                    
                    if min_hold_passed:
                        if high_profit_pct > trail_trigger:
                            pos['sl'] = max(pos['sl'], high_price * (1.0 - trail_dist))
                        elif high_profit_pct > be_trigger:
                            pos['sl'] = max(pos['sl'], entry * (1.0 + be_lock))"""

new_profit_guard = """                    hold_time_m = idx - pos['time']
                    high_profit_pct = (high_price - pos['entry_price']) / pos['entry_price']
                    current_profit_pct = (price - pos['entry_price']) / pos['entry_price']
                    old_sl = pos['sl']
                    entry = pos['entry_price']
                    
                    if high_profit_pct > params.get('TRAILING_TRIGGER', 0.08):
                        pos['sl'] = max(pos['sl'], high_price * (1.0 - params.get('TRAILING_DIST', 0.035)))"""
content = content.replace(old_profit_guard, new_profit_guard)

# Add TimeDecay to exit reasons
time_decay = """                    if hold_time_m > 48 * 60:
                        alt_24h_ret_c = s_data['altcoin_24h_return'][idx]
                        alt_24h_vol_c = s_data['altcoin_24h_volume'][idx]
                        alt_24h_vol_sma7_c = s_data['altcoin_24h_vol_sma7'][idx]
                        if alt_24h_ret_c < 1.0 or alt_24h_vol_c < alt_24h_vol_sma7_c * 0.8:
                            exit_reason = "TimeDecay"
                            exit_price = price * (1.0 - slippage_pct)
                    
                    if hold_time_m > 24 * 60 and current_profit_pct <= -0.07:"""
content = re.sub(r"if hold_time_m > 24 \* 60 and current_profit_pct <= -0.07:", time_decay, content)


# 5. Setup logic & Risk alignment
setup_old = """                    if alt_24h_ret > (btc_ret + 2.5) and alt_24h_vol > alt_24h_vol_sma7:
                        hourly_vol = s_data['hourly_volume'][idx]
                        avg_vol = s_data['vol_1h_avg_24h'][idx]
                        if hourly_vol > 1.5 * avg_vol:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout\""""

setup_new = """                    btc_4h_ret = s_data['btc_4h_return'][idx]
                    alt_4h_ret = s_data['altcoin_4h_return'][idx]
                    if -3.0 <= btc_4h_ret <= 1.0 and alt_4h_ret > 3.0:
                        hourly_vol = s_data['hourly_volume'][idx]
                        avg_vol = s_data['vol_1h_avg_24h'][idx]
                        if hourly_vol > 2.0 * avg_vol:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout\""""
content = content.replace(setup_old, setup_new)

risk_old = """                            risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                            if not s_data['btc_uptrend_15m'][idx]:
                                risk_pct = risk_pct * 0.5"""

risk_new = """                            risk_pct = (params.get('BASE_RISK_PERCENT', 2.0) / 100.0) * size_strength
                            if not s_data['btc_uptrend_15m'][idx]:
                                btc_4h_ret_risk = s_data['btc_4h_return'][idx]
                                if btc_4h_ret_risk < -1.5:
                                    risk_pct = risk_pct * 0.75
                                elif btc_4h_ret_risk < -1.0:
                                    risk_pct = risk_pct * 0.9"""
content = content.replace(risk_old, risk_new)

with open('portfolio_backtester.py', 'w') as f:
    f.write(content)
print("patched portfolio_backtester.py")
