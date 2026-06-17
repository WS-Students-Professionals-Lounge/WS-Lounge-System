#!/usr/bin/env python3
"""
Root-level run script for WS Lounge System.
Automatically cds into high_end_ws_lounge/ and runs the main app.
"""

import os
import subprocess
import sys

# Change to the app directory
app_dir = 'high_end_ws_lounge'
if not os.path.exists(app_dir):
    print(f"Error: {app_dir} not found. Make sure you're in the project root.")
    sys.exit(1)

os.chdir(app_dir)
print(f"Changed to {os.path.abspath(app_dir)}")

# Optional: activate venv if exists
venv_path = os.path.join(app_dir, 'venv', 'Scripts', 'activate.bat')
if os.path.exists(venv_path):
    print("Venv found, but activation is manual. Run 'high_end_ws_lounge\\venv\\Scripts\\activate' first if needed.")

# Run the actual run.py
try:
    subprocess.call([sys.executable, 'run.py'] + sys.argv[1:])
except FileNotFoundError:
    print("Error: high_end_ws_lounge/run.py not found.")
    sys.exit(1)

