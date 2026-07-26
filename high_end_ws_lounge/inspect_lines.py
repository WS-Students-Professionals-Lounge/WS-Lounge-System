with open('database_fixed.py', 'r') as f:
    for i in range(20):
        line = f.readline()
        print(f'{i+1}: {repr(line)}')
