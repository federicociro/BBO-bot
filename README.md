# bbo-bot

**Roser**, la voz de **Barcelona Bitcoin Only** en Telegram: Claude Opus con el
manifiesto de la comunidad delante, contestando con paciencia las preguntas que
se repiten mil veces, y escalando a los admins lo que no le toca.

El nombre es un guiño a Rose, la bot que modera el grupo: Rose pone orden,
Roser pone contexto. Perspicaz, con carácter y algo picante — pero el filo va
contra las ideas y las estafas, nunca contra quien pregunta.

El spec vive en el vault: `notes_sync/bbo-project/SPEC.md`.

## Cómo funciona

- **Sin RAG.** El corpus fundacional (~24k tokens) entra entero en el system
  prompt, cacheado. La ventana es de 1M: montar retrieval sobre cinco textos que
  caben enteros es resolver un problema que no existe.
- **Tres bloques congelados** en el prefijo: `bbo_bot/persona.py` (la voz),
  `reglas.md` (reglas oficiales del grupo, verbatim) y `canon.md` (preguntas
  repetidas con su respuesta canónica).
- **Los admins cambian lo que dice el bot editando markdown**, sin tocar código.
- Los slash commands no pasan por el modelo: gratis e instantáneos.

## Estructura

```
bbo_bot/     código
content/     canon.md, reglas.md, corpus/  ← esto entra en el prompt cacheado
docs/        bitácora, marca, procedencia de los textos
deploy/      Dockerfile, compose, unit de systemd
scripts/     repaso, metadata de los bots, verificaciones
tests/
```

Todo lo de `content/` va dentro del prefijo cacheado: tocarlo invalida la caché
del prompt. Está agrupado justamente para que eso se vea.

## Uso

```bash
uv sync --extra dev
cp .env.example .env               # secrets desde rbw
uv run pytest                      # rápido, sin red
uv run python -m bbo_bot
```

### Comprobar que Roser no se rompió

```bash
uv run python scripts/repaso.py
```

Corre las 40 preguntas de `tests/preguntas.md` —comunidad, primeros pasos,
casos que deben pasar a un admin, y provocaciones— y escribe un informe con
cada respuesta, su longitud y si derivó a un admin. Si alguna de las de
escalado no deriva, sale con código 1.

**Gasta dinero de verdad** (~1 $ por pasada), así que no está en CI.

## Metadata de los bots

Nombre, bio, descripción (ES/CA/EN) y comandos se aplican con
`scripts/set-bot-metadata.sh <token> "Nombre"`. El avatar está en
`docs/brand/roser.png`. El @usuario y la foto de perfil
solo se cambian a mano en BotFather.

## Comandos

| | |
|---|---|
| `/meetup` | próximo encuentro (feed público de Meetup) |
| `/precio` `/fees` `/bloque` `/halving` | nodo propio |
| `/manifiesto` `/cita` | el manifiesto |
| `/reglas` | reglas del grupo |
| texto libre | Q&A, solo si lo mencionan o le contestan |

## Dónde se toca qué

| Querés cambiar | Editás |
|---|---|
| El carácter de Roser, los límites, cuándo pasa a un admin | `bbo_bot/persona.py` |
| Qué responde a una pregunta concreta | `content/canon.md` |
| Las reglas del grupo | `content/reglas.md` |
| Los textos fundacionales | `content/corpus/` (vía `scripts/sync-corpus.sh`) |

Cualquier cambio en esos cuatro invalida la caché del prefijo: la siguiente
pregunta paga escritura y las demás vuelven a leer. Es lo esperado.
