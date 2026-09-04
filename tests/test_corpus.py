from pathlib import Path

from bbo_bot.corpus import cargar

RAIZ = Path(__file__).resolve().parent.parent


def _cargar():
    cargar.cache_clear()
    return cargar(
        RAIZ / "content" / "corpus", RAIZ / "content" / "canon.md", RAIZ / "content" / "reglas.md"
    )


def test_lleva_corpus_reglas_y_canon():
    t = _cargar()
    assert "Un espectro está surgiendo" in t
    assert "A specter is haunting" in t
    assert "REGLAS DEL GRUPO" in t and "bajo tu propia responsabilidad" in t
    assert "CANON" in t and "La pregunta número 500" not in t


def test_el_prefijo_es_estable():
    """Si esto falla, la caché no sirve: el prefijo cambia entre requests."""
    assert _cargar() == _cargar()


def test_no_entra_el_pdf():
    t = _cargar()
    assert "Cleminson" not in t and "eugenic" not in t.lower()
