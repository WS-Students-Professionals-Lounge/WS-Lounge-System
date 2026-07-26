import os
import sys
import subprocess

cwd = os.getcwd()
print('cwd=', cwd)

result = subprocess.run([
    os.path.join('.', 'venv', 'Scripts', 'python.exe'),
    '-m',
    'pytest',
    '-q',
], capture_output=True, text=True)
with open('pytest_output.txt', 'w', encoding='utf-8') as f:
    f.write('STDOUT:\n')
    f.write(result.stdout)
    f.write('\nSTDERR:\n')
    f.write(result.stderr)
    f.write('\nEXIT=' + str(result.returncode) + '\n')
print('done', result.returncode)
