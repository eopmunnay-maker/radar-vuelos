#!/bin/bash
# Demo guiada del Radar de Vuelos — para grabar el video.
# Ejecuta cada paso cuando pulses ENTER.
cd "$(dirname "$0")"

paso() {
  echo ""
  echo "════════════════════════════════════════════════"
  echo "  $1"
  echo "════════════════════════════════════════════════"
  read -r -p "▶ Pulsa ENTER para ejecutar este paso... "
  echo ""
}

clear
echo ""
echo "  ✈️  RADAR DE VUELOS — DEMO EN VIVO"
echo "  Travelpayouts · SQLite · Telegram · Google Calendar"
echo ""

paso "PASO 1 — Buscar precios reales: Lima → Cusco (ruta, fecha, precio, aerolínea, escalas)"
python3 radar.py buscar lima cusco 2026-09-15

paso "PASO 2 — Histórico de precios guardado en SQLite"
python3 radar.py historial lima cusco

paso "PASO 3 — Gráfico de evolución de precios"
python3 radar.py grafico lima cusco && open evolucion.png

paso "PASO 4 — Vigilancia automática: si el precio baja del umbral, alerta por Telegram 🚨"
python3 radar.py vigilar lima cusco 2026-09-15 --umbral 50 --una-vez

paso "PASO 5 — Decidí viajar: el agente crea el evento en Google Calendar por API 🗓️"
python3 radar.py viajar lima cusco 2026-09-15

echo ""
echo "════════════════════════════════════════════════"
echo "  ✅ FIN DE LA DEMO"
echo "  Extras: python3 radar.py panel   (panel web)"
echo "          python3 radar.py escuchar (bot conversacional)"
echo "════════════════════════════════════════════════"
