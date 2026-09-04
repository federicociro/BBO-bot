"""Utilidades compartidas por los handlers."""

from __future__ import annotations

from telegram import Update


def link_mensaje(chat_id: int, message_id: int) -> str:
    """URL de un mensaje concreto, para que un admin llegue de un clic."""
    interno = str(chat_id).removeprefix("-100")
    return f"https://t.me/c/{interno}/{message_id}"


async def responder_largo(update: Update, texto: str) -> None:
    """Telegram corta en 4096 caracteres."""
    for i in range(0, len(texto), 4000):
        await update.effective_message.reply_text(texto[i : i + 4000])
