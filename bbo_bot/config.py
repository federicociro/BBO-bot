"""Configuracion por env vars. Los secrets viven en Vaultwarden, nunca acá."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _req(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise SystemExit(f"Falta {name}. Mirá .env.example — los secrets están en rbw.")
    return v


def _ids(raw: str | None) -> frozenset[int]:
    return frozenset(int(x) for x in (raw or "").replace(",", " ").split())


@dataclass(frozen=True)
class Config:
    telegram_token: str
    main_chat_id: int
    admin_chat_id: int
    channel_id: int
    dm_allowlist: frozenset[int]
    dm_abierto: bool
    owner_id: int
    escalation_chat_id: int
    git_pull: bool

    model: str
    effort: str

    mempool_url: str
    meetup_group: str
    fiat: str

    cooldown_s: int
    max_chars_entrada: int
    ventana_agrupado_s: float
    daily_token_budget: int

    corpus_dir: Path = ROOT / "corpus"
    canon_path: Path = ROOT / "canon.md"
    reglas_path: Path = ROOT / "reglas.md"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            telegram_token=_req("BBO_TELEGRAM_TOKEN"),
            main_chat_id=int(_req("BBO_MAIN_CHAT_ID")),
            admin_chat_id=int(_req("BBO_ADMIN_CHAT_ID")),
            channel_id=int(os.environ.get("BBO_CHANNEL_ID") or 0),
            dm_allowlist=_ids(os.environ.get("BBO_DM_ALLOWLIST")),
            dm_abierto=os.environ.get("BBO_DM_OPEN", "").strip() in {"1", "true", "yes"},
            owner_id=int(os.environ.get("BBO_OWNER_ID") or 0),
            # Los escalados urgentes van donde se lean YA. Si no hay un chat
            # dedicado, al privado del dueño; el log de admins recibe copia.
            escalation_chat_id=int(
                os.environ.get("BBO_ESCALATION_CHAT_ID")
                or os.environ.get("BBO_OWNER_ID")
                or 0
            ),
            git_pull=os.environ.get("BBO_GIT_PULL", "").strip() in {"1", "true", "yes"},
            model=os.environ.get("BBO_MODEL", "claude-opus-5"),
            effort=os.environ.get("BBO_EFFORT", "medium"),
            mempool_url=os.environ.get("BBO_MEMPOOL_URL", "").rstrip("/"),
            meetup_group=os.environ.get("BBO_MEETUP_GROUP", "bitcoin-barcelona"),
            fiat=os.environ.get("BBO_FIAT", "EUR").upper(),
            cooldown_s=int(os.environ.get("BBO_COOLDOWN_S", "15")),
            max_chars_entrada=int(os.environ.get("BBO_MAX_CHARS_ENTRADA", "1500")),
            ventana_agrupado_s=float(os.environ.get("BBO_VENTANA_AGRUPADO_S", "8")),
            daily_token_budget=int(os.environ.get("BBO_DAILY_TOKEN_BUDGET", "500000")),
        )

    @property
    def known_chats(self) -> frozenset[int]:
        """Allowlist dura: fuera de estos chats el bot no habla."""
        return frozenset(c for c in (self.main_chat_id, self.admin_chat_id, self.channel_id) if c)
