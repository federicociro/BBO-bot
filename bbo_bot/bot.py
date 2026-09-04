"""Handlers de Telegram.

Reglas de convivencia que se implementan acá:
- En el grupo el bot está callado salvo que lo mencionen o le contesten.
- Por privado solo habla con la allowlist. Un bot que atiende MDs a cualquiera
  normaliza justo el patrón del que avisamos ("los admins no te escriben
  primero").
- Nada de publicar solo en el canal: redacta, y publica un admin.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, time as dtime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import alertas, mempool, meetup, rose
from .budget import Presupuesto
from .claude import Voz
from .config import Config

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


def _link(chat_id: int, message_id: int) -> str:
    interno = str(chat_id).removeprefix("-100")
    return f"https://t.me/c/{interno}/{message_id}"


async def _responder_largo(update: Update, texto: str) -> None:
    """Telegram corta en 4096 caracteres."""
    for i in range(0, len(texto), 4000):
        await update.effective_message.reply_text(texto[i : i + 4000])


# --- comandos -------------------------------------------------------------


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(AYUDA)


async def cmd_meetup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    try:
        ev = await asyncio.to_thread(meetup.proximo, cfg.meetup_group)
    except Exception:  # noqa: BLE001
        await update.effective_message.reply_text("No puedo consultar la agenda ahora mismo.")
        return
    if ev is None:
        await update.effective_message.reply_text(
            "No hay ningún meetup publicado todavía. En cuanto haya fecha sale en Meetup."
        )
        return
    await update.effective_message.reply_text(ev.humano(), disable_web_page_preview=False)


def _cmd_nodo(fn, error: str):
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
    await _responder_largo(update, cuerpo.strip())


async def cmd_recargar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Relee el canon tras editarlo. Solo dueño o desde el log de admins."""
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]
    user = update.effective_user
    chat = update.effective_chat
    if user.id != cfg.owner_id and chat.id != cfg.admin_chat_id:
        return

    if cfg.git_pull:
        ok, detalle = await asyncio.to_thread(_git_pull, cfg)
        if not ok:
            await update.effective_message.reply_text(f"No pude actualizar desde git: {detalle}")
            return
        await update.effective_message.reply_text(f"git: {detalle}")

    try:
        chars = await asyncio.to_thread(voz.recargar)
    except Exception as e:  # noqa: BLE001
        await update.effective_message.reply_text(f"No pude recargar: {e}")
        log.exception("fallo al recargar el material")
        return
    await update.effective_message.reply_text(
        f"Material recargado: {chars:,} caracteres. "
        "La próxima pregunta reescribe la caché.".replace(",", ".")
    )


def _git_pull(cfg: Config) -> tuple[bool, str]:
    import subprocess

    raiz = cfg.canon_path.parent
    if not (raiz / ".git").exists():
        return False, "esto no es un checkout de git"
    try:
        r = subprocess.run(
            ["git", "-C", str(raiz), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "git pull tardó demasiado"
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:200]
    return True, (r.stdout or "sin cambios").strip().splitlines()[-1][:200]


async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """El id que hay que poner en el .env, dicho por el propio bot."""
    chat = update.effective_chat
    await update.effective_message.reply_text(
        f"chat_id: {chat.id}\ntipo: {chat.type}\ntu user_id: {update.effective_user.id}"
    )


# --- texto libre ----------------------------------------------------------


def _va_dirigido(update: Update, bot_username: str, bot_id: int) -> bool:
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        if msg.reply_to_message.from_user.id == bot_id:
            return True
    return f"@{bot_username}".lower() in (msg.text or "").lower()


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]
    presupuesto: Presupuesto = ctx.bot_data["presupuesto"]
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

    espera = presupuesto.espera(user.id)
    if espera > 0:
        await msg.reply_text(f"Dame {espera:.0f} segundos y seguimos.")
        return
    presupuesto.marcar(user.id)

    await ctx.bot.send_chat_action(chat.id, ChatAction.TYPING)
    r = await voz.responder(msg.text or "")

    if not presupuesto.hay_saldo():
        await alertas.avisar(
            ctx, cfg.owner_id, "presupuesto",
            f"presupuesto diario agotado ({presupuesto.gastado} tokens). "
            "El Q&A queda desactivado hasta mañana.",
        )

    texto = r.texto
    for esc in r.escalados:
        if not await _avisar_admins(ctx, cfg, esc, chat, msg, user):
            await alertas.avisar(
                ctx, cfg.owner_id, "escalado-perdido",
                f"NO llegó un escalado al log de admins ({esc.motivo}). "
                f"Revisá BBO_ADMIN_CHAT_ID.\n{_link(chat.id, msg.message_id)}",
                siempre=True,
            )
            texto += (
                "\n\n⚠️ No he podido avisar a los admins por un problema mío. "
                "Escribile a uno directamente, no lo dejes acá."
            )

    await _responder_largo(update, texto)


async def _avisar_admins(ctx, cfg: Config, esc, chat, msg, user) -> bool:
    quien = f"@{user.username}" if user.username else f"id {user.id}"
    aviso = (
        f"⚠️ *Escalado* — {esc.motivo}\n\n"
        f"{esc.resumen}\n\n"
        f"De: {quien} · en {chat.title or chat.id}\n"
        f"{_link(chat.id, msg.message_id)}"
    )

    # Urgente primero: esto tiene que llegar a alguien que lo lea hoy.
    entregado = False
    if cfg.escalation_chat_id:
        try:
            await ctx.bot.send_message(
                cfg.escalation_chat_id, aviso, parse_mode=ParseMode.MARKDOWN
            )
            entregado = True
        except Exception:  # noqa: BLE001
            log.exception("no llegó el escalado urgente a %s", cfg.escalation_chat_id)

    # Copia al log de admins, que se lee semanalmente: es el registro, no el aviso.
    if cfg.admin_chat_id and cfg.admin_chat_id != cfg.escalation_chat_id:
        try:
            await ctx.bot.send_message(
                cfg.admin_chat_id, aviso, parse_mode=ParseMode.MARKDOWN,
                disable_notification=True,
            )
            entregado = entregado or not cfg.escalation_chat_id
        except Exception:  # noqa: BLE001
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
        ctx, cfg.owner_id, f"chat-desconocido-{chat.id}",
        f"me añadió @{quien} a un chat que no está en la config: "
        f"{chat.title!r} ({chat.id}). Me salgo.",
        siempre=True,
    )
    try:
        await ctx.bot.leave_chat(chat.id)
    except Exception:  # noqa: BLE001
        log.exception("no pude salir del chat %s", chat.id)


# --- meetup: borrador para los admins, publica un humano ------------------


async def job_meetup(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cfg: Config = ctx.bot_data["cfg"]
    try:
        ev = await asyncio.to_thread(meetup.proximo, cfg.meetup_group)
    except Exception:  # noqa: BLE001
        log.exception("no se pudo leer la agenda")
        return
    if ev is None:
        return
    manana = datetime.now(meetup.TZ) + timedelta(days=1)
    if ev.inicio.date() != manana.date():
        return

    borrador = f"📅 Mañana hay meetup:\n\n{ev.humano()}"
    teclado = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Publicar en el canal", callback_data="pub"),
            InlineKeyboardButton("Descartar", callback_data="no"),
        ]]
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


# --- arranque -------------------------------------------------------------


def arrancar() -> None:
    cfg = Config.from_env()
    presupuesto = Presupuesto(cfg.daily_token_budget, cfg.cooldown_s)

    app = Application.builder().token(cfg.telegram_token).build()
    app.bot_data.update(
        cfg=cfg,
        presupuesto=presupuesto,
        voz=Voz(cfg, presupuesto),
    )

    app.add_handler(CommandHandler(["start", "ayuda", "help"], cmd_start))
    app.add_handler(CommandHandler("meetup", cmd_meetup))
    app.add_handler(CommandHandler("precio", cmd_precio))
    app.add_handler(CommandHandler("fees", _cmd_nodo(mempool.fees, "No puedo consultar las fees ahora mismo.")))
    app.add_handler(CommandHandler("bloque", _cmd_nodo(mempool.bloque, "No puedo consultar la altura ahora mismo.")))
    app.add_handler(CommandHandler("halving", _cmd_nodo(mempool.halving, "No puedo consultar la altura ahora mismo.")))
    app.add_handler(CommandHandler("manifiesto", cmd_manifiesto))
    app.add_handler(CommandHandler("cita", cmd_cita))
    app.add_handler(CommandHandler("reglas", cmd_reglas))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("recargar", cmd_recargar))
    app.add_handler(CallbackQueryHandler(on_boton))
    app.add_handler(ChatMemberHandler(on_cambio_de_chat, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    if app.job_queue:
        app.job_queue.run_daily(job_meetup, time=dtime(hour=18, minute=0))

    if cfg.dm_abierto:
        log.warning("BBO_DM_OPEN activo: el privado está abierto a cualquiera (solo QA)")
    if not app.bot_data["voz"].activa:
        log.warning("modo QA sin modelo: solo comandos")
    app.post_init = _comprobar_admins

    log.info("BBO bot en marcha (modelo=%s, effort=%s)", cfg.model, cfg.effort)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def _comprobar_admins(app: Application) -> None:
    """Al arrancar: ¿llegamos al chat de admins? Si no, que se vea."""
    cfg: Config = app.bot_data["cfg"]
    destino = cfg.escalation_chat_id or cfg.admin_chat_id
    try:
        chat = await app.bot.get_chat(destino)
        log.info("destino de escalados OK: %s (%s)", chat.title or chat.first_name, chat.id)
    except Exception as e:  # noqa: BLE001
        log.error(
            "NO SE LLEGA AL DESTINO DE ESCALADOS %s (%s). "
            "Añadí la bot al chat, o escribile por privado, y comprobá el id con /chatid.",
            destino, e,
        )
        if cfg.owner_id:
            try:
                await app.bot.send_message(
                    cfg.owner_id,
                    f"🤖 Roser · arranqué, pero NO llego al destino de escalados "
                    f"({destino}): {e}. Los escalados no van a llegar.",
                )
            except Exception:  # noqa: BLE001
                log.exception("tampoco se pudo alertar al dueño")
