"""Traer cambios del canon desde git.

El checkout es la fuente del material: los admins mergean en GitHub y Roser
recarga sin que nadie entre al servidor.
"""

from __future__ import annotations

import subprocess

from .config import Config


def git_pull(cfg: Config) -> tuple[bool, str]:
    raiz = cfg.canon_path.parent.parent
    if not (raiz / ".git").exists():
        return False, "esto no es un checkout de git"
    try:
        r = subprocess.run(
            ["git", "-C", str(raiz), "pull", "--ff-only"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "git pull tardó demasiado"
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:200]
    return True, (r.stdout or "sin cambios").strip().splitlines()[-1][:200]
