with open('database_fixed.py', 'r') as f:
    lines = f.readlines()
    print(f'Total lines: {len(lines)}')
    print(f'First 5 lines after line 40:')
    for i, line in enumerate(lines[40:45]):
        print(f'{41+i}: {line.rstrip()}')
