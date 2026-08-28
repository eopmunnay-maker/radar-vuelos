#!/usr/bin/env python3
"""Siembra histórico demo de varios días para la demostración.

Uso: python demo_semilla.py LIM CUZ 2026-09-15 [dias]
Genera consultas simuladas (2 por día) hacia atrás, con una tendencia
de bajada al final, para que el gráfico y las alertas se aprecien.
"""
import hashlib
import random
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

from config import DB_PATH
import db


def sembrar(origen: str, destino: str, fecha_vuelo: str, dias: int = 14):
    random.seed(f"{origen}{destino}{fecha_vuelo}")
    # mismo precio base que el generador demo de travelpayouts.py,
    # para que el histórico sembrado empalme con las consultas en vivo
    semilla = hashlib.md5(f"{origen.upper()}{destino.upper()}{fecha_vuelo}".encode()).hexdigest()
    base = 150 + int(semilla[:6], 16) % 400
    ahora = datetime.now(timezone.utc)
    con = sqlite3.connect(DB_PATH)
    db.conectar().close()  # asegura el esquema
    n = 0
    for d in range(dias, 0, -1):
        for hora in (9, 18):
            t = (ahora - timedelta(days=d)).replace(hour=hora, minute=0, second=0)
            # tendencia: sube a mitad de periodo y baja fuerte al final
            factor = 1 + 0.25 * (1 - abs(d - dias / 2) / (dias / 2)) - (0.30 if d <= 2 else 0)
            precio = round(base * factor + random.uniform(-15, 15), 0)
            con.execute(
                """INSERT INTO precios (origen, destino, fecha_salida, precio, moneda,
                   aerolinea, escalas, link, consultado_en)
                   VALUES (?, ?, ?, ?, 'USD', ?, ?, NULL, ?)""",
                (origen.upper(), destino.upper(), fecha_vuelo, max(precio, 80),
                 random.choice(["LA", "H2", "JA", "AV"]), random.randint(0, 2),
                 t.isoformat(timespec="seconds")),
            )
            n += 1
    con.commit()
    con.close()
    print(f"✅ Sembradas {n} consultas demo de {origen.upper()} → {destino.upper()} "
          f"({dias} días de histórico)")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    sembrar(sys.argv[1], sys.argv[2], sys.argv[3],
            int(sys.argv[4]) if len(sys.argv) > 4 else 14)
