import json

with open('/root/config.json', 'r') as f:
    c = json.load(f)

c['PORTFOLIO_EJECT'] = -5.632436172471953

with open('/root/config.json', 'w') as f:
    json.dump(c, f, indent=4)

