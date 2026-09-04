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

- La instancia propia de mempool responde precio, fees y altura.
- Feed iCal de `bitcoin-barcelona`: da `DTSTART` con TZID, `SUMMARY`, `URL`.
- Token de Telegram válido.

### 2026-09-04 — el incidente de los dos euros

Alguien pegó el raw de una wiki (una BIP) repartido en **ocho mensajes
seguidos**. Roser contestó ocho veces, con ensayos de 200-400 palabras cada uno.
Coste: un par de euros por lo que debería haber sido una respuesta.

Tres fallos encadenados, y el caro no era el evidente:

1. **Ocho llamadas casi simultáneas.** Una entrada de caché que se está
   escribiendo todavía no se puede leer, así que varias pagaron el prefijo
   entero (33k tokens) a precio completo en vez de a precio de caché. Eso solo
   multiplica por diez.
2. **Sin límite de entrada.** El documento entero entraba al prompt.
3. **Respuestas larguísimas**, con thinking facturado como salida.

Arreglos: se agrupan los mensajes de un mismo usuario con debounce de 8 s y se
contesta una sola vez; cerrojo por usuario para que nunca haya dos llamadas en
paralelo; entrada por encima de 1500 caracteres ni se manda al modelo; y regla
dura de longitud en la persona (2-4 frases, una idea por respuesta, sin menús
de conversación al final). Medido después: de 200-400 palabras a 44-97, y
`max_tokens` de 1024 a 700.

**Lección**: el límite de gasto no puede vivir solo en el presupuesto diario. La
concurrencia es lo que rompe la economía de la caché, y no se ve venir.

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
