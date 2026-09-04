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
        _contestar_agrupado, cfg.ventana_agrupado_s, name=clave,
        data={"chat_id": chat.id, "user_id": user.id, "message_id": msg.message_id,
              "chat_title": chat.title, "username": user.username},
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
                d["chat_id"], texto[i : i + 4000],
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
            ctx, cfg.owner_id, "presupuesto",
            f"presupuesto diario agotado ({presupuesto.gastado} tokens). "
            "El Q&A queda desactivado hasta mañana.",
        )

    texto = r.texto
    for esc in r.escalados:
        if not await _avisar_escalado(ctx, cfg, esc, d):
            await alertas.avisar(
                ctx, cfg.owner_id, "escalado-perdido",
                f"NO llegó un escalado ({esc.motivo}). Revisá BBO_ESCALATION_CHAT_ID.\n"
                f"{_link(d['chat_id'], d['message_id'])}",
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
        f"{_link(d['chat_id'], d['message_id'])}"
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


async def job_auto_pull(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Trae los cambios del canon y recarga solo si algo cambió de verdad.

    Sin esto, editar el canon en GitHub no llega a Roser hasta que alguien se
    acuerde de /recargar — y nadie se acuerda.
    """
    cfg: Config = ctx.bot_data["cfg"]
    voz: Voz = ctx.bot_data["voz"]

    ok, detalle = await asyncio.to_thread(_git_pull, cfg)
    if not ok:
        log.warning("auto-pull falló: %s", detalle)
        return
    if "Already up to date" in detalle or "Ya está actualizado" in detalle:
        return

    try:
        chars = await asyncio.to_thread(voz.recargar)
    except Exception:  # noqa: BLE001
        log.exception("auto-pull trajo cambios pero no pude recargar")
        await alertas.avisar(
            ctx, cfg.owner_id, "recarga-fallida",
            "traje cambios del canon pero no pude recargarlos. Sigo con el anterior.",
            siempre=True,
        )
        return

    log.info("canon recargado tras auto-pull: %s chars", chars)
    await alertas.avisar(
        ctx, cfg.owner_id, "canon-actualizado",
        f"canon actualizado desde git y recargado ({chars} caracteres). {detalle}",
        siempre=True,
    )


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
        if cfg.git_pull and cfg.auto_pull_min:
            app.job_queue.run_repeating(
                job_auto_pull, interval=cfg.auto_pull_min * 60, first=60
            )
            log.info("auto-pull del canon cada %s min", cfg.auto_pull_min)

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
