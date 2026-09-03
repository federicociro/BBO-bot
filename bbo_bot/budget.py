"""Presupuesto diario de tokens y cooldown por usuario.

Es la única protección real contra un bucle o un troll: el bot vive en un grupo
público y cada mensaje al modelo cuesta dinero.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Presupuesto:
    limite_diario: int
    cooldown_s: int
    _dia: date = field(default_factory=date.today)
    _gastado: int = 0
    _ultimo: dict[int, float] = field(default_factory=dict)

    def _rotar(self) -> None:
        hoy = date.today()
        if hoy != self._dia:
            self._dia, self._gastado = hoy, 0

    @property
    def gastado(self) -> int:
        self._rotar()
        return self._gastado

    def hay_saldo(self) -> bool:
        self._rotar()
        return self._gastado < self.limite_diario

    def apuntar(self, tokens: int) -> None:
        self._rotar()
        self._gastado += tokens

    def espera(self, user_id: int) -> float:
        """Segundos que le faltan a este usuario, 0 si puede preguntar."""
        ultimo = self._ultimo.get(user_id)
        if ultimo is None:
            return 0.0
        return max(0.0, self.cooldown_s - (time.monotonic() - ultimo))

    def marcar(self, user_id: int) -> None:
        self._ultimo[user_id] = time.monotonic()
