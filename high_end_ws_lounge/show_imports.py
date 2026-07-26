with open('database_fixed.py', 'r') as f:
    lines = f.readlines()
    for i in range(16, 30):
        print(f'{i+1}: {lines[i].rstrip()}')
