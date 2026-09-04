"""Próximos meetups desde los feeds públicos de Meetup.com.

iCal da la fecha/hora estructurada (DTSTART con TZID) pero no el lugar; el RSS
da la descripción completa. Por eso se leen los dos. Nada de GraphQL: es un
calendario público, meterle OAuth2 y rotación de tokens no compra nada.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

TZ = ZoneInfo("Europe/Madrid")
TIMEOUT = 10.0
TTL = timedelta(hours=1)

_cache: tuple[datetime, list[Evento]] | None = None


@dataclass(frozen=True)
class Evento:
    titulo: str
    inicio: datetime
    url: str
    descripcion: str = ""

    def humano(self) -> str:
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        d = self.inicio
        return (
            f"{self.titulo}\n"
            f"{dias[d.weekday()]} {d.day} de {meses[d.month - 1]}, {d:%H:%M}\n"
            f"{self.url}"
        )


def _parse_ical(texto: str) -> list[Evento]:
    eventos = []
    for bloque in texto.split("BEGIN:VEVENT")[1:]:
        bloque = bloque.split("END:VEVENT")[0]
        campos = {}
        for linea in bloque.replace("\r\n ", "").replace("\r\n", "\n").split("\n"):
            if ":" in linea:
                k, _, v = linea.partition(":")
                campos[k.split(";")[0]] = v.strip()
        dt = campos.get("DTSTART")
        if not dt:
            continue
        try:
            inicio = datetime.strptime(dt[:15], "%Y%m%dT%H%M%S").replace(tzinfo=TZ)
        except ValueError:
            continue
        eventos.append(
            Evento(
                titulo=campos.get("SUMMARY", "Meetup"),
                inicio=inicio,
                url=campos.get("URL", ""),
            )
        )
    return eventos


def _parse_rss(texto: str) -> dict[str, str]:
    """link -> descripción."""
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError:
        return {}
    out = {}
    for item in raiz.iter("item"):
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        if link:
            out[link] = re.sub(r"\n{3,}", "\n\n", desc)
    return out


def proximos(grupo: str, forzar: bool = False) -> list[Evento]:
    """Eventos futuros, ordenados. Cacheado 1 h en memoria. Bloqueante."""
    global _cache
    ahora = datetime.now(UTC)
    if not forzar and _cache and ahora - _cache[0] < TTL:
        return _cache[1]

    base = f"https://www.meetup.com/{grupo}/events"
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as c:
        ical = c.get(f"{base}/ical/")
        ical.raise_for_status()
        eventos = _parse_ical(ical.text)
        try:
            rss = c.get(f"{base}/rss")
            descripciones = _parse_rss(rss.text) if rss.status_code == 200 else {}
        except httpx.HTTPError:
            descripciones = {}

    eventos = [
        Evento(e.titulo, e.inicio, e.url, descripciones.get(e.url, ""))
        for e in eventos
        if e.inicio > datetime.now(TZ)
    ]
    eventos.sort(key=lambda e: e.inicio)
    _cache = (ahora, eventos)
    return eventos


def proximo(grupo: str) -> Evento | None:
    ev = proximos(grupo)
    return ev[0] if ev else None
