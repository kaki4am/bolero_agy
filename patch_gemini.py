import re

with open('/root/GEMINI.md', 'r') as f:
    text = f.read()

text = re.sub(r"Strategy V154", "Strategy V155", text)
text = re.sub(r"V154", "V155", text)
text = re.sub(r"- \*\*Time-Decaying Take-Profit\*\*: Gradually lower Take-Profit target threshold as hold duration increases beyond 48 hours to accelerate capital recycling.\n", "", text)
text = re.sub(r"- \*\*Stale Trend Exposure Guard\*\*: If an asset is held for > 72 hours and its 1H momentum turns negative \(Price < SMA20 1H\), trigger an early exit.\n", "", text)

with open('/root/GEMINI.md', 'w') as f:
    f.write(text)
