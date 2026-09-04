FROM python:3.13-slim

# git para que /recargar y el auto-pull funcionen dentro del contenedor
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 bbo

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && rm -rf /root/.cache

COPY bbo_bot/ ./bbo_bot/

# El material NO se hornea en la imagen: se monta content/ desde el checkout de
# git, para que editar el canon llegue a Roser sin reconstruir nada. Ver #2.
VOLUME ["/app/content"]

USER bbo
CMD ["python", "-m", "bbo_bot"]
