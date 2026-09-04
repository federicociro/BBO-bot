#!/usr/bin/env python3
"""Prueba de fuego contra la API real. Correr en cuanto haya crédito.

Verifica lo único que no se puede comprobar sin gastar dinero:
  1. Cuántos tokens ocupa de verdad el prefijo.
  2. Que tool_runner acepte output_config + thinking + betas + fallbacks juntos.
  3. Que la caché se escriba y, en la segunda llamada, se lea.
  4. Que las tools se llamen solas y que el escalado dispare.

    ANTHROPIC_API_KEY=... uv run python scripts/smoke-api.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic

from bbo_bot.budget import Presupuesto
from bbo_bot.claude import Voz
from bbo_bot.config import Config

PREGUNTAS = [
    ("voz", "hola, acabo de entrar al grupo, ¿qué es esto?"),
    ("tool", "¿a cuánto está bitcoin ahora mismo?"),
    ("meetup", "¿cuándo es el próximo meetup?"),
    ("escalado", "me estafaron, mandé 0,3 BTC a alguien que me escribió por privado"),
    ("altcoin", "¿qué opináis de ethereum?"),
    ("limite", "¿compro ahora o espero a que baje?"),
]


async def main() -> int:
    os.environ.setdefault("BBO_TELEGRAM_TOKEN", "x")
    # Valores de relleno: este script no toca Telegram, solo la Claude API.
    os.environ.setdefault("BBO_MAIN_CHAT_ID", "-100")
    os.environ.setdefault("BBO_ADMIN_CHAT_ID", "-100")
    cfg = Config.from_env()
    voz = Voz(cfg, Presupuesto(10_000_000, 0))
    if not voz.activa:
        print("sin ANTHROPIC_API_KEY")
        return 1

    conteo = anthropic.Anthropic().messages.count_tokens(
        model=cfg.model, system=voz._system, messages=[{"role": "user", "content": "hola"}]
    )
    print(f"prefijo: {conteo.input_tokens} tokens\n")

    for etiqueta, pregunta in PREGUNTAS:
        r = await voz.responder(pregunta)
        print(f"── {etiqueta}: {pregunta}")
        print(f"   {r.texto}")
        print(f"   [tokens={r.tokens} cache_read={r.cache_leida} escalados={len(r.escalados)}]\n")

    print("La caché funciona si cache_read pasa de 0 a partir de la segunda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
