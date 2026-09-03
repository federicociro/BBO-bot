"""Datos del nodo propio. Solo agregados: nada de address ni xpub."""

from __future__ import annotations

import httpx

HALVING_CADA = 210_000
TIMEOUT = 8.0


def _miles(n: float, dec: int = 0) -> str:
    """Formato español: 965.386. Se formatea el número, nunca la frase entera."""
    return f"{n:,.{dec}f}".replace(",", ".")


class MempoolError(RuntimeError):
    pass


def _get(base: str, path: str):
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(f"{base}{path}")
            r.raise_for_status()
            return r.json() if "json" in r.headers.get("content-type", "") else r.text
    except Exception as e:  # noqa: BLE001 - el bot solo necesita saber que falló
        raise MempoolError(f"{path}: {e}") from e


def precio(base: str, fiat: str = "EUR") -> str:
    d = _get(base, "/v1/prices")
    if fiat not in d:
        raise MempoolError(f"no hay precio en {fiat}")
    return f"1 BTC = {_miles(d[fiat])} {fiat}"


def fees(base: str) -> str:
    d = _get(base, "/v1/fees/recommended")
    return (
        f"Fees ahora — rápida: {d['fastestFee']} sat/vB · "
        f"30 min: {d['halfHourFee']} · 1 h: {d['hourFee']} · "
        f"económica: {d['economyFee']}"
    )


def altura(base: str) -> int:
    return int(_get(base, "/blocks/tip/height"))


def bloque(base: str) -> str:
    return f"Altura actual: {_miles(altura(base))}"


def halving(base: str) -> str:
    h = altura(base)
    objetivo = ((h // HALVING_CADA) + 1) * HALVING_CADA
    faltan = objetivo - h
    dias = faltan * 10 / 60 / 24
    return (
        f"Próximo halving en el bloque {_miles(objetivo)}: "
        f"faltan {_miles(faltan)} bloques, unos {dias:.0f} días."
    )
