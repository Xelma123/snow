# Setup

## 1. Prerequisites

- Docker Engine + Compose plugin (or Podman compatible workflow)
- Home Assistant reachable over HTTP/HTTPS from the machine that runs Snow
- OpenRouter account + API key

No specific brand of PC, router, or bulb is required. Any device Home Assistant already controls can be a target once you point Snow at the right `entity_id`.

## 2. Configure secrets

```bash
cp .env.example .env
```

### `SNOW_APP_TOKEN`

Shared secret between the web UI / future apps and the API.

```bash
openssl rand -hex 24
```

### `OPENROUTER_API_KEY`

Create a key at [openrouter.ai/keys](https://openrouter.ai/keys).  
Snow uses a single fixed free-tier model (see `server/app/config.py`). Check current free quotas on OpenRouter.

### `HA_URL` + `HA_TOKEN`

1. Open Home Assistant in a browser.
2. Profile (user) → **Long-Lived Access Tokens** → create (`snow`).
3. Set `HA_URL` to the base URL Snow should call, for example:
   - `http://192.168.x.x:8123`
   - `http://homeassistant.local:8123`
   - `http://homeassistant:8123` (same Docker network)
4. Paste the token into `HA_TOKEN`.

### `HA_DEFAULT_LIGHT`

1. HA → **Developer tools → States**
2. Pick any `light.*` entity you want as default
3. Copy the full entity id into `HA_DEFAULT_LIGHT`

### Weather (optional)

Set `HOME_LAT` and `HOME_LON` to your location for the `get_weather` tool (Open-Meteo, no API key).

## 3. Run

```bash
docker compose up -d --build
docker compose logs -f snow
curl http://127.0.0.1:8787/api/health
```

Health JSON should show `ok: true` and ideally both OpenRouter and HA tokens configured.

## 4. Client

1. On any phone/tablet/PC on the network: `http://<snow-host>:8787`
2. Open ⚙ → set server URL if needed → paste `SNOW_APP_TOKEN`
3. Send a test command (e.g. turn the default light off)

Speech: microphone uses **on-device** browser STT when available; only the resulting text is POSTed to Snow.

## 5. Without Docker (dev)

```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# run from repo root so ../web resolves, or set paths accordingly
cd ..
set PYTHONPATH=server       # Windows PowerShell: $env:PYTHONPATH="server"
uvicorn app.main:app --app-dir server --host 0.0.0.0 --port 8787
```

(Adjust env loading so `.env` in repo root is found, or export variables.)

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| 401 / 403 | Client token ≠ `SNOW_APP_TOKEN` |
| OpenRouter errors | Key, quota, model availability |
| HA errors / 502 | `HA_URL` reachability from container, token, entity id |
| Light does nothing | Entity exists in HA; control it manually first |
| Container can’t reach HA | Don’t use `127.0.0.1` for HA on the host; use LAN IP or shared Docker network |

## Production tips

- Put Snow behind a reverse proxy (Caddy/Nginx) with TLS if exposed beyond LAN
- Prefer VPN for remote access instead of opening 8787 publicly
- Keep backups of `.env` offline; never commit it
