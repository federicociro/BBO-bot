FROM python:3.13-slim

RUN useradd -m -u 1000 bbo
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir . && rm -rf /root/.cache

COPY bbo_bot/ ./bbo_bot/
COPY corpus/ ./corpus/
COPY canon.md reglas.md ./

USER bbo
CMD ["python", "-m", "bbo_bot"]
