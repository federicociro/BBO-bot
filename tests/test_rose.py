import bbo_bot.rose as rose


def test_reconoce_a_rose():
    assert rose.es_rose("MissRose_bot")
    assert not rose.es_rose("cualquier_otro_bot")
    assert not rose.es_rose(None)


def test_se_puede_apagar():
    assert rose.guino(activo=False) is None


def test_no_responde_dos_veces_seguidas(monkeypatch):
    """Dos bots hablándose es un bucle: como mucho uno por ventana."""
    rose._ultimo = 0.0
    monkeypatch.setattr(rose.random, "random", lambda: 0.0)  # siempre pasa el dado
    assert rose.guino() is not None
    assert rose.guino() is None


def test_alertas_tienen_freno():
    """Un bot que spamea cuando algo se rompe se silencia, y deja de servir."""
    import bbo_bot.alertas as alertas

    alertas._ultima.clear()
    assert alertas._pasa_el_freno("x")
    assert not alertas._pasa_el_freno("x")
    assert alertas._pasa_el_freno("otra-clave")
