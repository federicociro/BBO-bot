"""Punto de entrada: `python -m bbo_bot`."""

import logging
import os
import sys
from pathlib import Path


def _cargar_env() -> None:
    """.env sin dependencias: son ocho variables, no hace falta una librería."""
    env = Path(os.environ.get("BBO_ENV_FILE") or
               Path(__file__).resolve().parent.parent / ".env")
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, _, v = linea.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # httpx loguea cada request en INFO; con el polling de Telegram es ruido.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _cargar_env()

    from .bot import arrancar

    arrancar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
