#!/usr/bin/env python3
"""Radar de Vuelos ✈️ — agente de precios de vuelos.

Comandos:
  buscar   ORIGEN DESTINO FECHA     Consulta precios y los guarda en SQLite
  historial ORIGEN DESTINO          Muestra el histórico de la ruta
  grafico  ORIGEN DESTINO           Genera el gráfico de evolución de precios
  vigilar  ORIGEN DESTINO FECHA     Monitorea la ruta y alerta por Telegram
  viajar   ORIGEN DESTINO FECHA     Propone el evento del viaje en Google Calendar

Ejemplos:
  python radar.py buscar LIM CUZ 2026-09-15
  python radar.py vigilar LIM MIA 2026-10-01 --umbral 350 --intervalo 3600
  python radar.py viajar LIM CUZ 2026-09-15
"""
import argparse
import sys
import time

import calendario
import db
import grafico
import telegram_bot
import travelpayouts
from config import MODO_DEMO


def _aviso_demo():
    if MODO_DEMO:
        print("⚠️  MODO DEMO: sin TRAVELPAYOUTS_TOKEN, usando precios simulados.\n")


def _tabla_vuelos(vuelos: list[dict]):
    print(f"{'#':<3}{'Precio':>10}  {'Aerolínea':<10}{'Escalas':<9}Fecha")
    for i, v in enumerate(vuelos, 1):
        print(f"{i:<3}{v['precio']:>7.0f} {v['moneda']}  "
              f"{v['aerolinea'] or '—':<10}{v['escalas'] if v['escalas'] is not None else '—':<9}"
              f"{v['fecha_salida']}")


def cmd_buscar(args) -> list[dict]:
    _aviso_demo()
    print(f"🔎 Buscando {args.origen.upper()} → {args.destino.upper()} para {args.fecha}...")
    vuelos = travelpayouts.buscar_vuelos(args.origen, args.destino, args.fecha)
    if not vuelos:
        print("No se encontraron vuelos para esa ruta/fecha.")
        return []
    for v in vuelos:
        db.guardar_precio(v)
    _tabla_vuelos(vuelos)
    mejor = vuelos[0]
    print(f"\n💰 Mejor precio: {mejor['precio']:.0f} {mejor['moneda']} "
          f"({mejor['aerolinea']}, {mejor['escalas']} escalas)")
    if mejor.get("link"):
        print(f"🔗 {mejor['link']}")
    print(f"✅ {len(vuelos)} precios guardados en el histórico (radar.db)")
    return vuelos


def cmd_historial(args):
    filas = db.historial(args.origen, args.destino, getattr(args, "fecha", None))
    if not filas:
        print("Sin registros para esa ruta. Ejecuta primero: python radar.py buscar ...")
        return
    print(f"📒 Histórico {args.origen.upper()} → {args.destino.upper()} "
          f"({len(filas)} registros)\n")
    print(f"{'Consultado':<21}{'Vuelo del':<12}{'Precio':>10}  Aerolínea")
    for f in filas:
        print(f"{f['consultado_en'][:19]:<21}{f['fecha_salida']:<12}"
              f"{f['precio']:>7.0f} {f['moneda']}  {f['aerolinea'] or '—'}")
    precios = [f["precio"] for f in filas]
    print(f"\nMín: {min(precios):.0f} | Máx: {max(precios):.0f} | "
          f"Promedio: {sum(precios)/len(precios):.0f} {filas[-1]['moneda']}")


def cmd_grafico(args):
    salida = grafico.generar_grafico(args.origen.upper(), args.destino.upper(),
                                     getattr(args, "fecha", None), args.out)
    if not salida:
        print("Sin datos para graficar. Ejecuta primero: python radar.py buscar ...")
        return
    print(f"📈 Gráfico generado: {salida}")
    if args.telegram:
        telegram_bot.enviar_foto(salida,
                                 f"Evolución {args.origen.upper()} → {args.destino.upper()}")
        print("📤 Enviado por Telegram")


def cmd_vigilar(args):
    """Bucle de monitoreo: consulta, guarda y alerta si conviene comprar."""
    _aviso_demo()
    origen, destino = args.origen.upper(), args.destino.upper()
    print(f"👁️  Vigilando {origen} → {destino} ({args.fecha}) | "
          f"umbral: {args.umbral} | cada {args.intervalo}s | Ctrl+C para salir\n")
    iteracion = 0
    while True:
        iteracion += 1
        anterior = db.ultimo_precio(origen, destino, args.fecha)
        vuelos = travelpayouts.buscar_vuelos(origen, destino, args.fecha, limite=3)
        if vuelos:
            mejor = vuelos[0]
            for v in vuelos:
                db.guardar_precio(v)
            print(f"[{time.strftime('%H:%M:%S')}] consulta #{iteracion}: "
                  f"{mejor['precio']:.0f} {mejor['moneda']}")

            alertas = []
            if args.umbral and mejor["precio"] <= args.umbral:
                alertas.append(f"precio ({mejor['precio']:.0f}) ≤ umbral ({args.umbral:.0f})")
            if anterior and mejor["precio"] < anterior["precio"] * 0.95:
                baja = 100 * (1 - mejor["precio"] / anterior["precio"])
                alertas.append(f"bajó {baja:.1f}% desde la última consulta")

            if alertas:
                texto = (f"🚨 <b>¡Alerta de precio!</b> ✈️\n"
                         f"{origen} → {destino} el {args.fecha}\n"
                         f"💰 <b>{mejor['precio']:.0f} {mejor['moneda']}</b> "
                         f"({mejor['aerolinea']}, {mejor['escalas']} escalas)\n"
                         f"📌 Motivo: {' y '.join(alertas)}\n"
                         + (f"🔗 {mejor['link']}" if mejor.get("link") else ""))
                telegram_bot.enviar_mensaje(texto)
                print(f"   🚨 ALERTA enviada: {' y '.join(alertas)}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] sin resultados")

        if args.una_vez:
            break
        try:
            time.sleep(args.intervalo)
        except KeyboardInterrupt:
            print("\n👋 Vigilancia detenida.")
            break


def cmd_panel(args):
    """Panel web local: visualización del histórico y evolución de precios."""
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs
    from pathlib import Path

    panel_path = Path(__file__).resolve().parent / "panel.html"

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _responder(self, cuerpo: bytes, tipo: str):
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/api/historial":
                q = parse_qs(url.query)
                filas = db.historial(q.get("origen", ["LIM"])[0],
                                     q.get("destino", ["CUZ"])[0])
                moneda = filas[-1]["moneda"] if filas else "USD"
                cuerpo = json.dumps({"historial": filas, "moneda": moneda}).encode()
                self._responder(cuerpo, "application/json; charset=utf-8")
            elif url.path in ("/", "/panel.html"):
                self._responder(panel_path.read_bytes(), "text/html; charset=utf-8")
            else:
                self.send_response(404)
                self.end_headers()

    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador)
    print(f"📊 Panel disponible en http://127.0.0.1:{args.puerto}  (Ctrl+C para detener)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Panel detenido.")
    finally:
        servidor.server_close()


# --- Bot conversacional -------------------------------------------------
CIUDADES = {
    "lima": "LIM", "cusco": "CUZ", "cuzco": "CUZ", "arequipa": "AQP",
    "trujillo": "TRU", "piura": "PIU", "iquitos": "IQT", "tarapoto": "TPP",
    "cajamarca": "CJA", "caj": "CJA", "chiclayo": "CIX", "juliaca": "JUL",
    "puerto maldonado": "PEM", "pucallpa": "PCL", "jauja": "JAU",
    "jamaica": "KIN", "kingston": "KIN", "montego": "MBJ",
    "miami": "MIA", "orlando": "MCO", "nueva york": "JFK", "new york": "JFK",
    "cancun": "CUN", "mexico": "MEX", "bogota": "BOG", "medellin": "MDE",
    "quito": "UIO", "guayaquil": "GYE", "santiago": "SCL",
    "buenos aires": "EZE", "sao paulo": "GRU", "rio": "GIG",
    "panama": "PTY", "habana": "HAV", "punta cana": "PUJ",
    "madrid": "MAD", "barcelona": "BCN", "paris": "CDG", "roma": "FCO",
    "los angeles": "LAX",
}


# nombre legible por código IATA (para las respuestas del bot);
# se omiten los alias cortos tipo "caj"
NOMBRES_IATA = {iata: nombre.title() for nombre, iata in CIUDADES.items()
                if len(nombre) > 3}


def _con_nombre(iata: str) -> str:
    nombre = NOMBRES_IATA.get(iata)
    return f"{iata} ({nombre})" if nombre else iata


def _sin_tildes(texto: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def interpretar_consulta(texto: str) -> dict | None:
    """Extrae origen, destino y fecha de una pregunta en lenguaje natural.

    Entiende códigos IATA (LIM, CUZ...) y ciudades comunes. Si solo hay
    un destino ("búscame un vuelo a jamaica"), asume origen LIM.
    """
    import re
    limpio = _sin_tildes(texto.lower())

    fecha = None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", limpio)
    if m:
        fecha = m.group(1)
    else:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", limpio)
        if m:
            fecha = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"

    lugares = []
    # patrón "de X a Y" con ciudades o códigos
    for nombre, iata in CIUDADES.items():
        pos = limpio.find(nombre)
        if pos >= 0:
            lugares.append((pos, iata))
    for m in re.finditer(r"\b([A-Z]{3})\b", texto):
        codigo = m.group(1)
        if codigo not in {"USD", "PEN", "EUR"}:
            lugares.append((m.start(), codigo))
    lugares.sort(key=lambda x: x[0])
    codigos = []
    ultima_pos = -1
    for pos, iata in lugares:
        # si una ciudad conocida y un código IATA coinciden en la misma
        # posición (ej. "CAJ" ↔ cajamarca→CJA), gana la ciudad conocida
        if pos == ultima_pos or iata in codigos:
            continue
        codigos.append(iata)
        ultima_pos = pos

    if not codigos:
        return None
    if len(codigos) == 1:
        origen, destino = "LIM", codigos[0]
        if destino == "LIM":
            return None
    else:
        origen, destino = codigos[0], codigos[1]
    return {"origen": origen, "destino": destino, "fecha": fecha}


def responder_consulta(consulta: dict) -> str:
    """Busca vuelos para la consulta interpretada y arma la respuesta."""
    vuelos = travelpayouts.buscar_vuelos(consulta["origen"], consulta["destino"],
                                         consulta["fecha"], limite=3)
    if not vuelos:
        cuando = f" para {consulta['fecha']}" if consulta["fecha"] else ""
        return (f"😕 No encontré precios de {consulta['origen']} → "
                f"{consulta['destino']}{cuando} en este momento. "
                "Prueba otra fecha o ruta.")
    for v in vuelos:
        db.guardar_precio(v)
    mejor = vuelos[0]
    lineas = [f"✈️ <b>{_con_nombre(consulta['origen'])} → "
              f"{_con_nombre(consulta['destino'])}</b>"]
    for v in vuelos:
        lineas.append(f"• {v['fecha_salida']}: <b>{v['precio']:.0f} {v['moneda']}</b> "
                      f"({v['aerolinea']}, {v['escalas']} escalas)")
    if mejor.get("link"):
        lineas.append(f"🔗 <a href=\"{mejor['link']}\">Ver el más barato</a>")
    enlace = calendario.enlace_evento(mejor["origen"], mejor["destino"],
                                      mejor["fecha_salida"], mejor["precio"],
                                      mejor["moneda"], mejor["aerolinea"])
    lineas.append(f"🗓️ ¿Decidido a viajar? <a href=\"{enlace}\">Agregar a Google Calendar</a>")
    return "\n".join(lineas)


def cmd_escuchar(args):
    """Bot conversacional: responde preguntas de vuelos por Telegram."""
    _aviso_demo()
    print("🤖 Bot escuchando en Telegram. Pregúntale, por ejemplo:")
    print('   "búscame un vuelo a jamaica"')
    print('   "vuelo de LIM a CUZ el 2026-09-15"')
    print("   Ctrl+C para detener\n")
    offset = 0
    while True:
        try:
            mensajes = telegram_bot.obtener_mensajes(offset)
        except KeyboardInterrupt:
            print("\n👋 Bot detenido.")
            return
        except Exception as e:
            print(f"(reintentando: {e})")
            time.sleep(3)
            continue
        for m in mensajes:
            offset = m["update_id"] + 1
            if not m["texto"]:
                continue
            print(f"[{time.strftime('%H:%M:%S')}] pregunta: {m['texto']}")
            consulta = interpretar_consulta(m["texto"])
            if not consulta:
                telegram_bot.enviar_mensaje(
                    "🤖 No entendí la ruta. Pregúntame así:\n"
                    "• búscame un vuelo a jamaica\n"
                    "• vuelo de Lima a Cusco el 2026-09-15\n"
                    "• vuelo de LIM a MIA")
                continue
            try:
                respuesta = responder_consulta(consulta)
            except Exception:
                respuesta = (f"😕 No pude consultar {consulta['origen']} → "
                             f"{consulta['destino']} (¿la ruta o el código existe?). "
                             "Intenta con otra ciudad o código IATA.")
            try:
                telegram_bot.enviar_mensaje(respuesta)
                print(f"   → respondido: {consulta['origen']} → {consulta['destino']}")
            except Exception as e:
                print(f"   (no se pudo responder: {e})")


def cmd_viajar(args):
    """El usuario decidió viajar: propone el evento en Google Calendar."""
    origen, destino = args.origen.upper(), args.destino.upper()
    ultimo = db.ultimo_precio(origen, destino, args.fecha)
    if ultimo:
        precio, moneda, aerolinea = ultimo["precio"], ultimo["moneda"], ultimo["aerolinea"]
    else:
        _aviso_demo()
        vuelos = travelpayouts.buscar_vuelos(origen, destino, args.fecha, limite=1)
        if not vuelos:
            print("No hay datos de esa ruta.")
            return
        db.guardar_precio(vuelos[0])
        precio, moneda, aerolinea = vuelos[0]["precio"], vuelos[0]["moneda"], vuelos[0]["aerolinea"]

    print(f"🗓️  Proponiendo evento: viaje {origen} → {destino} el {args.fecha} "
          f"({precio:.0f} {moneda})\n")

    link_api = calendario.crear_evento_api(origen, destino, args.fecha, precio, moneda)
    if link_api:
        print(f"✅ Evento creado en tu Google Calendar:\n{link_api}")
        telegram_bot.enviar_mensaje(f"🗓️ Evento creado en Google Calendar:\n{link_api}")
        return

    enlace = calendario.enlace_evento(origen, destino, args.fecha, precio, moneda, aerolinea)
    print("Abre este enlace para confirmar el evento en Google Calendar:")
    print(enlace)
    telegram_bot.enviar_mensaje(
        f"🗓️ <b>Propuesta de viaje</b> {origen} → {destino} el {args.fecha}\n"
        f"💰 {precio:.0f} {moneda}\n"
        f"Agrégalo a tu calendario:\n{enlace}")


def main():
    parser = argparse.ArgumentParser(description="Radar de Vuelos ✈️",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("Comandos:")[1])
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("buscar", help="Consulta precios y guarda histórico")
    p.add_argument("origen"); p.add_argument("destino"); p.add_argument("fecha")
    p.set_defaults(func=cmd_buscar)

    p = sub.add_parser("historial", help="Muestra el histórico de una ruta")
    p.add_argument("origen"); p.add_argument("destino")
    p.add_argument("--fecha", help="Filtrar por fecha del vuelo")
    p.set_defaults(func=cmd_historial)

    p = sub.add_parser("grafico", help="Gráfico de evolución de precios")
    p.add_argument("origen"); p.add_argument("destino")
    p.add_argument("--fecha", help="Filtrar por fecha del vuelo")
    p.add_argument("--out", default="evolucion.png")
    p.add_argument("--telegram", action="store_true", help="Enviar el gráfico por Telegram")
    p.set_defaults(func=cmd_grafico)

    p = sub.add_parser("vigilar", help="Monitorea la ruta y alerta por Telegram")
    p.add_argument("origen"); p.add_argument("destino"); p.add_argument("fecha")
    p.add_argument("--umbral", type=float, default=None,
                   help="Alerta si el precio baja de este valor")
    p.add_argument("--intervalo", type=int, default=3600,
                   help="Segundos entre consultas (default: 3600)")
    p.add_argument("--una-vez", action="store_true",
                   help="Una sola consulta (útil para cron/launchd)")
    p.set_defaults(func=cmd_vigilar)

    p = sub.add_parser("panel", help="Panel web con la evolución de precios")
    p.add_argument("--puerto", type=int, default=4700)
    p.set_defaults(func=cmd_panel)

    p = sub.add_parser("escuchar", help="Bot conversacional: responde preguntas por Telegram")
    p.set_defaults(func=cmd_escuchar)

    p = sub.add_parser("viajar", help="Propone el evento del viaje en Google Calendar")
    p.add_argument("origen"); p.add_argument("destino"); p.add_argument("fecha")
    p.set_defaults(func=cmd_viajar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
