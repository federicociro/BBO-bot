"""Guiños esporádicos a Rose bot.

Dos bots hablándose es la receta clásica de un bucle infinito, así que esto es
deliberadamente tonto y está atado corto:

- Frases enlatadas, **nunca** una llamada al modelo. Coste cero, y el texto que
  publica Rose (que lo escribe cualquiera con un trigger) no llega al prompt.
- Como mucho uno cada `INTERVALO_MIN`, y encima con probabilidad: la gracia se
  gasta rápido.
- Jamás se responde a una respuesta nuestra. Un guiño y se acabó.
"""

from __future__ import annotations

import random
import time

USERNAMES = {"MissRose_bot", "Rose", "MissRose"}
INTERVALO_MIN = 60 * 60 * 30  # 30 h: como mucho uno cada día y pico
PROBABILIDAD = 0.15

GUINOS = [
    "Rose poniendo orden, como siempre. Alguien tiene que hacerlo.",
    "Las reglas las sirve Rose, el contexto lo pongo yo. División de poderes.",
    "Rose modera, yo explico. Ninguno de los dos custodia tus llaves.",
    "Dos bots en un grupo cypherpunk. Verificad el código de ambos.",
    "Rose es más rápida que yo, pero yo leí el manifiesto entero.",
]

_ultimo = 0.0


def es_rose(username: str | None) -> bool:
    return bool(username) and username in USERNAMES


def guino(activo: bool = True) -> str | None:
    """Devuelve una frase, o None (que es lo normal)."""
    global _ultimo
    if not activo:
        return None
    ahora = time.monotonic()
    if _ultimo and ahora - _ultimo < INTERVALO_MIN:
        return None
    if random.random() > PROBABILIDAD:
        return None
    _ultimo = ahora
    return random.choice(GUINOS)
