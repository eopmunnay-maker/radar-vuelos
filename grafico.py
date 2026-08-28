"""Visualización de la evolución de precios con matplotlib."""
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # sin ventana: solo genera el archivo
import matplotlib.pyplot as plt

import db


def generar_grafico(origen: str, destino: str, fecha_salida: str | None = None,
                    salida: str = "evolucion.png") -> str | None:
    """Genera un PNG con la evolución del precio mínimo por consulta."""
    filas = db.historial(origen, destino, fecha_salida)
    if not filas:
        return None

    # precio mínimo registrado en cada momento de consulta
    por_consulta: dict[str, float] = {}
    for f in filas:
        t = f["consultado_en"]
        por_consulta[t] = min(por_consulta.get(t, float("inf")), f["precio"])

    tiempos = [datetime.fromisoformat(t) for t in por_consulta]
    precios = list(por_consulta.values())
    moneda = filas[-1]["moneda"]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(tiempos, precios, marker="o", linewidth=2, color="#1a73e8")
    ax.fill_between(tiempos, precios, min(precios) * 0.95, alpha=0.12, color="#1a73e8")

    minimo = min(precios)
    idx = precios.index(minimo)
    ax.annotate(f"Mínimo: {minimo:.0f} {moneda}", (tiempos[idx], minimo),
                textcoords="offset points", xytext=(0, -18),
                ha="center", fontweight="bold", color="#188038")

    titulo = f"Evolución de precios {origen.upper()} → {destino.upper()}"
    if fecha_salida:
        titulo += f"  (vuelo del {fecha_salida})"
    ax.set_title(titulo, fontsize=13, fontweight="bold")
    ax.set_xlabel("Momento de la consulta")
    ax.set_ylabel(f"Precio mínimo ({moneda})")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(salida, dpi=120)
    plt.close(fig)
    return salida
