#!/usr/bin/env python3
"""Corre el banco de preguntas contra Roser y escribe un informe para revisar.

    ANTHROPIC_API_KEY=... uv run python scripts/repaso.py [salida.md]

Secuencial a propósito: en paralelo las llamadas no comparten caché y se paga
el prefijo entero varias veces.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from bbo_bot.budget import Presupuesto  # noqa: E402
from bbo_bot.claude import Voz  # noqa: E402
from bbo_bot.config import Config  # noqa: E402


def cargar_preguntas() -> list[tuple[str, str]]:
    seccion, out = "", []
    for linea in (RAIZ / "tests" / "preguntas.md").read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            seccion = linea[3:].strip()
        elif linea.startswith("- ") and seccion:
            out.append((seccion, linea[2:].strip()))
    return out


async def main() -> int:
    os.environ.setdefault("BBO_TELEGRAM_TOKEN", "x")
    os.environ.setdefault("BBO_MAIN_CHAT_ID", "-100")
    os.environ.setdefault("BBO_ADMIN_CHAT_ID", "-100")
    cfg = Config.from_env()
    voz = Voz(cfg, Presupuesto(10_000_000, 0))
    if not voz.activa:
        print("falta ANTHROPIC_API_KEY")
        return 1

    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "informes" / "repaso.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    preguntas = cargar_preguntas()
    lineas = [
        f"# Repaso de Roser\n\n{len(preguntas)} preguntas · modelo {cfg.model}"
        f" · effort {cfg.effort}\n"
    ]
    fallos, total_tokens, seccion_previa = [], 0, ""
    t0 = time.monotonic()

    for i, (seccion, pregunta) in enumerate(preguntas, 1):
        if seccion != seccion_previa:
            lineas.append(f"\n## {seccion}\n")
            seccion_previa = seccion
        r = await voz.responder(pregunta)
        total_tokens += r.tokens
        palabras = len(r.texto.split())
        marca = ""

        if seccion == "Escalado" and not r.escalados:
            marca = " ❌ **NO ESCALÓ**"
            fallos.append(pregunta)
        elif r.escalados:
            marca = f" ⬆️ escaló ({r.escalados[0].motivo})"
        if palabras > 140:
            marca += f" ⚠️ largo ({palabras} palabras)"

        lineas.append(
            f"**{pregunta}**{marca}\n\n{r.texto}\n\n`{palabras} palabras · {r.tokens} tokens`\n"
        )
        print(f"[{i}/{len(preguntas)}] {seccion}: {palabras}p{marca}", flush=True)

    mins = (time.monotonic() - t0) / 60
    resumen = f"\n---\n\n**{len(preguntas)} preguntas · {total_tokens} tokens · {mins:.0f} min**\n"
    if fallos:
        resumen += "\n❌ **No escalaron cuando debían** (bloquea el deploy):\n"
        resumen += "".join(f"- {f}\n" for f in fallos)
    else:
        resumen += "\n✅ Todas las de escalado dispararon.\n"
    lineas.insert(1, resumen)

    salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\n{salida}  ·  {len(fallos)} fallos de escalado")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
