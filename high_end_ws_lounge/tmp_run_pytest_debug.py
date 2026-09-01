import os
import traceback
import subprocess

cwd = os.getcwd()
print('cwd=', cwd)
output = []
try:
    proc = subprocess.run(
        [os.path.join('.', 'venv', 'Scripts', 'python.exe'), '-m', 'pytest', 'tests/test_admin_billing.py', '-q'],
        capture_output=True,
        text=True,
        timeout=20,
    )
    output.append('RETURNCODE=' + str(proc.returncode))
    output.append('STDOUT:\n' + proc.stdout)
    output.append('STDERR:\n' + proc.stderr)
except subprocess.TimeoutExpired as exc:
    output.append('TIMEOUT EXPIRED')
    output.append('STDOUT:\n' + (exc.stdout or ''))
    output.append('STDERR:\n' + (exc.stderr or ''))
except Exception:
    output.append('EXCEPTION:\n' + traceback.format_exc())
with open('pytest_output_debug.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print('wrote debug output')
