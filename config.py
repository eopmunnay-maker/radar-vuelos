"""Configuración del Radar de Vuelos.

Lee las variables desde un archivo .env (si existe) o del entorno.
Si no hay token de Travelpayouts, el agente funciona en MODO DEMO
con precios simulados, para poder probar todo el flujo.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "radar.db"


def _cargar_env():
    """Carga .env manualmente (sin dependencias externas)."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for linea in env_file.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()

# --- Travelpayouts ---
TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN", "")
MONEDA = os.environ.get("MONEDA", "usd")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Modo demo: se activa solo si no hay token de Travelpayouts
MODO_DEMO = not TRAVELPAYOUTS_TOKEN
