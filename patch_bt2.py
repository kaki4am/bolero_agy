import re

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

# np_data additions
np_code = r"'btc_24h_return': ind\['btc_safe'\]\['btc_24h_return'\].values if 'btc_24h_return' in ind\['btc_safe'\] else pd\.Series\(0\.0, index=df\.index\)\.values,"
new_np_code = """'btc_24h_return': ind['btc_safe']['btc_24h_return'].values if 'btc_24h_return' in ind['btc_safe'] else pd.Series(0.0, index=df.index).values,
                'btc_4h_return': ind['btc_safe']['btc_4h_return'].values if 'btc_4h_return' in ind['btc_safe'] else pd.Series(0.0, index=df.index).values,
                'altcoin_4h_return': ind['altcoin_4h_return'].values,
                'rsi_1h': ind['rsi_1h'].values,
                'bbw_1h': ind['bbw_1h'].values,
                'min_bbw_24_1h': ind['min_bbw_24_1h'].values,"""
code = re.sub(np_code, new_np_code, code)

# Logic replacements
run_logic = r"btc_ret = s_data\['btc_24h_return'\]\[idx\]\n\s+alt_24h_ret = s_data\['altcoin_24h_return'\]\[idx\]\n\s+alt_24h_vol = s_data\['altcoin_24h_volume'\]\[idx\]\n\s+alt_24h_vol_sma7 = s_data\['altcoin_24h_vol_sma7'\]\[idx\]\n\s+# 1\. Relative Strength Decoupling Filter \(Entry Filter\)\n\s+# Altcoin 24h Return % > \(BTC 24h Return % \+ 2\.5%\) and Altcoin 24h Volume > SMA\(Altcoin 24h Volume, 7\)\n\s+if alt_24h_ret > \(btc_ret \+ 2\.5\) and alt_24h_vol > alt_24h_vol_sma7:\n\s+# 2\. Volume-Anomaly Squeeze Breakout \(Entry Signal\)\n\s+# Current Hourly Volume > 1\.5 \* SMA\(Hourly Volume, 24\)\n\s+hourly_vol = s_data\['hourly_volume'\]\[idx\]\n\s+avg_vol = s_data\['vol_1h_avg_24h'\]\[idx\]\n\s+if hourly_vol > 1\.5 \* avg_vol:\n\s+# Squeeze Exit: price > bb_upper and bands expanding\n\s+bb_width_prev = s_data\['bb_width_prev'\]\[idx\]\n\s+bbw = s_data\['bb_width'\]\[idx\]\n\s+if price > bb_upper and bbw > bb_width_prev:\n\s+setup = \"Decoupled_Squeeze_Breakout\""

new_run = """btc_ret = s_data['btc_4h_return'][idx]
                    alt_4h_ret = s_data['altcoin_4h_return'][idx]
                    hourly_vol = s_data['hourly_volume'][idx]
                    avg_vol = s_data['vol_1h_avg_24h'][idx]
                    bbw_1h = s_data['bbw_1h'][idx]
                    min_bbw_24 = s_data['min_bbw_24_1h'][idx]
                    rsi_1h = s_data['rsi_1h'][idx]
                    
                    if alt_4h_ret > (btc_ret + 2.5) and hourly_vol > 2.5 * avg_vol:
                        if bbw_1h > 1.5 * min_bbw_24 and rsi_1h > 65:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout" """
code = re.sub(run_logic, new_run, code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
