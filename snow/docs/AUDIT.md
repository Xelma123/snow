# Snow code audit (debug sprint)

## Fixed in this pass

| Issue | Fix |
|-------|-----|
| SQLite lock risk | WAL + `busy_timeout=5000` + 30s connect timeout |
| Shared HTTP | `http_client.py` single `httpx.AsyncClient` for HA/weather |
| Weather false positive | Strict patterns (`hava nasıl/durumu`…) |
| Multi-intent | Split on `ve` / `and` / `&` |
| Delayed commands | SQLite `jobs` + background scheduler (~12s tick) |
| Name memory | `profile` table (`adım murat`) |
| TV surface | Station TV card + `media_control` + discovery log |
| Busy UX | RUN LED + full UI lock until reply |
| Dead assets | Removed unused `app.js` / `snow.css` |
| CORS | `allow_credentials=False` |
| Rate-limit map | Prune stale keys |
| entities API | Accepts `media_player` |
| Model | Locked `openai/gpt-oss-20b:free` (daily reliability) |

## Remaining / ops

- Set real `HA_DEFAULT_TV` / `devices.yaml` to your Android TV entity_id  
- Free 120B may rate-limit; rules still handle lights/TV/delay  
- Wi‑Fi server: DHCP reservation recommended  
