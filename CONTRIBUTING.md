# Contribuir

Repo técnico. Los admins no técnicos de BBO **no tocan esto**: nos piden
cambios en el grupo y quien sabe de código hace de interfaz. Igual que ellos no
nos piden a nosotros que llevemos la comunicación de la comunidad.

## Qué se toca para cambiar a Roser

| Querés cambiar | Editás |
|---|---|
| Qué responde a una pregunta concreta | `content/canon.md` |
| Su carácter, sus límites, cuándo pasa a un admin | `bbo_bot/persona.py` |
| Las reglas del grupo (texto oficial, verbatim) | `content/reglas.md` |
| Los textos fundacionales | `content/corpus/` |

Todo `content/` va dentro del prompt cacheado. Cambiarlos invalida la caché:
la siguiente pregunta paga la escritura, las de después vuelven a leerla. Es
barato, pero no es gratis — no los toques por cosmética.

## Escribir canon

````markdown
### ¿La pregunta, tal como la hace la gente?
La respuesta en la voz de Roser: directa, 2-4 frases, con posición.
````

- **No es un FAQ que se copia y pega.** Es el contenido correcto *y* el ejemplo
  de tono a la vez.
- **Nunca un veredicto sin motivo.** Si escribís "X no" y no explicás por qué,
  Roser se inventa la razón — y cada vez una distinta. Pasó con Ledger.
- **Con posición.** "Hay opiniones para todos los gustos" no es una respuesta.
- Sin consejo financiero: ni precios objetivo, ni predicciones.
- Si el caso lo tiene que ver una persona, escribí `→ **escala**`. Roser no
  avisa a nadie: le dice a quien pregunta que responda con `@admin`, y de eso
  se encarga Rose.
- `[[?]]` marca lo indefinido. Roser dice que no está decidido en vez de
  inventárselo.

## Ramas y worktrees

**Una rama por issue**, nunca commits directos a `main`:

```bash
git worktree add -b issue-N-slug ../bbo-bot.worktrees/issue-N-slug main
cd ../bbo-bot.worktrees/issue-N-slug && uv sync --extra dev
```

Worktrees y no `git checkout`, por un motivo concreto: **el bot de QA corre
desde este checkout**. Cambiar de rama aquí le mueve los ficheros bajo los pies
a un proceso vivo — y como `content/` se relee en caliente, se pondría a
contestar con el canon de una rama a medias.

Regla: **`/home/fede/git/bbo-bot` se queda en `main` siempre.** El trabajo va
en `../bbo-bot.worktrees/`. Al terminar:

```bash
git worktree remove ../bbo-bot.worktrees/issue-N-slug
```

Tras mergear a `main`, reiniciá QA para que coja el código nuevo: el auto-pull
trae `content/`, pero el código Python ya está importado en memoria.

## Desarrollo

```bash
uv sync --extra dev
uv run pytest                    # rápido, sin red
uvx ruff check . && uvx ruff format --check .
uv run python scripts/repaso.py  # 40 preguntas contra la API real
```

CI corre `ruff` y `pytest` en cada PR.

`scripts/repaso.py` **gasta dinero de verdad** (~1 $ por pasada). No lo metas
en CI.

Conventional Commits con scope. Antes de tocar la lógica de coste
(`budget.py`, el agrupado de mensajes en `bot.py`) leé el incidente de los dos
euros en `docs/NOTES.md`: la concurrencia rompe la economía de la caché y no se ve
venir.

**Nunca commitees secrets.** `.env` y `.env.qa` están ignorados y hay gitleaks
en pre-commit:

```bash
pre-commit install && pre-commit install --hook-type commit-msg
```
