# Deploy en LXC

Un proceso Python que hace long polling. No necesita puertos abiertos, ni
reverse proxy, ni certificados. Un LXC de 512 MB sobra.

## Instalación

```bash
adduser --system --group --home /opt/roser roser
apt install -y git python3 curl
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/federicociro/BBO-bot.git /opt/roser
cd /opt/roser && uv sync
cp .env.example .env && chmod 600 .env    # y rellenarlo
chown -R roser:roser /opt/roser

cp deploy/roser.service /etc/systemd/system/
systemctl enable --now roser
journalctl -u roser -f
```

## Que el canon se actualice solo

El checkout de `/opt/roser` **es** la fuente del canon (`content/`). Con esto en `.env`:

```
BBO_GIT_PULL=1
BBO_AUTO_PULL_MIN=15
```

Roser hace `git pull --ff-only` cada 15 minutos y, si el canon cambió, lo
recarga sola y avisa por privado. Un admin edita `canon.md` desde la web de
GitHub, mergeáis, y en un cuarto de hora está en vivo sin que nadie entre al
servidor. `/recargar` sigue estando para cuando no quieras esperar.

Repo público por HTTPS: el usuario `roser` no necesita llaves para el pull.

## Comprobaciones tras arrancar

```
journalctl -u roser | grep -E "destino de escalados|auto-pull"
```

Si dice `NO SE LLEGA AL DESTINO DE ESCALADOS`, los avisos no llegarán: añadí la
bot al chat y comprobá el id con `/chatid` desde dentro.
