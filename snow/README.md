# Snow

Self-hosted home assistant brain. Thin client + server-side tools + Home Assistant.

```
Client (text / on-device STT)
        │
        ▼
   Snow API  ── OpenRouter (one model)
        │
        └── Home Assistant
```

## Quick start (personal lab)

```bash
cp personal/env.example .env
# edit .env + personal/devices.yaml
docker compose up -d --build
# open http://SERVER_IP:8787
```

See **`personal/RUNBOOK.md`** for full Acer + HA steps (including Wi‑Fi notes).

## Stack

- **API** FastAPI `/api/v1/*` — chat, home summary, health, sessions  
- **Storage** SQLite sessions + audit  
- **Tools** lights, switches, scenes, weather, home summary, aliases  
- **Fallback** Turkish rule engine if OpenRouter fails  
- **UI** mobile Snow shell, home panel, PWA manifest  

## Docs

- [Setup](docs/setup.md)  
- [Architecture](docs/architecture.md)  
- [Roadmap](docs/roadmap.md)  
- [Personal runbook](personal/RUNBOOK.md)  

## License

MIT
