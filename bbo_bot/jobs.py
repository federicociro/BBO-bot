"""Tareas periodicas: canon al dia y aviso de meetup."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from . import alertas, meetup
from .claude import Voz
from .config import Config
from .git import git_pull

log = logging.getLogger(__name__)


async def job_auto_pull(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Trae los cambios del canon y recarga solo si algo cambió de verdad.

    Sin esto, editar el canon en GitHub no llega a Roser hasta que alguien se
    acuerde de /recargar — y nadie se acuerda.
    """
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]

    ok, detalle = await asyncio.to_thread(git_pull, cfg)
    if not ok:
        log.warning("auto-pull falló: %s", detalle)
        return
    if "Already up to date" in detalle or "Ya está actualizado" in detalle:
        return

    try:
        chars = await asyncio.to_thread(voz.recargar)
    except Exception:
        log.exception("auto-pull trajo cambios pero no pude recargar")
        await alertas.avisar(
            ctx,
            cfg.owner_id,
            "recarga-fallida",
            "traje cambios del canon pero no pude recargarlos. Sigo con el anterior.",
            siempre=True,
        )
        return

    log.info("canon recargado tras auto-pull: %s chars", chars)
    await alertas.avisar(
        ctx,
        cfg.owner_id,
        "canon-actualizado",
        f"canon actualizado desde git y recargado ({chars} caracteres). {detalle}",
        siempre=True,
    )


# --- meetup: borrador para los admins, publica un humano ------------------


async def job_meetup(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    try:
        ev = await asyncio.to_thread(meetup.proximo, cfg.meetup_group)
    except Exception:
        log.exception("no se pudo leer la agenda")
        return
    if ev is None:
        return
    manana = datetime.now(meetup.TZ) + timedelta(days=1)
    if ev.inicio.date() != manana.date():
        return

    borrador = f"📅 Mañana hay meetup:\n\n{ev.humano()}"
    teclado = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Publicar en el canal", callback_data="pub"),
                InlineKeyboardButton("Descartar", callback_data="no"),
            ]
        ]
    )
    await ctx.bot.send_message(
        cfg.admin_chat_id,
        f"Borrador de anuncio (no se publica solo):\n\n{borrador}",
        reply_markup=teclado,
    )
    ctx.bot_data["borrador"] = borrador


async def on_boton(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    q = update.callback_query
    await q.answer()
    if q.data == "pub" and ctx.bot_data.get("borrador"):
        await ctx.bot.send_message(cfg.channel_id, ctx.bot_data["borrador"])
        await q.edit_message_text("Publicado en el canal.")
    else:
        await q.edit_message_text("Descartado.")
    ctx.bot_data.pop("borrador", None)
