"""Vercel entry point for the WS Lounge Flask application."""

import os
import sys


project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "high_end_ws_lounge")
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from run import app


if __name__ == "__main__":
    app.run()