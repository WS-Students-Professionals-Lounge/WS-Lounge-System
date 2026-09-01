import re

with open('database_fixed.py', 'r') as f:
    content = f.read()

# Fix line 38: replace ')) with just )
content = re.sub(r'\n\)\)\n', '\n)\n', content, count=1)

with open('database_fixed.py', 'w') as f:
    f.write(content)

print('Fixed')
