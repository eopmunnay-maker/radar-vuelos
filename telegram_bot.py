"""Alertas por Telegram usando la Bot API oficial.

Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en el .env.
Sin credenciales, los mensajes se imprimen en consola (modo demo).
"""
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API = "https://api.telegram.org/bot{token}/{metodo}"


def _configurado() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def enviar_mensaje(texto: str) -> bool:
    """Envía un mensaje de texto al chat configurado."""
    if not _configurado():
        print("\n[TELEGRAM demo] " + texto + "\n")
        return False
    resp = requests.post(
        API.format(token=TELEGRAM_BOT_TOKEN, metodo="sendMessage"),
        json={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=30,
    )
    resp.raise_for_status()
    return True


def obtener_mensajes(offset: int, espera: int = 25) -> list[dict]:
    """Long polling de getUpdates: devuelve los mensajes nuevos del chat
    configurado como [{update_id, texto}]."""
    if not TELEGRAM_BOT_TOKEN:
        return []
    resp = requests.get(
        API.format(token=TELEGRAM_BOT_TOKEN, metodo="getUpdates"),
        params={"offset": offset, "timeout": espera},
        timeout=espera + 10,
    )
    resp.raise_for_status()
    mensajes = []
    for upd in resp.json().get("result", []):
        msj = upd.get("message") or {}
        chat = str((msj.get("chat") or {}).get("id", ""))
        texto = msj.get("text")
        if chat == TELEGRAM_CHAT_ID and isinstance(texto, str):
            mensajes.append({"update_id": upd["update_id"], "texto": texto})
        else:
            mensajes.append({"update_id": upd["update_id"], "texto": None})
    return mensajes


def enviar_foto(ruta_imagen: str, caption: str = "") -> bool:
    """Envía una imagen (p. ej. el gráfico de evolución de precios)."""
    if not _configurado():
        print(f"\n[TELEGRAM demo] foto: {ruta_imagen} — {caption}\n")
        return False
    with open(ruta_imagen, "rb") as f:
        resp = requests.post(
            API.format(token=TELEGRAM_BOT_TOKEN, metodo="sendPhoto"),
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": f},
            timeout=60,
        )
    resp.raise_for_status()
    return True
