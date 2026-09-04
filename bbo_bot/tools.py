"""Las herramientas del bot. Todas read-only salvo `escalar`, que solo avisa.

Ojo con la caché: las tools renderizan en posición 0 del prompt, antes del
system. El esquema sale de la firma y del docstring, así que mientras estos no
cambien el prefijo es byte a byte idéntico y la caché aguanta. Por eso la
fábrica de abajo es segura aunque devuelva funciones nuevas en cada request.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from anthropic import beta_tool

from . import meetup, mempool
from .config import Config


@dataclass
class Escalado:
    motivo: str
    resumen: str


@dataclass
class Caja:
    """Lo que las tools quieren contarle al bot cuando termina el turno."""

    escalados: list[Escalado] = field(default_factory=list)


def construir(cfg: Config, caja: Caja) -> list:
    """Devuelve la lista de tools, siempre en el mismo orden."""

    @beta_tool
    def precio_btc() -> str:
        """Precio actual de Bitcoin según el nodo de la comunidad."""
        try:
            return mempool.precio(cfg.mempool_url, cfg.fiat)
        except mempool.MempoolError:
            return "No se pudo consultar el precio ahora mismo."

    @beta_tool
    def fees_mempool() -> str:
        """Fees recomendadas ahora mismo, en sat/vB, según el nodo de la comunidad."""
        try:
            return mempool.fees(cfg.mempool_url)
        except mempool.MempoolError:
            return "No se pudieron consultar las fees ahora mismo."

    @beta_tool
    def altura_bloque() -> str:
        """Altura del último bloque y cuánto falta para el próximo halving."""
        try:
            return f"{mempool.bloque(cfg.mempool_url)}. {mempool.halving(cfg.mempool_url)}"
        except mempool.MempoolError:
            return "No se pudo consultar la altura de bloque ahora mismo."

    @beta_tool
    def proximo_meetup() -> str:
        """Próximo meetup de BBO: título, fecha, hora y enlace."""
        try:
            ev = meetup.proximo(cfg.meetup_group)
        except Exception:
            return "No se pudo consultar la agenda de meetups ahora mismo."
        if ev is None:
            return "No hay ningún meetup publicado todavía."
        return ev.humano()

    @beta_tool
    def escalar(motivo: str, resumen: str) -> str:
        """Pasa el tema a los admins humanos de BBO.

        Úsala sin excepción ante seeds o claves privadas pegadas en el chat,
        robos y estafas, preguntas fiscales o legales, dinero de una persona
        concreta, decisiones internas de la comunidad, moderación, o cuando
        alguien insiste después de que dijeras que no sabés.

        Args:
            motivo: Categoría corta, p. ej. "seed expuesta" o "consulta fiscal".
            resumen: Qué pasó, en una o dos frases. Nunca copies aquí una seed,
                una clave privada ni datos personales.
        """
        caja.escalados.append(Escalado(motivo=motivo, resumen=resumen))
        return "Escalado a los admins. Decile a la persona que esto lo mira un humano."

    return [precio_btc, fees_mempool, altura_bloque, proximo_meetup, escalar]
