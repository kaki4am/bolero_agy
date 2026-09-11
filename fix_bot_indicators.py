import re

with open('/root/bot.py', 'r') as f:
    content = f.read()

# Fix unused bb_1h / bbw_1h
content = re.sub(r' +if len\(close_1h\) >= 24:\n +bb_1h = ta\.bbands\(close_1h, length=20, std=2\.0\)\n +if bb_1h is not None and not bb_1h\.empty:\n +bbw_1h = \(bb_1h\[\'BBU_20_2\.0_2\.0\'\] - bb_1h\[\'BBL_20_2\.0_2\.0\'\]\) / bb_1h\[\'BBM_20_2\.0_2\.0\'\]\n +cache_data\.update\(\{\'bbw_1h\': bbw_1h\.iloc\[-1\], \'min_bbw_24_1h\': bbw_1h\.iloc\[-24:\]\.min\(\)\}\)\n', '', content)

with open('/root/bot.py', 'w') as f:
    f.write(content)
