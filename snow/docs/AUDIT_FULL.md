# Snow Full Audit Report

**Date:** 2026-07  
**Scope:** Codebase + architecture (Acer homelab)  
**Skills applied:** structured-output, prompt-engineering, conversation-memory, fastapi-pro, docker-expert, voice-ai, android-dev, frontend-developer  

## Working core

- Pipeline: identity → multi → device-rules → LLM+tools → offline  
- Tool bus: handlers / schemas / manifest / executor  
- HA: light, media, switch, scene, weather, routines, jobs  
- Offline rules work without OpenRouter  
- Voice: push-to-talk; Android native TTS  
- Auth: Bearer + rate limit; SQLite WAL  

## Findings (priority)

| ID | Area | Severity | Issue | Mitigation (this refactor) |
|----|------|----------|--------|----------------------------|
| AI-1 | Tools | HIGH | Tool args not server-validated | `tools/validation.py` Pydantic |
| AI-2 | Prompt | MED | Weak security boundaries | Harden `prompts.py` |
| AI-3 | Memory | MED | Full history dump | Slim history + char budget |
| AI-6 | HTTP | LOW | New client per OpenRouter call | Shared httpx |
| BE-2 | Jobs | MED | No claim/lock | `claim_due` status=running |
| BE-4 | API | MED | No global errors / request-id | Middleware + handlers |
| BE-6/7 | Docker | MED | No HEALTHCHECK / limits | Dockerfile + compose |
| CL-1 | Voice | MED | Latency UX | Immediate feedback + chat timeout |

## Out of scope (Acer 8GB)

Celery/Redis, vector RAG, cloud STT/TTS mandate, multi-user RBAC, native Compose rewrite.

## Model

`openai/gpt-oss-20b:free` — free models: use **tool-calling** as structured path, not strict JSON schema mode.
