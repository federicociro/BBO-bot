"""Cliente de la Claude API: caching del corpus, presupuesto y tool loop.

El tool runner del SDK de Python es SÍNCRONO, así que `responder()` lo ejecuta
en un hilo aparte para no bloquear el event loop de python-telegram-bot.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass

import anthropic

from .budget import Presupuesto
from .config import Config
from .corpus import cargar
from .persona import PERSONA
from .tools import Caja, Escalado, construir

log = logging.getLogger(__name__)

MAX_TOKENS = 700
BETAS = ["server-side-fallback-2026-07-01"]

# Prometer un humano sin avisarlo deja a alguien esperando ayuda que no viene.
# La instrucción en el prompt no basta: falla, y acá falla caro. Si el texto
# dice que hay un humano en camino, lo hay — aunque el modelo no llamara a la
# herramienta.
PROMESA_DE_HUMANO = re.compile(
    r"(lo (mira|miran|va a mirar|verá|ve)\s+(un|una|los|las)?\s*(humano|admin)"
    r"|ya (está|estás)? ?avisad|avis[éo] a (los|un) admin"
    r"|un admin (te|lo|se)|los admins (te|lo|se)"
    r"|te (escriben|escribirá|contactan|contactarán))",
    re.IGNORECASE,
)


@dataclass
class Respuesta:
    texto: str
    escalados: list
    tokens: int = 0
    cache_leida: int = 0


SIN_KEY = (
    "Estoy en modo QA sin modelo: los comandos funcionan, pero el Q&A no. Falta ANTHROPIC_API_KEY."
)


class Voz:
    def __init__(self, cfg: Config, presupuesto: Presupuesto) -> None:
        self.cfg = cfg
        self.presupuesto = presupuesto
        # El SDK no valida credenciales al construir el cliente, sino al hacer
        # el request: hay que mirar el entorno para saberlo al arrancar.
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            self.client = None
            log.warning("sin credenciales de Anthropic: el Q&A queda desactivado")
        else:
            self.client = anthropic.Anthropic()
        # El prefijo tiene que ser idéntico en cada request; solo cambia si
        # alguien recarga a propósito tras editar el canon.
        self._system: list = []
        self.recargar()

    def recargar(self) -> int:
        """Relee corpus, reglas y canon. Devuelve el tamaño del prefijo en chars.

        Invalida la caché del prompt a propósito: la siguiente pregunta paga la
        escritura y las de después vuelven a leer. Es el precio de editar en
        caliente, y es barato comparado con redesplegar.
        """
        cargar.cache_clear()
        material = cargar(self.cfg.corpus_dir, self.cfg.canon_path, self.cfg.reglas_path)
        self._system = [
            {"type": "text", "text": PERSONA},
            {
                "type": "text",
                "text": material,
                "cache_control": {"type": "ephemeral"},
            },
        ]
        return len(material)

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
                    caja.escalados,
                    tokens,
                    cache_leida,
                )
            texto = "".join(b.text for b in mensaje.content if b.type == "text") or texto

        texto = texto.strip()
        if PROMESA_DE_HUMANO.search(texto) and not caja.escalados:
            log.warning("prometió un humano sin escalar; se fuerza el escalado")
            caja.escalados.append(
                Escalado(
                    motivo="aviso forzado",
                    resumen=(
                        "Roser le dijo a la persona que un humano lo miraría, pero no "
                        "llamó a escalar. Se avisa igual por si acaso. Pregunta: " + pregunta[:300]
                    ),
                )
            )
        return Respuesta(texto, caja.escalados, tokens, cache_leida)

    @property
    def activa(self) -> bool:
        return self.client is not None

    async def responder(self, pregunta: str) -> Respuesta:
        if self.client is None:
            return Respuesta(SIN_KEY, [])
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
