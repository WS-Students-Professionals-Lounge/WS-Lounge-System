with open('database_fixed.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(34, 42):
        print(f'{i+1}: {repr(lines[i])}')
