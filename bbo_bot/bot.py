"""Arranque y registro de handlers."""

from __future__ import annotations

import logging
from datetime import time as dtime

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from . import comandos, conversacion, jobs, mempool
from .budget import Presupuesto
from .claude import Voz
from .config import Config

log = logging.getLogger(__name__)


def arrancar() -> None:
    cfg = Config.from_env()
    presupuesto = Presupuesto(cfg.daily_token_budget, cfg.cooldown_s)

    app = Application.builder().token(cfg.telegram_token).build()
    app.bot_data.update(cfg=cfg, presupuesto=presupuesto, voz=Voz(cfg, presupuesto))

    app.add_handler(CommandHandler(["start", "ayuda", "help"], comandos.cmd_start))
    app.add_handler(CommandHandler("meetup", comandos.cmd_meetup))
    app.add_handler(CommandHandler("precio", comandos.cmd_precio))
    app.add_handler(
        CommandHandler(
            "fees", comandos.cmd_nodo(mempool.fees, "No puedo consultar las fees ahora mismo.")
        )
    )
    app.add_handler(
        CommandHandler(
            "bloque", comandos.cmd_nodo(mempool.bloque, "No puedo consultar la altura ahora mismo.")
        )
    )
    app.add_handler(
        CommandHandler(
            "halving",
            comandos.cmd_nodo(mempool.halving, "No puedo consultar la altura ahora mismo."),
        )
    )
    app.add_handler(CommandHandler("manifiesto", comandos.cmd_manifiesto))
    app.add_handler(CommandHandler("cita", comandos.cmd_cita))
    app.add_handler(CommandHandler("reglas", comandos.cmd_reglas))
    app.add_handler(CommandHandler("chatid", comandos.cmd_chatid))
    app.add_handler(CommandHandler("recargar", comandos.cmd_recargar))
    app.add_handler(CallbackQueryHandler(jobs.on_boton))
    app.add_handler(
        ChatMemberHandler(conversacion.on_cambio_de_chat, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, conversacion.on_text))

    if app.job_queue:
        app.job_queue.run_daily(jobs.job_meetup, time=dtime(hour=18, minute=0))
        if cfg.git_pull and cfg.auto_pull_min:
            app.job_queue.run_repeating(
                jobs.job_auto_pull, interval=cfg.auto_pull_min * 60, first=60
            )
            log.info("auto-pull del canon cada %s min", cfg.auto_pull_min)

    app.post_init = _comprobar_destino

    if cfg.dm_abierto:
        log.warning("BBO_DM_OPEN activo: el privado está abierto a cualquiera (solo QA)")
    if not app.bot_data["voz"].activa:
        log.warning("modo QA sin modelo: solo comandos")
    log.info("Roser en marcha (modelo=%s, effort=%s)", cfg.model, cfg.effort)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def _comprobar_destino(app: Application) -> None:
    """Al arrancar: ¿llegamos a donde se registran los escalados?"""
    cfg: Config = app.bot_data["cfg"]
    destino = cfg.escalation_chat_id or cfg.admin_chat_id
    try:
        chat = await app.bot.get_chat(destino)
        log.info("destino de escalados OK: %s (%s)", chat.title or chat.first_name, chat.id)
    except Exception as e:
        log.error(
            "NO SE LLEGA AL DESTINO DE ESCALADOS %s (%s). Se pierde el registro; "
            "los avisos a admins siguen yendo por @admin en el grupo.",
            destino,
            e,
        )
        if cfg.owner_id:
            try:
                await app.bot.send_message(
                    cfg.owner_id,
                    f"🤖 Roser · arranqué, pero no llego al destino de escalados ({destino}): {e}.",
                )
            except Exception:
                log.exception("tampoco se pudo alertar al dueño")
