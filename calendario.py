"""Integración con Google Calendar.

Estrategia en dos niveles:
1. Siempre disponible: genera un enlace "Agregar a Google Calendar"
   (action=TEMPLATE) — no requiere credenciales ni OAuth.
2. Si hay credenciales de Google (credentials.json + google-api-python-client
   instalado), crea el evento directamente vía API.
"""
from datetime import datetime, timedelta
from urllib.parse import urlencode

from config import BASE_DIR

URL_TEMPLATE = "https://calendar.google.com/calendar/render"


def enlace_evento(origen: str, destino: str, fecha: str, precio: float,
                  moneda: str, aerolinea: str | None = None) -> str:
    """Enlace para proponer el evento del viaje en Google Calendar."""
    inicio = datetime.strptime(fecha, "%Y-%m-%d")
    fin = inicio + timedelta(days=1)
    detalles = (
        f"Vuelo {origen} → {destino}\n"
        f"Precio encontrado: {precio:.2f} {moneda}\n"
        + (f"Aerolínea: {aerolinea}\n" if aerolinea else "")
        + "Propuesto por Radar de Vuelos ✈️"
    )
    params = {
        "action": "TEMPLATE",
        "text": f"✈️ Viaje {origen} → {destino}",
        "dates": f"{inicio:%Y%m%d}/{fin:%Y%m%d}",   # evento de día completo
        "details": detalles,
        "location": destino,
    }
    return f"{URL_TEMPLATE}?{urlencode(params)}"


def crear_evento_api(origen: str, destino: str, fecha: str, precio: float,
                     moneda: str) -> str | None:
    """Crea el evento vía Google Calendar API si hay credenciales.

    Requiere: pip install google-api-python-client google-auth-oauthlib
    y un credentials.json (OAuth de escritorio) en la carpeta del proyecto.
    Devuelve el link del evento creado, o None si no hay credenciales.
    """
    cred_file = BASE_DIR / "credentials.json"
    if not cred_file.exists():
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("Instala: pip install google-api-python-client google-auth-oauthlib")
        return None

    scopes = ["https://www.googleapis.com/auth/calendar.events"]
    token_file = BASE_DIR / "token.json"
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), scopes)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())

    servicio = build("calendar", "v3", credentials=creds)
    evento = {
        "summary": f"✈️ Viaje {origen} → {destino}",
        "location": destino,
        "description": f"Precio encontrado: {precio:.2f} {moneda}\nPropuesto por Radar de Vuelos",
        "start": {"date": fecha},
        "end": {"date": (datetime.strptime(fecha, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")},
        "reminders": {"useDefault": True},
    }
    creado = servicio.events().insert(calendarId="primary", body=evento).execute()
    return creado.get("htmlLink")
