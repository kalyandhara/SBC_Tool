#!/usr/bin/env python3
"""Unified SBC app entrypoint.

Usage:
  python run_app.py
  python run_app.py --host 127.0.0.1 --port 8000 --debug
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(r"D:\SBC_Tool - Copy").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Activate venv if present
venv_python = ROOT / "venv" / "Scripts" / "python.exe"
if venv_python.exists() and sys.executable != str(venv_python):
    os.execl(str(venv_python), str(venv_python), *sys.argv)

parser = argparse.ArgumentParser(description="Run SBC Flask app")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
parser.add_argument("--port", type=int, default=8000, help="Port to bind")
parser.add_argument("--debug", action="store_true", help="Run in debug mode")
args = parser.parse_args()

# Import app lazily after path setup
from app import app

if __name__ == "__main__":
    # Flask already bootstraps DB via _bootstrap()
    app.run(host=args.host, port=args.port, debug=args.debug)