filename = 'database_fixed.py'
with open(filename, 'r') as f:
    lines = f.readlines()
    
print(f'Total lines: {len(lines)}')
print('\nLines 17-32 (import section):')
for i in range(16, min(32, len(lines))):
    print(f'{i+1}: {repr(lines[i])}')
