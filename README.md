# bbo-bot

La voz de **Barcelona Bitcoin Only** en Telegram: Claude Opus con el manifiesto
de la comunidad delante, contestando con paciencia las preguntas que se repiten
mil veces, y escalando a los admins lo que no le toca.

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

## Uso

```bash
uv sync --extra dev
cp .env.example .env      # secrets desde rbw
uv run pytest
uv run python -m bbo_bot
```

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
| El tono, los límites, cuándo escala | `bbo_bot/persona.py` |
| Qué responde a una pregunta concreta | `canon.md` |
| Las reglas del grupo | `reglas.md` |
| Los textos fundacionales | `corpus/` (vía `scripts/sync-corpus.sh`) |

Cualquier cambio en esos cuatro invalida la caché del prefijo: la siguiente
pregunta paga escritura y las demás vuelven a leer. Es lo esperado.
