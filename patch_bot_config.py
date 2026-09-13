import re

with open('/root/bot.py', 'r') as f:
    content = f.read()

# Replace the hardcoded dictionary with self.config = {}
new_content = re.sub(r"self\.config = \{.*?\n        \}", "self.config = {}", content, flags=re.DOTALL)

with open('/root/bot.py', 'w') as f:
    f.write(new_content)
