# ✈️ Radar de Vuelos

Agente construido con IA (Codex/Claude Code) que consulta precios de vuelos en
**Travelpayouts**, guarda un **histórico en SQLite**, muestra la **evolución de
precios**, envía **alertas por Telegram** y **propone eventos en Google
Calendar** cuando el usuario decide viajar.

> Proyecto integrador — Clase 02 · Actividad calificada.

## Funcionalidades

- 🔎 **Consulta de ruta, fecha, precio, aerolínea y escalas** (API Aviasales/Travelpayouts v3).
- 📒 **Histórico** de cada consulta en SQLite (`radar.db`).
- 📈 **Visualización** de la evolución de precios (gráfico PNG, enviable por Telegram).
- 🚨 **Alertas automáticas** por bot de Telegram cuando el precio baja del umbral o cae ≥5%.
- 🗓️ **Google Calendar**: al decidir viajar, el agente propone el evento (enlace directo, o creación automática vía API si configuras credenciales).
- 🧪 **Modo demo**: sin API keys genera precios simulados para probar todo el flujo.

## Instalación

```bash
git clone https://github.com/eopmunnay-maker/radar-vuelos.git
cd radar-vuelos
pip install -r requirements.txt
cp .env.example .env   # y completa tus credenciales (opcional)
```

## Uso

```bash
# 1. Buscar precios (consulta + guarda histórico)
python radar.py buscar LIM CUZ 2026-09-15

# 2. Ver el histórico de la ruta
python radar.py historial LIM CUZ

# 3. Gráfico de evolución de precios (y enviarlo por Telegram)
python radar.py grafico LIM CUZ --telegram

# 4. Vigilar la ruta: consulta cada hora y alerta por Telegram
python radar.py vigilar LIM CUZ 2026-09-15 --umbral 120 --intervalo 3600

# (para cron/launchd: una sola pasada)
python radar.py vigilar LIM CUZ 2026-09-15 --umbral 120 --una-vez

# 5. Decidí viajar → proponer evento en Google Calendar
python radar.py viajar LIM CUZ 2026-09-15
```

## Arquitectura

```
radar.py            CLI del agente (buscar / historial / grafico / vigilar / viajar)
├── travelpayouts.py  Cliente API Aviasales v3 (+ modo demo sin token)
├── db.py             Histórico de precios en SQLite
├── grafico.py        Evolución de precios con matplotlib
├── telegram_bot.py   Alertas vía Bot API de Telegram
├── calendario.py     Eventos en Google Calendar (enlace o API)
└── config.py         Configuración desde .env
```

Flujo de una alerta:

```
vigilar → Travelpayouts API → guardar en SQLite → ¿precio ≤ umbral o bajó ≥5%?
                                                        │ sí
                                                        ▼
                                              Bot de Telegram 🚨
```

## Credenciales

| Servicio | Variable | Dónde obtenerla |
|---|---|---|
| Travelpayouts | `TRAVELPAYOUTS_TOKEN` | app.travelpayouts.com → perfil → API token |
| Telegram | `TELEGRAM_BOT_TOKEN` | @BotFather → `/newbot` |
| Telegram | `TELEGRAM_CHAT_ID` | `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| Google Calendar (opcional) | `credentials.json` | Google Cloud Console → OAuth Desktop |

Sin credenciales el agente **sigue funcionando en modo demo** (precios
simulados y alertas impresas en consola), ideal para la demostración.

## Cómo se usó la IA (Codex)

El agente fue construido de forma iterativa con un agente de código:
se le describió el objetivo (radar de precios con histórico, alertas y
calendario) y generó la arquitectura modular, el cliente de la API, el
esquema SQLite y el CLI; luego se refinaron los umbrales de alerta y el
modo demo para poder demostrarlo sin credenciales.
