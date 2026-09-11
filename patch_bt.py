import re

with open('/root/portfolio_backtester.py', 'r') as f:
    code = f.read()

# 1. precalculate_all BTC 4h return
btc_24h_code = r"btc_15m_indexed\['btc_24h_return'\] = \(btc_15m_indexed\['close'\] - btc_15m_indexed\['close'\]\.shift\(96\)\) / btc_15m_indexed\['close'\]\.shift\(96\) \* 100"
new_btc = """btc_15m_indexed['btc_24h_return'] = (btc_15m_indexed['close'] - btc_15m_indexed['close'].shift(96)) / btc_15m_indexed['close'].shift(96) * 100
            btc_15m_indexed['btc_4h_return'] = (btc_15m_indexed['close'] - btc_15m_indexed['close'].shift(16)) / btc_15m_indexed['close'].shift(16) * 100"""
code = re.sub(btc_24h_code, new_btc, code)

align_btc = r"'btc_24h_return': btc_15m_indexed\['btc_24h_return'\]\n\s+\}\)"
new_align = """'btc_24h_return': btc_15m_indexed['btc_24h_return'],
                'btc_4h_return': btc_15m_indexed['btc_4h_return']
            })"""
code = re.sub(align_btc, new_align, code)

# 2. altcoin 1h context
alt_1h_code = r"df_1h\['altcoin_24h_return'\] = \(df_1h\['close'\] - df_1h\['close'\]\.shift\(24\)\) / df_1h\['close'\]\.shift\(24\) \* 100\n\s+df_1h\['altcoin_24h_volume'\] = df_1h\['qav'\]\.rolling\(24, min_periods=1\)\.sum\(\)\n\s+df_1h\['altcoin_24h_vol_sma7'\] = df_1h\['altcoin_24h_volume'\]\.rolling\(24\*7, min_periods=1\)\.mean\(\)"

new_alt = """df_1h['altcoin_24h_return'] = (df_1h['close'] - df_1h['close'].shift(24)) / df_1h['close'].shift(24) * 100
            df_1h['altcoin_4h_return'] = (df_1h['close'] - df_1h['close'].shift(4)) / df_1h['close'].shift(4) * 100
            df_1h['altcoin_24h_volume'] = df_1h['qav'].rolling(24, min_periods=1).sum()
            df_1h['altcoin_24h_vol_sma7'] = df_1h['altcoin_24h_volume'].rolling(24*7, min_periods=1).mean()
            if len(df_1h) >= 14:
                df_1h['rsi_1h'] = ta.rsi(df_1h['close'], length=14)
            else:
                df_1h['rsi_1h'] = 50.0
            
            if len(df_1h) >= 20:
                bb_1h = ta.bbands(df_1h['close'], length=20, std=2.0)
                if bb_1h is not None and not bb_1h.empty:
                    bbw_1h = (bb_1h['BBU_20_2.0_2.0'] - bb_1h['BBL_20_2.0_2.0']) / bb_1h['BBM_20_2.0_2.0']
                    df_1h['bbw_1h'] = bbw_1h
                else:
                    df_1h['bbw_1h'] = 0.0
            else:
                df_1h['bbw_1h'] = 0.0
            df_1h['min_bbw_24_1h'] = df_1h['bbw_1h'].rolling(24, min_periods=1).min()"""
code = re.sub(alt_1h_code, new_alt, code)

# align 1m index
align_1m_code = r"indicators\['altcoin_24h_return'\] = df_1h_idx\['altcoin_24h_return'\]\.reindex\(df_1m_idx\.index\)\.ffill\(\)\.bfill\(\)\.fillna\(0\)"
new_align_1m = """indicators['altcoin_24h_return'] = df_1h_idx['altcoin_24h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['altcoin_4h_return'] = df_1h_idx['altcoin_4h_return'].reindex(df_1m_idx.index).ffill().bfill().fillna(0)
            indicators['rsi_1h'] = df_1h_idx['rsi_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(50.0)
            indicators['bbw_1h'] = df_1h_idx['bbw_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0.0)
            indicators['min_bbw_24_1h'] = df_1h_idx['min_bbw_24_1h'].reindex(df_1m_idx.index).ffill().bfill().fillna(0.0)"""
code = re.sub(align_1m_code, new_align_1m, code)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(code)
