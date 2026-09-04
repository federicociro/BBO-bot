"""Avisos operativos al dueño del bot, por privado.

Distinto de un escalado. El escalado es de la comunidad y va al log de admins;
esto es "algo va mal con la bot" y va a una persona concreta:

    escalado  → alguien pegó una seed        → chat de admins
    alerta    → no pude avisar al chat       → privado del dueño

Con freno: una alerta de cada tipo por hora. Un bot que spamea cuando algo se
rompe se silencia, y entonces no sirve para nada.
"""

from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

VENTANA_S = 3600
_ultima: dict[str, float] = {}


def _pasa_el_freno(clave: str) -> bool:
    # El centinela es None, no 0.0: `monotonic()` cuenta desde el arranque de la
    # máquina, así que en un contenedor recién levantado `ahora - 0.0` es menor
    # que la ventana y se tragaba en silencio la primera alerta de cada tipo
    # durante la primera hora de vida. Justo cuando más falta hacen.
    ahora = time.monotonic()
    ultima = _ultima.get(clave)
    if ultima is not None and ahora - ultima < VENTANA_S:
        return False
    _ultima[clave] = ahora
    return True


async def avisar(ctx, owner_id: int, clave: str, texto: str, *, siempre: bool = False) -> None:
    """`clave` agrupa alertas del mismo tipo para el freno."""
    if not owner_id:
        return
    if not siempre and not _pasa_el_freno(clave):
        return
    try:
        await ctx.bot.send_message(owner_id, f"🤖 Roser · {texto}")
    except Exception:
        log.exception("no se pudo alertar al dueño: %s", texto)
