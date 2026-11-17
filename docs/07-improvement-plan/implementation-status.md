# Implementation Status

Companion to [refactor-and-agent-roadmap.md](refactor-and-agent-roadmap.md). Updated 2026-11-16.

Phase 1 (security and correctness) is complete. Parts of Phases 2 and 4 are done because Phase 1 depended on them. Phase 3 and Phase 5 are not started.

## How to run the checks

```bash
# one-time: virtualenv at the repository root
python3 -m venv .venv && .venv/bin/pip install -r backend-api/requirements-dev.txt numpy pytest-mock

# backend (SQLite, fast)
cd backend-api && ../.venv/bin/python -m pytest tests -q

# backend on PostgreSQL (needed for row-lock tests in test_payments_concurrency.py)
TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/python -m pytest tests -q

# migrations
DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/alembic upgrade head
DATABASE_URL=... ../.venv/bin/alembic check

# lint and types
../.venv/bin/ruff check . && ../.venv/bin/mypy --strict --follow-imports=silent app/domain app/services/access_policy.py

# ai-service and frontend
cd ../ai-service && ../.venv/bin/python -m pytest -q
cd ../frontend && npm run typecheck && npm run lint
```

A throwaway PostgreSQL 14 with pgvector can be started with Homebrew binaries:
`initdb -D /tmp/mva_pg -U postgres --auth=trust`, then
`pg_ctl -D /tmp/mva_pg -o "-p 55432 -k /tmp -c listen_addresses=127.0.0.1" start`.

Last results: backend 286 passed on SQLite (2 PostgreSQL-only tests skipped) and 288 passed on PostgreSQL 14, ai-service 34 passed, `alembic check` clean, `tsc --noEmit` clean, `ruff` clean in both Python services.

## Phase 1: Security and correctness

| Task | Status | Notes |
|---|---|---|
| T1.1 Domain errors, one error format | Done | `core/errors.py`, `api/error_handlers.py`. Services contain no `HTTPException`. `DomainError.commit_changes` lets a failure persist its side effects (revoked token family, failed AI call record) because `get_db_session` otherwise rolls back. |
| T1.2 Shared dependencies | Done | `api/deps.py`. `get_current_user` returns `UserModel` and now rejects refresh tokens used as access tokens. `deps.py` still runs the user lookup query. |
| T1.3 MeetingAccessPolicy | Done | `services/access_policy.py`, `domain/enums.py`, `domain/actor.py`. Highest granted permission wins. |
| T1.4 Apply policy to all routes | Done | Nested `/meetings/{id}/...` routes plus deprecated aliases on the old paths. `tests/test_authorization.py` covers 26 routes by 7 roles. `GET /meetings/{id}/export` removed. |
| T1.5 Authentication for creation | Done | Create, list and both upload routes require a user. |
| T1.6 Project linking | Done | Requires EDIT on the meeting. |
| T1.7 Payments hardening | Done | Money is `Numeric(12,2)`. Event insert is the idempotency gate, order row is locked. PostgreSQL concurrency test included. |
| T1.8 Subscription and quota | Done, one item open | Plans are `free/pro/business` (legacy `unlimited` is renamed on seed). History rows, lazy Free rollover, 402 at upload, export format gating by the meeting owner's plan. **Open:** quota is charged from the last segment end until ffprobe duration (T2.4) exists. |
| T1.9 No fake AI output | Done | Backend pipeline, chat, ai-service Gladia, generator, embeddings. Mock engine only with `ENVIRONMENT=development` and `AUDIO_PIPELINE_ENGINE=mock`, flagged `is_demo`. UI shows a "Dữ Liệu Mẫu" badge. |
| T1.10 Configuration and deploy | Done | Production validator for secrets and wildcard CORS in both services, `AI_SERVICE_TOKEN`, ports bound to loopback in dev and not published in prod, docs and OpenAPI off in production, nginx live-ws and docs blocks removed. |
| T1.11 Token hygiene | Done | `token_version`, refresh rotation with reuse detection, generic 401 text, single-flight refresh in the frontend. HttpOnly cookies not done (listed as optional). |
| T1.12 Upload validation | Done, one item open | Streaming size limit with cleanup, id-based storage keys, containment check, header sniffing. **Open:** ffprobe-based validation (T2.4). |

## Phase 2: Processing pipeline

| Task | Status | Notes |
|---|---|---|
| T2.1 State machine | Done | `services/processing/state.py`. The `recording` state was dropped together with the live WebSocket. Frontend polls until `ready` or `failed` and offers Retry (`POST /meetings/{id}/reprocess`). |
| T2.2 Job table, outbox, retries | **Not done** | Interim: dispatch happens in an `after_commit` hook and the in-process `asyncio.create_task` fallback is removed. There is no `processing_jobs` table, no outbox, no autoretry or backoff. Redis being down at commit time loses the dispatch. |
| T2.3 Split the worker | Partly | `MeetingProcessingPipeline` with injected AI client, quota service and session, unit-tested without Celery. One Celery task runs the stages sequentially. Per-process event loop and engine disposal are in place. No parallel summarize and index steps. |
| T2.4 Audio probe | **Not done** | |
| T2.5 AI audio contract | Partly | Route is `POST /audio/transcribe` with a storage key resolved inside `STORAGE_ROOT` (local file read closed). Still a single synchronous request. Timeouts are aligned (Gladia wait 1800 s, backend client 1860 s), not replaced by job polling. |
| T2.6 pgvector hybrid retrieval | **Not done** | Retrieval is still in-memory per question. The encode call now runs in a worker thread and the model loads once at startup. |
| T2.7 Dead code | Done | `asr.py`, `diarization.py`, `live_ws.py`, `passlib` removed; `vad.py` moved to `ai-service/research/`. |

## Phase 3 and Phase 5

Not started: transcript revisions, `TranscriptEditor`, domain events, agent tables, internal tool API, LangGraph agent, assistant UI.

## Phase 4: Quality and frontend

| Task | Status | Notes |
|---|---|---|
| T4.1 Alembic | Mostly | Baseline `0001_baseline` with indexes, unique constraints, CHECK constraints and a naming convention. `create_all` removed from startup and containers run `alembic upgrade head`. **Open:** timestamps are still naive UTC; the `timezone=True` switch was left out because SQLite tests return naive values. |
| T4.2 Export registry | Not done | `ExportService` still uses an `if/elif` chain. |
| T4.3 AIServiceClient | Done | `clients/ai_service_client.py`, Protocol plus HTTP adapter on the lifespan client, forwards `X-Service-Token`. `X-Request-ID` is not forwarded yet. |
| T4.4 Transaction ownership | Done | Only `get_db_session`, the worker runner and the startup seed commit. |
| T4.5 Logging | Partly | `request_id` is bound to structlog context vars. No JSON renderer, no `user_id`, no propagation to the AI service, no LLM latency or token logging. |
| T4.6 ai-service DI | Done | Lifespan creates the HTTP client and embedder. Routers use `Depends` providers in `app/deps.py`. |
| T4.7 Frontend | Partly | Done: error envelope parsing, single-flight refresh, share token on every meeting request, signed audio URL, status model, failure banner and retry, demo badge, nested routes on the meeting page, fixed broken profile and password calls. **Not done:** `@tanstack/react-query`, typed API modules and hooks, splitting `meetings/[id]/page.tsx`. |
| T4.8 CI | Done | Backend on a PostgreSQL service container with `alembic upgrade head` and `alembic check`, ai-service tests, `ruff`, `mypy --strict` on `app/domain` and `access_policy.py`, frontend lint without `|| true` and `tsc --noEmit`. Added `frontend/.eslintrc.json`; remaining ESLint output is 6 `exhaustive-deps` warnings and no errors. |

## Behaviour changes to be aware of

- Existing development databases created by `create_all` lack new columns. Recreate them (`docker compose down -v`) or run `alembic upgrade head` on an empty database.
- Anonymous meeting creation, listing and uploading no longer exist. Guests only act through share links.
- Share editors without an account cannot upload (upload requires a user).
- The signed audio URL lasts 10 minutes. On a playback error the page fetches a new URL, which restarts the audio element.
- Export format availability follows the plan of the meeting owner, not of the person downloading.
- `POST /users/me/change-password` now returns a fresh token pair; the previous tokens stop working immediately.
- ai-service `requirements.txt` is still unpinned. Backend dependencies are pinned to the tested versions (`requirements.txt`, `requirements-dev.txt`), and `bcrypt` is now listed explicitly because `passlib` was removed.

## Documentation

Updated: `04-design/api-communication-guide.md`, `04-design/database-erd.md`, `03-architecture/security-threat-model.md`, `01-requirements/traceability-matrix.md` (module names), `README.md`.

Still to update per roadmap section 5: `prd.md`, `srs.md`, `use-cases.md`, `system-architecture.md`, `sequence-diagrams.md`, `api-first-architecture.md`, `test-plan.md`, thesis chapters 3 and 4, and the regenerated OpenAPI file.
