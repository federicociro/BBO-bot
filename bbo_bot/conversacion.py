"""Texto libre: agrupado de mensajes, respuesta y aviso a los admins."""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from . import alertas, rose
from .budget import Presupuesto
from .claude import Voz
from .comun import link_mensaje
from .config import Config

log = logging.getLogger(__name__)


def _va_dirigido(update: Update, bot_username: str, bot_id: int) -> bool:
    msg = update.effective_message
    respondida = msg.reply_to_message
    if respondida and respondida.from_user and respondida.from_user.id == bot_id:
        return True
    return f"@{bot_username}".lower() in (msg.text or "").lower()


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Encola el mensaje. No contesta acá: espera a ver si vienen más.

    Pegar un documento en ocho mensajes seguidos disparaba ocho llamadas casi
    simultáneas. Y como una caché que se está escribiendo todavía no se puede
    leer, varias pagaban el prefijo entero a precio completo. Agrupar es, de
    lejos, el ahorro más grande de todo el bot.
    """
    cfg: Config = ctx.bot_data["cfg"]
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if user and user.is_bot:
        await _guino_rose(update, ctx)
        return

    if chat.type == chat.PRIVATE:
        if not cfg.dm_abierto and user.id not in cfg.dm_allowlist:
            await msg.reply_text(
                "Por privado solo hablo con los admins. Preguntame en el grupo — "
                "y ojo: nadie de BBO te escribe primero por privado. Nadie."
            )
            return
    else:
        if chat.id not in cfg.known_chats:
            log.warning("chat desconocido %s (%s)", chat.id, chat.title)
            return
        if not _va_dirigido(update, ctx.bot.username, ctx.bot.id):
            return

    clave = f"{chat.id}:{user.id}"
    buffer = ctx.bot_data.setdefault("pendientes", {}).setdefault(clave, [])
    buffer.append(msg.text or "")

    # Debounce: cada mensaje nuevo reinicia la cuenta atrás.
    for job in ctx.job_queue.get_jobs_by_name(clave):
        job.schedule_removal()
    ctx.job_queue.run_once(
        _contestar_agrupado,
        cfg.ventana_agrupado_s,
        name=clave,
        data={
            "chat_id": chat.id,
            "user_id": user.id,
            "message_id": msg.message_id,
            "chat_title": chat.title,
            "username": user.username,
        },
    )


async def _contestar_agrupado(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]
    presupuesto: Presupuesto = ctx.bot_data["presupuesto"]
    d = ctx.job.data
    clave = f"{d['chat_id']}:{d['user_id']}"

    trozos = ctx.bot_data.get("pendientes", {}).pop(clave, [])
    if not trozos:
        return
    pregunta = "\n\n".join(t for t in trozos if t).strip()

    async def responder(texto: str) -> None:
        for i in range(0, len(texto), 4000):
            await ctx.bot.send_message(
                d["chat_id"],
                texto[i : i + 4000],
                reply_to_message_id=d["message_id"] if i == 0 else None,
            )

    if len(pregunta) > cfg.max_chars_entrada:
        log.info("entrada descartada: %s caracteres de %s", len(pregunta), d["user_id"])
        await responder(
            f"Me pegaste {len(pregunta)} caracteres en {len(trozos)} mensajes. "
            "No leo documentos enteros: resumime la duda concreta en un párrafo "
            "y te contesto. Si es un tema largo, da para una charla de meetup."
        )
        return

    espera = presupuesto.espera(d["user_id"])
    if espera > 0:
        await responder(f"Dame {espera:.0f} segundos y seguimos.")
        return
    presupuesto.marcar(d["user_id"])

    # Una sola llamada por usuario a la vez: dos en paralelo no comparten caché.
    cerrojos = ctx.bot_data.setdefault("cerrojos", {})
    cerrojo = cerrojos.setdefault(d["user_id"], asyncio.Lock())
    if cerrojo.locked():
        log.info("ya hay una respuesta en curso para %s", d["user_id"])
        return

    async with cerrojo:
        await ctx.bot.send_chat_action(d["chat_id"], ChatAction.TYPING)
        r = await voz.responder(pregunta)

    if not presupuesto.hay_saldo():
        await alertas.avisar(
            ctx,
            cfg.owner_id,
            "presupuesto",
            f"presupuesto diario agotado ({presupuesto.gastado} tokens). "
            "El Q&A queda desactivado hasta mañana.",
        )

    texto = r.texto
    for esc in r.escalados:
        if not await _avisar_escalado(ctx, cfg, esc, d):
            await alertas.avisar(
                ctx,
                cfg.owner_id,
                "escalado-perdido",
                f"NO llegó un escalado ({esc.motivo}). Revisá BBO_ESCALATION_CHAT_ID.\n"
                f"{link_mensaje(d['chat_id'], d['message_id'])}",
                siempre=True,
            )
            texto += (
                "\n\n⚠️ No he podido avisar a los admins por un problema mío. "
                "Escribile a uno directamente, no lo dejes acá."
            )

    await responder(texto)


async def _avisar_escalado(ctx, cfg: Config, esc, d: dict) -> bool:
    quien = f"@{d['username']}" if d.get("username") else f"id {d['user_id']}"
    aviso = (
        f"⚠️ *Escalado* — {esc.motivo}\n\n"
        f"{esc.resumen}\n\n"
        f"De: {quien} · en {d.get('chat_title') or d['chat_id']}\n"
        f"{link_mensaje(d['chat_id'], d['message_id'])}"
    )

    # Urgente primero: esto tiene que llegar a alguien que lo lea hoy.
    entregado = False
    if cfg.escalation_chat_id:
        try:
            await ctx.bot.send_message(cfg.escalation_chat_id, aviso, parse_mode=ParseMode.MARKDOWN)
            entregado = True
        except Exception:
            log.exception("no llegó el escalado urgente a %s", cfg.escalation_chat_id)

    # Copia al log de admins, que se lee semanalmente: es el registro, no el aviso.
    if cfg.admin_chat_id and cfg.admin_chat_id != cfg.escalation_chat_id:
        try:
            await ctx.bot.send_message(
                cfg.admin_chat_id,
                aviso,
                parse_mode=ParseMode.MARKDOWN,
                disable_notification=True,
            )
            entregado = entregado or not cfg.escalation_chat_id
        except Exception:
            log.exception("no llegó la copia al log de admins")

    if not entregado:
        # Nunca en silencio: al log, y la persona se entera en la misma respuesta.
        log.error("ESCALADO NO ENTREGADO: %s / %s", esc.motivo, esc.resumen)
    return entregado


async def _guino_rose(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Guiño esporádico a Rose. Nunca una conversación entre bots."""
    cfg: Config = ctx.bot_data["cfg"]
    msg = update.effective_message
    if update.effective_chat.id not in cfg.known_chats:
        return
    if not rose.es_rose(msg.from_user.username):
        return
    frase = rose.guino(ctx.bot_data.get("rose_activo", True))
    if frase:
        await msg.reply_text(frase)


async def on_cambio_de_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Si la añaden a un chat desconocido: avisa y se va sola."""
    cfg: Config = ctx.bot_data["cfg"]
    mi = update.my_chat_member
    if not mi or mi.new_chat_member.status not in {"member", "administrator"}:
        return
    chat = mi.chat
    if chat.id in cfg.known_chats:
        log.info("añadida a un chat conocido: %s (%s)", chat.title, chat.id)
        return

    quien = mi.from_user.username or mi.from_user.id
    await alertas.avisar(
        ctx,
        cfg.owner_id,
        f"chat-desconocido-{chat.id}",
        f"me añadió @{quien} a un chat que no está en la config: "
        f"{chat.title!r} ({chat.id}). Me salgo.",
        siempre=True,
    )
    try:
        await ctx.bot.leave_chat(chat.id)
    except Exception:
        log.exception("no pude salir del chat %s", chat.id)
