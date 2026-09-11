import re

with open('/root/bot.py', 'r') as f:
    code = f.read()

# 1. Update blacklisted in bot.py
code = re.sub(
    r"blacklisted = \['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT', \n\s+'SOLUSDT', 'AVAXUSDT', 'PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'LUNCUSDT',\n\s+'FETUSDT', 'INJUSDT', 'NEARUSDT', 'DOTUSDT', 'FILUSDT', 'LDOUSDT', 'XECUSDT', 'SHIBUSDT', 'DODOUSDT',\n\s+'WLDUSDT', 'ADAUSDT', 'LINKUSDT', 'XRPUSDT', 'LTCUSDT',\n\s+'HFTUSDT', 'PEOPLEUSDT', 'ONGUSDT', 'SYNUSDT', 'COTIUSDT', 'CRVUSDT',\n\s+'XAUTUSDT', 'QQQBUSDT', 'MITOUSDT', 'MARSCOINUSDT'\]",
    "blacklisted = ['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'EURUSDT', 'USDTUSDT', 'BUSDUSDT', 'DAIUSDT', \n                       'AVAXUSDT', 'PEPEUSDT', 'DOGEUSDT', 'PENDLEUSDT', 'LUNCUSDT', 'VETUSDT', 'LAPTOPUSDT', 'REZUSDT', 'ANIMEUSDT', 'SAGAUSDT',\n                       'FETUSDT', 'INJUSDT', 'NEARUSDT', 'DOTUSDT', 'FILUSDT', 'LDOUSDT', 'XECUSDT', 'SHIBUSDT', 'DODOUSDT',\n                       'WLDUSDT', 'ADAUSDT', 'LINKUSDT', 'XRPUSDT', 'LTCUSDT',\n                       'HFTUSDT', 'PEOPLEUSDT', 'ONGUSDT', 'SYNUSDT', 'COTIUSDT', 'CRVUSDT',\n                       'XAUTUSDT', 'QQQBUSDT', 'MITOUSDT', 'MARSCOINUSDT']",
    code
)

# 2. Update btc_ret_4h in fetch_macro_trends
btc_ret_code = r"btc_ret_24h = \(btc_cp_15m - closes_15m\.iloc\[-97\]\) / closes_15m\.iloc\[-97\] \* 100 if len\(closes_15m\) > 96 else 0\.0"
new_btc_ret = """btc_ret_24h = (btc_cp_15m - closes_15m.iloc[-97]) / closes_15m.iloc[-97] * 100 if len(closes_15m) > 96 else 0.0
            btc_ret_4h = (btc_cp_15m - closes_15m.iloc[-17]) / closes_15m.iloc[-17] * 100 if len(closes_15m) > 16 else 0.0"""
code = re.sub(btc_ret_code, new_btc_ret, code)

market_trend_dict = r"'btc_uptrend_15m': btc_cp_15m > ema200_15m,\n\s+'btc_24h_return': btc_ret_24h\n\s+\}"
new_market_trend = """'btc_uptrend_15m': btc_cp_15m > ema200_15m,
                'btc_24h_return': btc_ret_24h,
                'btc_4h_return': btc_ret_4h
            }"""
code = re.sub(market_trend_dict, new_market_trend, code)

# 3. Update 1h context
old_cache_update = r"if len\(close_1h\) >= 25:\n\s+cache_data\.update\(\{'altcoin_24h_return': \(close_1h\.iloc\[-1\] - close_1h\.iloc\[-25\]\) / close_1h\.iloc\[-25\] \* 100\}\)\n\s+else:\n\s+cache_data\.update\(\{'altcoin_24h_return': 0\.0\}\)"
new_cache_update = """if len(close_1h) >= 25:
                            cache_data.update({'altcoin_24h_return': (close_1h.iloc[-1] - close_1h.iloc[-25]) / close_1h.iloc[-25] * 100})
                        else:
                            cache_data.update({'altcoin_24h_return': 0.0})
                        if len(close_1h) >= 5:
                            cache_data.update({'altcoin_4h_return': (close_1h.iloc[-1] - close_1h.iloc[-5]) / close_1h.iloc[-5] * 100})
                        else:
                            cache_data.update({'altcoin_4h_return': 0.0})
                        if len(close_1h) >= 24:
                            bb_1h = ta.bbands(close_1h, length=20, std=2.0)
                            if bb_1h is not None and not bb_1h.empty:
                                bbw_1h = (bb_1h['BBU_20_2.0_2.0'] - bb_1h['BBL_20_2.0_2.0']) / bb_1h['BBM_20_2.0_2.0']
                                cache_data.update({'bbw_1h': bbw_1h.iloc[-1], 'min_bbw_24_1h': bbw_1h.iloc[-24:].min()})
                        if len(close_1h) >= 14:
                            rsi_1h = ta.rsi(close_1h, length=14)
                            if rsi_1h is not None and not rsi_1h.empty:
                                cache_data.update({'rsi_1h': rsi_1h.iloc[-1]})
"""
code = re.sub(old_cache_update, new_cache_update, code)


with open('/root/bot.py', 'w') as f:
    f.write(code)
