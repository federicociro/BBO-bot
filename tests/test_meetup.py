from datetime import datetime
from pathlib import Path

from bbo_bot.meetup import TZ, _parse_ical

ICS = (Path(__file__).parent / "fixtures" / "meetup.ics").read_text(encoding="utf-8")


def test_parsea_fecha_hora_y_link():
    ev = _parse_ical(ICS)
    assert len(ev) >= 2
    e = min(ev, key=lambda x: x.inicio)
    assert e.inicio == datetime(2026, 9, 23, 18, 0, tzinfo=TZ)
    assert "SeedSigner" in e.titulo
    assert e.url.startswith("https://www.meetup.com/bitcoin-barcelona/events/")


def test_texto_humano_en_castellano():
    e = min(_parse_ical(ICS), key=lambda x: x.inicio)
    assert "miércoles 23 de septiembre" in e.humano()
