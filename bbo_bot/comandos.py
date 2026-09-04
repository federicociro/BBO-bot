"""Comandos con barra. Ninguno pasa por el modelo: gratis e instantaneos."""

from __future__ import annotations

import asyncio
import logging
import random

from telegram import Update
from telegram.ext import ContextTypes

from . import meetup, mempool
from .claude import Voz
from .comun import responder_largo
from .config import Config
from .git import git_pull

log = logging.getLogger(__name__)

AYUDA = """\
Soy Roser. Rose pone orden en el grupo; yo pongo contexto.

Preguntame lo que quieras sobre Bitcoin, la comunidad o el manifiesto —
mencioname o contestá a un mensaje mío. Ninguna duda es demasiado básica.

/meetup — próximo encuentro
/precio /fees /bloque /halving — datos de nuestro nodo
/manifiesto /cita — el manifiesto de la comunidad
/reglas — las reglas del grupo

Lo delicado —estafas, custodia, impuestos— lo mira un humano, no yo."""


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(AYUDA)


async def cmd_meetup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    try:
        ev = await asyncio.to_thread(meetup.proximo, cfg.meetup_group)
    except Exception:
        await update.effective_message.reply_text("No puedo consultar la agenda ahora mismo.")
        return
    if ev is None:
        await update.effective_message.reply_text(
            "No hay ningún meetup publicado todavía. En cuanto haya fecha sale en Meetup."
        )
        return
    await update.effective_message.reply_text(ev.humano(), disable_web_page_preview=False)


def cmd_nodo(fn, error: str):
    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        cfg: Config = ctx.bot_data["cfg"]
        try:
            texto = await asyncio.to_thread(fn, cfg.mempool_url)
        except mempool.MempoolError:
            texto = error
        await update.effective_message.reply_text(texto)

    return handler


async def cmd_precio(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    try:
        texto = await asyncio.to_thread(mempool.precio, cfg.mempool_url, cfg.fiat)
    except mempool.MempoolError:
        texto = "No puedo consultar el precio ahora mismo."
    await update.effective_message.reply_text(texto)


async def cmd_manifiesto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    texto = (cfg.corpus_dir / "00-manifesto-bbo.md").read_text(encoding="utf-8")
    apertura = "\n\n".join(p.strip() for p in texto.split("\n\n")[:3] if p.strip())
    await update.effective_message.reply_text(
        f"{apertura}\n\n— bitcoinbarcelona.xyz", disable_web_page_preview=True
    )


async def cmd_cita(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    texto = (cfg.corpus_dir / "00-manifesto-bbo.md").read_text(encoding="utf-8")
    parrafos = [p.strip() for p in texto.split("\n\n") if 120 < len(p.strip()) < 700]
    await update.effective_message.reply_text(random.choice(parrafos))


async def cmd_reglas(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    cuerpo = cfg.reglas_path.read_text(encoding="utf-8").split("---")[0]
    await responder_largo(update, cuerpo.strip())


async def cmd_recargar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Relee el canon tras editarlo. Solo dueño o desde el log de admins."""
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]
    user = update.effective_user
    chat = update.effective_chat
    if user.id != cfg.owner_id and chat.id != cfg.admin_chat_id:
        return

    if cfg.git_pull:
        ok, detalle = await asyncio.to_thread(git_pull, cfg)
        if not ok:
            await update.effective_message.reply_text(f"No pude actualizar desde git: {detalle}")
            return
        await update.effective_message.reply_text(f"git: {detalle}")

    try:
        chars = await asyncio.to_thread(voz.recargar)
    except Exception as e:
        await update.effective_message.reply_text(f"No pude recargar: {e}")
        log.exception("fallo al recargar el material")
        return
    await update.effective_message.reply_text(
        f"Material recargado: {chars:,} caracteres. "
        "La próxima pregunta reescribe la caché.".replace(",", ".")
    )


async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """El id que hay que poner en el .env, dicho por el propio bot."""
    chat = update.effective_chat
    await update.effective_message.reply_text(
        f"chat_id: {chat.id}\ntipo: {chat.type}\ntu user_id: {update.effective_user.id}"
    )
