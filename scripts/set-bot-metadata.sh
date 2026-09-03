#!/usr/bin/env bash
# Nombre, biografía, descripción y comandos de Roser, en ES/CA/EN.
# El @usuario y la foto de perfil NO se pueden cambiar por API: eso es BotFather.
#   scripts/set-bot-metadata.sh <token> ["Nombre"]
set -euo pipefail
T="${1:?falta el token}"
NOMBRE="${2:-Roser · BBO}"
api() { curl -s "https://api.telegram.org/bot${T}/$1" -H 'Content-Type: application/json' -d "$2" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("  ok" if d.get("ok") else "  FALLA: "+str(d.get("description")))'; }

echo "nombre"
api setMyName "{\"name\": \"${NOMBRE}\"}"

echo "biografía (ES/CA/EN)"
api setMyShortDescription '{"short_description": "La voz de Barcelona Bitcoin Only. Pregunto poco, respondo bastante."}'
api setMyShortDescription '{"short_description": "La veu de Barcelona Bitcoin Only. Pregunto poc, responc força.", "language_code": "ca"}'
api setMyShortDescription '{"short_description": "The voice of Barcelona Bitcoin Only. Bitcoin-only, free software, privacy.", "language_code": "en"}'

echo "descripción (ES/CA/EN)"
api setMyDescription '{"description": "Soy Roser, la voz de Barcelona Bitcoin Only. Rose pone orden en el grupo; yo pongo contexto.\n\nPreguntame sobre Bitcoin, el manifiesto o la comunidad: ninguna duda es demasiado básica. Lo delicado —estafas, custodia, impuestos— lo mira un humano, no yo.\n\nBitcoin-only, software libre, privacidad. Sin consejo financiero."}'
api setMyDescription '{"description": "Sóc la Roser, la veu de Barcelona Bitcoin Only. La Rose posa ordre al grup; jo poso context.\n\nPregunta-m''\''hi sobre Bitcoin, el manifest o la comunitat: cap dubte és massa bàsic. El que és delicat —estafes, custòdia, impostos— ho mira una persona, no jo.\n\nBitcoin-only, programari lliure, privadesa. Sense consells financers.", "language_code": "ca"}'
api setMyDescription '{"description": "I am Roser, the voice of Barcelona Bitcoin Only. Rose keeps order in the group; I provide context.\n\nAsk me about Bitcoin, the manifesto or the community: no question is too basic. Anything delicate —scams, custody, taxes— is handled by a human, not me.\n\nBitcoin-only, free software, privacy. No financial advice.", "language_code": "en"}'

echo "comandos"
CMDS='[
  {"command":"meetup","description":"Próximo meetup de BBO"},
  {"command":"precio","description":"A cuánto está bitcoin"},
  {"command":"fees","description":"Fees recomendadas ahora"},
  {"command":"bloque","description":"Altura del último bloque"},
  {"command":"halving","description":"Cuánto falta para el halving"},
  {"command":"manifiesto","description":"El manifiesto de la comunidad"},
  {"command":"cita","description":"Un fragmento del manifiesto"},
  {"command":"reglas","description":"Las reglas del grupo"},
  {"command":"ayuda","description":"Qué sé hacer"}
]'
api setMyCommands "{\"commands\": ${CMDS}}"
