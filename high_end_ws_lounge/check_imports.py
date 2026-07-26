with open('database_fixed.py', 'r') as f:
    for i in range(40):
        line = f.readline()
        print(f'{i+1}: {line.rstrip()}')
