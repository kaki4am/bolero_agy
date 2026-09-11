import re

with open('/root/portfolio_backtester.py', 'r') as f:
    content = f.read()

content = re.sub(r' +if len\(df_1h\) >= 20:\n +bb_1h = ta\.bbands\(df_1h\[\'close\'\], length=20, std=2\.0\)\n +if bb_1h is not None and not bb_1h\.empty:\n +bbw_1h = \(bb_1h\[\'BBU_20_2\.0_2\.0\'\] - bb_1h\[\'BBL_20_2\.0_2\.0\'\]\) / bb_1h\[\'BBM_20_2\.0_2\.0\'\]\n +df_1h\[\'bbw_1h\'\] = bbw_1h\n +else:\n +df_1h\[\'bbw_1h\'\] = 0\.0\n +else:\n +df_1h\[\'bbw_1h\'\] = 0\.0\n +df_1h\[\'min_bbw_24_1h\'\] = df_1h\[\'bbw_1h\'\]\.rolling\(24, min_periods=1\)\.min\(\)\n', '', content)
content = re.sub(r' +indicators\[\'bbw_1h\'\] = df_1h_idx\[\'bbw_1h\'\]\.reindex\(df_1m_idx\.index\)\.ffill\(\)\.bfill\(\)\.fillna\(0\.0\)\n', '', content)
content = re.sub(r' +indicators\[\'min_bbw_24_1h\'\] = df_1h_idx\[\'min_bbw_24_1h\'\]\.reindex\(df_1m_idx\.index\)\.ffill\(\)\.bfill\(\)\.fillna\(0\.0\)\n', '', content)
content = re.sub(r' +\'bbw_1h\': ind\[\'bbw_1h\'\]\.values,\n', '', content)
content = re.sub(r' +\'min_bbw_24_1h\': ind\[\'min_bbw_24_1h\'\]\.values,\n', '', content)

with open('/root/portfolio_backtester.py', 'w') as f:
    f.write(content)
