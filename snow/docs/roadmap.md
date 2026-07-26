# Roadmap

The v0.1 light + weather tools are a **starting surface**, not the product limit.  
This file is a capability backlog: implement in any order that fits hardware you already expose through Home Assistant (or future adapters).

**Design rule:** New feature → **server tool first**. Clients only gain UI/UX; they never hold the brain.

---

## v0.1 — Talking spine ✅

- [x] Snow API + single OpenRouter model + tool loop  
- [x] HA lights + scenes + weather tool  
- [x] Mobile-first web bridge + on-device STT  
- [x] Identity QUERY/SET + profile validators  
- [x] Device rules (offline/fast actuators)  
- [ ] Hardened docs + first public release polish  

## v0.2 — Home awareness (partial)

- [x] Inventory of `light.*` / `switch.*` / `media_player.*` (live context)  
- [x] Friendly names in world context  
- [ ] Room / area grouping  
- [ ] Presence signals (optional)  
- [x] Command history / audit trail  
- [ ] Richer usage summaries UI  

## v0.3 — Routines & time ✅ (core)

- [x] Named macros (`personal/routines.yaml` → `run_routine`)  
- [x] Delayed actions (SQLite jobs + scheduler)  
- [x] Jobs API + Station cancel UI  
- [x] Routines API + Station run buttons  
- [ ] Time / sun-based suggestions (HA automations or event bus)  
- [ ] Natural-language “save this as a routine”  

## v0.4 — More actuators

- [x] TV / media_player via HA  
- [ ] Wake-on-LAN targets  
- [ ] Climate (HVAC, fans)  
- [ ] Covers (blinds, garage)  
- [ ] Binary sensors (“is the door open?”)  
- [ ] Locks with **confirm** policy  

## v0.5 — Media depth (optional)

- [x] Basic TV on/off/play/pause/volume  
- [ ] App deep-links when HA supports them  
- [ ] Music players (Spotify etc. — document active-device limits)  
- [ ] “Movie mode” as routine (already seed: `film_gecesi`)  

## v0.6 — Life admin

- [x] Profile name memory  
- [ ] Preference keys (`night_brightness`, locale)  
- [ ] Calendar (CalDAV / Nextcloud)  
- [ ] Lists & reminders  
- [ ] Optional external info tools with privacy notes  

## v0.7 — Security & network

- [x] Bearer token + rate limit  
- [ ] Remote access (VPN-first)  
- [ ] Scoped guest tokens  
- [ ] Homelab health questions  

## v0.8 — Personality & memory

- [x] Stable user name  
- [ ] Multi-user profiles  
- [ ] Explicit “don’t do that again” memory  
- [ ] Optional local embeddings (mind host RAM)  

## v0.9 — Productization

- [x] Thin Android WebView shell scaffold  
- [ ] Install wizard  
- [x] Tool bus packing (handlers + manifest + schemas)  
- [ ] Plugin/tool pack API  
- [ ] i18n prompt packs  

## v1.0 — “Home OS” feel

- [x] Station status + chat (not pure chatbot)  
- [ ] Confirmations for dangerous actions  
- [ ] Permissions by person / area  
- [ ] Operator runbooks (personal RUNBOOK exists)  
- [ ] Event-driven presence / HA WebSocket  

---

## Near-term engineering (internal)

| Phase | Focus |
|-------|--------|
| **A** | Tool handlers split, smoke tests, mutate cache ✅ in progress |
| **B** | Acer deploy verify, Station polish, profile prefs |
| **C** | Risk policy + new HA domains |
| **D** | HA WebSocket events + presence |
| **E** | Planner + confirmations |

---

## Resource honesty

Snow stays thin: orchestration + tools, not a GPU LLM host by default.  
Heavy local models or server-side ASR are out of scope unless the operator wants them.
