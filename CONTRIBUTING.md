# Cómo colaborar

Lo que más falta no es código: es **canon**. Si contestás las mismas preguntas
una y otra vez en el grupo, esa respuesta debería estar acá.

## Editar lo que dice Roser

| Querés cambiar | Editás |
|---|---|
| Qué responde a una pregunta concreta | `canon.md` |
| Las reglas del grupo | `reglas.md` |
| Su carácter, sus límites, cuándo escala | `bbo_bot/persona.py` |
| Los textos fundacionales | `corpus/` |

**No hace falta saber programar para tocar `canon.md` ni `reglas.md`.** Se
editan desde la web de GitHub: botón del lápiz, escribís, "Propose changes".

### Cómo se escribe una entrada del canon

````markdown
### ¿La pregunta, tal como la hace la gente?
La respuesta en la voz de Roser: directa, 3-4 frases, con posición.
````

Reglas de la casa:

- **No es un FAQ que se copia y pega.** Es a la vez el contenido correcto y el
  ejemplo de tono: Roser lo adapta a cómo venga formulada la pregunta.
- **Escribilo como hablás en el grupo**, no como un manual. Si suena a folleto
  de banco, está mal.
- **Con posición.** "Hay opiniones para todos los gustos" no es una respuesta.
- **Nada de consejo financiero**: sin precios objetivo, sin predicciones.
- Si la respuesta correcta es "esto lo mira un humano", escribí `→ **escala**`.
- `[[?]]` marca lo que todavía no está decidido. Roser dice que no está
  definido en lugar de inventárselo.

## Que Roser se entere

El canon se lee al arrancar. Después de mergear:

```
/recargar    # en el log de admins, o por privado del dueño
```

Relee todo en caliente. La siguiente pregunta reescribe la caché del prompt
(unos céntimos); las de después vuelven a leerla.

## Código

```bash
uv sync --extra dev
uv run pytest
```

Conventional Commits con scope. Antes de tocar la lógica de escalado o el
presupuesto, leé `SPEC.md` en el vault: son las dos cosas que, si fallan,
fallan caro.

**Nunca commitees secrets.** `.env` y `.env.qa` están en `.gitignore` y hay
gitleaks en pre-commit:

```bash
pre-commit install && pre-commit install --hook-type commit-msg
```
