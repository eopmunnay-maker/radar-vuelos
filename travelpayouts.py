"""Cliente de la API de Travelpayouts (Aviasales Data API v3).

Endpoint usado: /aviasales/v3/prices_for_dates
Docs: https://travelpayouts.github.io/slate/#flight-price-data

Si no hay token configurado (MODO_DEMO), se generan precios simulados
pero realistas, deterministas por hora, para poder demostrar todo el
flujo (histórico, gráfico, alertas) sin credenciales.
"""
import hashlib
import time
from datetime import date, timedelta

import requests

from config import TRAVELPAYOUTS_TOKEN, MONEDA, MODO_DEMO

API_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

AEROLINEAS_DEMO = ["LA", "H2", "JA", "AV", "CM", "SK"]


def buscar_vuelos(origen: str, destino: str, fecha: str | None = None,
                  limite: int = 5) -> list[dict]:
    """Consulta precios para una ruta y fecha. Con fecha=None busca las
    mejores fechas disponibles. Devuelve lista de vuelos normalizados:
    origen, destino, fecha_salida, precio, moneda, aerolinea, escalas, link.
    """
    origen, destino = origen.upper(), destino.upper()
    if MODO_DEMO:
        fecha_demo = fecha or (date.today() + timedelta(days=30)).isoformat()
        return _vuelos_demo(origen, destino, fecha_demo, limite)

    params = {
        "origin": origen,
        "destination": destino,
        "currency": MONEDA,
        "sorting": "price",
        "limit": limite,
        "one_way": "true",
    }
    if fecha:
        params["departure_at"] = fecha
    resp = requests.get(
        API_URL,
        params=params,
        headers={"X-Access-Token": TRAVELPAYOUTS_TOKEN},
        timeout=30,
    )
    resp.raise_for_status()
    datos = resp.json().get("data", [])
    return [
        {
            "origen": v["origin"],
            "destino": v["destination"],
            "fecha_salida": v["departure_at"][:10],
            "precio": float(v["price"]),
            "moneda": MONEDA.upper(),
            "aerolinea": v.get("airline"),
            "escalas": v.get("transfers", 0),
            "link": "https://www.aviasales.com" + v["link"] if v.get("link") else None,
        }
        for v in datos
    ]


def _vuelos_demo(origen: str, destino: str, fecha: str, limite: int) -> list[dict]:
    """Precios simulados: base fija por ruta + variación por hora.

    El hash de (ruta+fecha) fija un precio base; la hora actual agrega
    una oscilación, así el histórico muestra subidas y bajadas reales.
    """
    semilla = hashlib.md5(f"{origen}{destino}{fecha}".encode()).hexdigest()
    base = 150 + int(semilla[:6], 16) % 400          # 150–550 USD
    hora = int(time.time() // 3600)
    vuelos = []
    for i in range(limite):
        osc = int(hashlib.md5(f"{semilla}{hora}{i}".encode()).hexdigest()[:4], 16)
        precio = base + i * 25 + (osc % 120) - 60    # oscila ±60
        vuelos.append({
            "origen": origen,
            "destino": destino,
            "fecha_salida": fecha,
            "precio": float(max(precio, 80)),
            "moneda": "USD",
            "aerolinea": AEROLINEAS_DEMO[(int(semilla[6:8], 16) + i) % len(AEROLINEAS_DEMO)],
            "escalas": (int(semilla[8:10], 16) + i) % 3,
            "link": f"https://www.aviasales.com/search/{origen}{fecha.replace('-', '')[6:]}{destino}1",
        })
    return sorted(vuelos, key=lambda v: v["precio"])
