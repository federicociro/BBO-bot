# NOTES — bbo-bot

Bitácora. Lo que se decidió y por qué, y lo que falta.

## 2026-09-03 — arranque

Repo creado a partir de `notes_sync/bbo-project/SPEC.md`. Antes hubo un
scaffold sobre Ollama que se borró entero: la arquitectura pasó a Claude API.

### Decisiones

- **Sin RAG.** Corpus + reglas + canon = ~87 KB ≈ 24k tokens estimados, contra
  1M de ventana. Un breakpoint de caché en el segundo bloque de `system`.
- **Un solo modelo**, `claude-opus-5`, `effort=medium` pinneado. Multimodelo
  descartado: las cachés son por modelo, y el modelo barato acabaría atendiendo
  a los recién llegados, que es justo donde importa la voz.
- **TTL de caché 5 min** (default), sin re-warm programado. El tráfico del grupo
  es bursty con huecos de horas; el TTL de 1 h cuesta el doble de escritura y
  tampoco cubre el hueco.
- **mempool y meetup son síncronos** porque el `tool_runner` del SDK de Python
  lo es. `Voz.responder()` lo mete en `asyncio.to_thread` para no bloquear el
  event loop de PTB. Así hay una sola implementación en vez de duplicar
  async/sync.
- **Meetup por feeds públicos** (iCal para fecha/hora/link, RSS para la
  descripción), no GraphQL, aunque BBO tenga Pro: es un calendario público y
  meterle OAuth2 no compra nada.
- **Guiños a Rose enlatados**, nunca generados por el modelo: dos bots
  hablándose es un bucle, y el texto de Rose lo escribe cualquiera con un
  trigger, así que no entra al prompt.
- **Fulcrum fuera de v1**: address/xpub en un grupo público es un footgun de
  privacidad.

### Comandos ejecutados

```bash
uv sync --extra dev          # anthropic 1.3.0, python-telegram-bot 22.8
uv run pytest                # 12 passed
uvx yamllint --strict ...    # OK
curl .../getMe               # @BBO_8333_bot, privacy mode ON
```

### Verificado contra servicios reales

- `https://mempool.federicociro.com/api` responde precio, fees y altura.
- Feed iCal de `bitcoin-barcelona`: da `DTSTART` con TZID, `SUMMARY`, `URL`.
- Token de Telegram válido.

### Pendiente

- [ ] **`ANTHROPIC_API_KEY`**: no hay ninguna todavía. Nada del camino que pasa
      por el modelo está probado contra la API real — en particular que
      `tool_runner` acepte `output_config`, `thinking`, `betas` y `fallbacks`
      juntos. Es lo primero que hay que ejercitar.
- [ ] **Añadir el bot a los tres chats y correr `scripts/verify-chats.sh`.**
      Ahora mismo `getChat` da "chat not found" en los tres, que es lo normal
      cuando el bot no es miembro. Si el id del log está mal, los escalados se
      pierden en silencio.
- [ ] **Privacy mode**: está ON (`can_read_all_group_messages: false`), que
      encaja con "el bot está callado salvo que lo mencionen". Consecuencia a
      decidir: así **no puede detectar una seed pegada en el grupo** si el
      mensaje no lo menciona. Apagarlo permitiría un detector local por regex
      (sin mandar nada a la API, sin loggear), a cambio de que el bot reciba
      todos los mensajes.
- [ ] Medir el corpus con `messages.count_tokens` y rehacer la tabla de coste
      del spec.
- [ ] Rellenar los 8 `[[?]]` de `canon.md`.
- [ ] Rotar el token de Telegram con `/revoke` (se compartió en claro) y
      guardarlo en `rbw`.
- [ ] Deploy: compose en `homelab-docker/`, entrada en `ansible-plays`.
