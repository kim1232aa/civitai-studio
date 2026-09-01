#!/bin/sh
cd "$(dirname "$0")"
python3 static_patch.py
exec python3 server.py
