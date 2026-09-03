from bbo_bot.mempool import _miles


def test_formato_espanol():
    assert _miles(965386) == "965.386"
    assert _miles(70160) == "70.160"


def test_no_toca_el_resto_de_la_frase():
    frase = f"faltan {_miles(84614)} bloques, unos 588 días."
    assert "bloques, unos" in frase
