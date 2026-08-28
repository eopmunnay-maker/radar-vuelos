"""Capa de datos: histórico de precios en SQLite."""
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

ESQUEMA = """
CREATE TABLE IF NOT EXISTS precios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    origen        TEXT NOT NULL,
    destino       TEXT NOT NULL,
    fecha_salida  TEXT NOT NULL,          -- fecha del vuelo (YYYY-MM-DD)
    precio        REAL NOT NULL,
    moneda        TEXT NOT NULL,
    aerolinea     TEXT,
    escalas       INTEGER,
    link          TEXT,
    consultado_en TEXT NOT NULL           -- momento de la consulta (ISO 8601)
);
CREATE INDEX IF NOT EXISTS idx_ruta ON precios (origen, destino, fecha_salida);
"""


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def guardar_precio(vuelo: dict):
    """Guarda una consulta de precio en el histórico."""
    with conectar() as con:
        con.execute(
            """INSERT INTO precios
               (origen, destino, fecha_salida, precio, moneda, aerolinea,
                escalas, link, consultado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                vuelo["origen"], vuelo["destino"], vuelo["fecha_salida"],
                vuelo["precio"], vuelo["moneda"], vuelo.get("aerolinea"),
                vuelo.get("escalas"), vuelo.get("link"),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )


def historial(origen: str, destino: str, fecha_salida: str | None = None):
    """Devuelve el histórico de precios de una ruta, ordenado por consulta."""
    sql = "SELECT * FROM precios WHERE origen = ? AND destino = ?"
    params = [origen.upper(), destino.upper()]
    if fecha_salida:
        sql += " AND fecha_salida = ?"
        params.append(fecha_salida)
    sql += " ORDER BY consultado_en"
    with conectar() as con:
        return [dict(f) for f in con.execute(sql, params)]


def ultimo_precio(origen: str, destino: str, fecha_salida: str):
    """Último precio registrado antes de la consulta actual (para comparar)."""
    filas = historial(origen, destino, fecha_salida)
    return filas[-1] if filas else None
