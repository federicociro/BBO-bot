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
    # La primera siempre pasa, aunque la máquina acabe de arrancar y
    # monotonic() valga cuatro segundos.
    assert alertas._pasa_el_freno("x")
    assert not alertas._pasa_el_freno("x")
    assert alertas._pasa_el_freno("otra-clave")


def test_no_se_promete_un_humano_sin_avisarlo():
    """Peor que no escalar es decir que escalaste: la persona espera ayuda que
    nadie mandó. La regla del prompt fallaba, así que hay red en el código."""
    from bbo_bot.claude import PROMESA_DE_HUMANO as P

    for frase in [
        "Esto lo mira un humano de BBO.",
        "Ya avisé a los admins, te escriben ellos.",
        "Un admin te va a contactar.",
        "Esto lo va a mirar un admin humano para acompañarte.",
    ]:
        assert P.search(frase), frase

    for frase in [
        "Nadie de BBO te escribe primero por privado.",
        "En los meetups hacemos sesiones de introducción.",
        "Sparrow en ordenador, BlueWallet en el móvil.",
    ]:
        assert not P.search(frase), frase


def test_la_primera_alerta_pasa_en_maquina_recien_arrancada(monkeypatch):
    """monotonic() cuenta desde el arranque: con centinela 0.0, un contenedor
    nuevo se tragaba la primera alerta de cada tipo durante una hora."""
    import bbo_bot.alertas as alertas

    alertas._ultima.clear()
    monkeypatch.setattr(alertas.time, "monotonic", lambda: 4.0)
    assert alertas._pasa_el_freno("arranque")
