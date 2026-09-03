from bbo_bot.budget import Presupuesto


def test_corta_al_agotar_el_dia():
    p = Presupuesto(limite_diario=100, cooldown_s=0)
    assert p.hay_saldo()
    p.apuntar(100)
    assert not p.hay_saldo()


def test_cooldown_por_usuario():
    p = Presupuesto(limite_diario=10_000, cooldown_s=30)
    assert p.espera(1) == 0
    p.marcar(1)
    assert 0 < p.espera(1) <= 30
    assert p.espera(2) == 0  # otro usuario no paga el cooldown ajeno
