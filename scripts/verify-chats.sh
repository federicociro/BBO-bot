#!/usr/bin/env bash
# Confirma que los chat ids del .env son los que espera la Bot API.
# Hay que añadir el bot a los tres chats antes: si no, da "chat not found".
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
set -a && source .env && set +a

for var in BBO_MAIN_CHAT_ID BBO_ADMIN_CHAT_ID BBO_CHANNEL_ID; do
  id="${!var}"
  printf '%-20s %-16s ' "$var" "$id"
  curl -s "https://api.telegram.org/bot${BBO_TELEGRAM_TOKEN}/getChat?chat_id=${id}" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d.get("result",{}); print(f"OK {r.get(\"type\")} · {r.get(\"title\")}" if d.get("ok") else f"FALLA · {d.get(\"description\")}")'
done
