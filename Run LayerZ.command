#!/bin/bash
# Double-click this file in Finder to launch LayerZ without using the terminal.
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
else
  source .venv/bin/activate
fi

python3 run.py
