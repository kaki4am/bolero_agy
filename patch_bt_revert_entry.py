import re

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

old_run = """btc_ret = s_data['btc_4h_return'][idx]
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

new_run = """btc_ret = s_data['btc_24h_return'][idx]
                    alt_24h_ret = s_data['altcoin_24h_return'][idx]
                    alt_24h_vol = s_data['altcoin_24h_volume'][idx]
                    alt_24h_vol_sma7 = s_data['altcoin_24h_vol_sma7'][idx]
                    
                    if alt_24h_ret > (btc_ret + 2.5) and alt_24h_vol > alt_24h_vol_sma7:
                        hourly_vol = s_data['hourly_volume'][idx]
                        avg_vol = s_data['vol_1h_avg_24h'][idx]
                        if hourly_vol > 1.5 * avg_vol:
                            bb_width_prev = s_data['bb_width_prev'][idx]
                            bbw = s_data['bb_width'][idx]
                            if price > bb_upper and bbw > bb_width_prev:
                                setup = "Decoupled_Squeeze_Breakout" """

code = re.sub(re.escape(old_run), new_run, code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
