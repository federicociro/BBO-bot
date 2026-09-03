"""Cliente de la Claude API: caching del corpus, presupuesto y tool loop.

El tool runner del SDK de Python es SÍNCRONO, así que `responder()` lo ejecuta
en un hilo aparte para no bloquear el event loop de python-telegram-bot.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import anthropic

from .budget import Presupuesto
from .config import Config
from .corpus import cargar
from .persona import PERSONA
from .tools import Caja, construir

log = logging.getLogger(__name__)

MAX_TOKENS = 1024
BETAS = ["server-side-fallback-2026-07-01"]


@dataclass
class Respuesta:
    texto: str
    escalados: list
    tokens: int = 0
    cache_leida: int = 0


class Voz:
    def __init__(self, cfg: Config, presupuesto: Presupuesto) -> None:
        self.cfg = cfg
        self.presupuesto = presupuesto
        self.client = anthropic.Anthropic()
        # Se arma una vez: el prefijo tiene que ser idéntico en cada request.
        self._system = [
            {"type": "text", "text": PERSONA},
            {
                "type": "text",
                "text": cargar(cfg.corpus_dir, cfg.canon_path, cfg.reglas_path),
                "cache_control": {"type": "ephemeral"},
            },
        ]

    def _turno(self, pregunta: str, caja: Caja) -> Respuesta:
        runner = self.client.beta.messages.tool_runner(
            model=self.cfg.model,
            max_tokens=MAX_TOKENS,
            system=self._system,
            tools=construir(self.cfg, caja),
            messages=[{"role": "user", "content": pregunta}],
            output_config={"effort": self.cfg.effort},
            thinking={"type": "adaptive"},
            betas=BETAS,
            fallbacks="default",
        )

        texto, tokens, cache_leida = "", 0, 0
        for mensaje in runner:
            u = mensaje.usage
            tokens += (u.input_tokens or 0) + (u.output_tokens or 0)
            cache_leida += getattr(u, "cache_read_input_tokens", 0) or 0

            if mensaje.stop_reason == "refusal":
                log.warning("refusal: %s", getattr(mensaje, "stop_details", None))
                return Respuesta(
                    "Eso no lo puedo contestar. Si hace falta, lo ve un admin.",
                    caja.escalados, tokens, cache_leida,
                )
            texto = "".join(b.text for b in mensaje.content if b.type == "text") or texto

        return Respuesta(texto.strip(), caja.escalados, tokens, cache_leida)

    async def responder(self, pregunta: str) -> Respuesta:
        if not self.presupuesto.hay_saldo():
            return Respuesta(
                "Se agotó el presupuesto del día. Mañana sigo; "
                "mientras tanto los admins están por acá.",
                [],
            )

        caja = Caja()
        try:
            r = await asyncio.to_thread(self._turno, pregunta, caja)
        except anthropic.APIStatusError as e:
            log.error("API %s: %s", e.status_code, e.message)
            return Respuesta("Ahora mismo no puedo contestar. Probá en un rato.", [])
        except anthropic.APIConnectionError:
            log.error("sin conexión con la API")
            return Respuesta("Ahora mismo no puedo contestar. Probá en un rato.", [])

        self.presupuesto.apuntar(r.tokens)
        log.info("tokens=%s cache_read=%s", r.tokens, r.cache_leida)
        if not r.texto:
            return Respuesta("No sé qué contestar a eso.", r.escalados, r.tokens, r.cache_leida)
        return r
