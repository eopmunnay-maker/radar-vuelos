#!/bin/bash
cd "$(dirname "$0")"
echo "✈️  Radar de Vuelos — abriendo el panel en tu navegador..."
( sleep 1.5 && open "http://127.0.0.1:4700" ) &
python3 radar.py panel
