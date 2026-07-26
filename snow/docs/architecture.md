# Snow dynamic architecture (Jarvis core)

## Problem with static systems

Hard-coded phrase lists and greedy regex (“adım X”) look smart until:
- “adım ne” becomes name **Ne**
- “selam adım ne” overwrites Murat
- New slang/devices require code deploys

Snow targets a **dynamic** house OS: language model + **tools** + **live inventory** + **validators**.

## Pipeline

```
User text
   │
   ├─1─ Identity classifier (QUERY | SET | none)
   │       └─ profile_get / profile_set  [server validates names]
   │
   ├─2─ Device multi-intent (ve/and) if ALL segments are actuator-confident
   │
   ├─3─ Device fast-path (light/TV/weather/delay only)
   │
   └─4─ DEFAULT: LLM + tool calling
            + live HA inventory every turn (TTL cache ~20s)
            + profile in world context
            + tools: HA, weather, profile_* 
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| **Policy prompt** | How to behave; never invent devices |
| **World context** | Live lights/TV/switches from HA |
| **Tools** | Only way to mutate house or profile |
| **Validators** | `validate_display_name`, entity allowlists |
| **Device rules** | Optional low-latency actuators when AI is slow/down |
| **Audit + sessions** | SQLite truth trail |

## Identity contract

| Utterance | Kind | Action |
|-----------|------|--------|
| adım ne / ismim nedir | QUERY | `profile_get` only |
| benim adım Murat | SET | `profile_set` after validation |
| ne, kim, nedir | invalid name | rejected |

## Extension model (future Jarvis)

New capability = **new tool + schema + optional policy line**, not a new mega-regex file.
Examples: locks (confirm), presence events, energy, reminders bus.

## Tool bus (v1)

```
tools/
  manifest.py       # risk, mutate, domains + is_home_mutating
  schemas.py        # OpenRouter tool JSON
  executor.py       # ToolExecutor dispatch + cache invalidate on home-mutate
  context.py        # ToolContext (settings, ha, resolve helpers)
  handlers/         # one module per domain
    light.py media.py home.py weather.py profile.py jobs.py routines.py
  registry.py       # thin re-export + boot-time drift asserts
  routines.py       # YAML loader for personal/routines.yaml
```

- Metadata: `tools/manifest.py` (`risk`, `mutate`, `domains`)
- Schemas: `tools/schemas.py` — must match `TOOL_META` and `HANDLERS` (assert on import)
- Dispatch: `tools/executor.py` → `handlers/*`
- Public import: `tools/registry.py` (`ToolExecutor`, `openrouter_tools_schema`)
- Data-driven macros: `personal/routines.yaml` → `run_routine`
- Device fast-path only: `core/device_rules.py` (compat: `core/fallback.py`)
- Live context: home inventory + **pending jobs** + **routine list** (`core/context.py`)
- Home-mutating tools clear inventory cache automatically in the executor
- Jobs API: `GET/DELETE /api/v1/jobs`
- Routines API: `GET /api/v1/routines`, `POST /api/v1/routines/run`

### Adding a tool

1. `handlers/<domain>.py` — `async def run(ctx, args)`
2. Register in `handlers/__init__.py` `HANDLERS`
3. Schema entry in `schemas.py`
4. Meta row in `manifest.py`
5. Optional one line in `core/prompts.py`
6. `python scripts/smoke_manifest.py`

## Offline

If OpenRouter fails: device rules still open/close lights & TV; identity still works offline via classifier + SQLite.

## Structured tools

- OpenRouter **tool calling** (not free-form HA JSON).
- Server validates every tool payload via Pydantic (`tools/validation.py`) before handlers/HA.
- Free models: no reliance on `response_format.json_schema`.

## Memory (tiered, no vectors)

| Tier | Source |
|------|--------|
| Live | HA inventory TTL + jobs + routines (`context.py`) |
| Entity | `profile` allowlist (`user_name`, `locale`, …) |
| Short buffer | `get_history_for_llm` — last N msgs, char budget |

## Jobs

SQLite jobs with **claim** (`pending` → `running` → `done`/`failed`) every ~12s.

## Docker

- `HEALTHCHECK` + compose healthcheck  
- Soft `mem_limit` / `cpus` for Acer  
- `HA_URL`: LAN IP or `http://host.docker.internal:8123`  

## Voice (phone bridge)

```
Phone /voice (or Android WebView)
  User press → STT once → POST /api/v1/chat → TTS once → idle
```

- Push-to-talk only (no auto re-listen)  
- Android: native TTS (`SnowNative`); pause cancels STT/TTS  
- No audio upload to Acer  


