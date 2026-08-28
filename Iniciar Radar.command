#!/bin/bash
cd "$(dirname "$0")"
PY="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
pkill -f "radar.py panel" 2>/dev/null
sleep 0.5
( sleep 1.5 && open "http://127.0.0.1:4700" ) &
echo "✈️  Radar de Vuelos encendido — el panel se abre en tu navegador."
echo "    (No cierres esta ventana mientras uses el panel)"
"$PY" radar.py panel
