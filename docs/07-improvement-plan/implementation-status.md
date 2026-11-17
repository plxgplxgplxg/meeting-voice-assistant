# Implementation Status

Companion to [refactor-and-agent-roadmap.md](refactor-and-agent-roadmap.md). Updated 2026-11-17.

All five phases of the roadmap and the documentation updates of section 5 are implemented. The sections below record what was built, where the implementation deviates from the roadmap, and what is still open. Nothing from the second half of the work is committed yet: commit `2033c3c` holds Phase 1 and the first part of Phases 2 and 4; Phases 2 (rest), 3, 4 (rest), 5 and the docs are in the working tree.

## How to run the checks

```bash
# one-time: virtualenv at the repository root
python3 -m venv .venv && .venv/bin/pip install -r backend-api/requirements-dev.txt -r ai-service/requirements.txt

# backend (SQLite, fast)
cd backend-api && ../.venv/bin/python -m pytest tests -q

# backend on PostgreSQL (vector retrieval, row locks, payment concurrency)
TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/python -m pytest tests -q

# migrations
DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/alembic upgrade head
DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/alembic check

# lint and types
../.venv/bin/ruff check . && ../.venv/bin/mypy --strict --follow-imports=silent app/domain app/services/access_policy.py

# ai-service, including the PostgreSQL checkpointer test
cd ../ai-service && AGENT_TEST_PG_URL=postgresql://postgres@127.0.0.1:55432/meeting_test ../.venv/bin/python -m pytest -q

# frontend
cd ../frontend && npm run lint && npm run typecheck && npm test && npm run build

# regenerate the public API contract after changing endpoints
cd ../backend-api && ../.venv/bin/python scripts/export_openapi.py
```

A throwaway PostgreSQL 14 with pgvector can be started with Homebrew binaries:
`initdb -D /tmp/mva_pg -U postgres --auth=trust`, then
`pg_ctl -D /tmp/mva_pg -o "-p 55432 -k /tmp -c listen_addresses=127.0.0.1" start`, then `createdb -h 127.0.0.1 -p 55432 -U postgres meeting_test` and `CREATE EXTENSION vector`.

Last results (2026-11-17): backend 415 passed and 7 skipped on SQLite, 422 passed and 0 skipped on PostgreSQL 14; ai-service 75 passed with `AGENT_TEST_PG_URL`; frontend 12 unit tests passed; `alembic upgrade head` then `alembic check` clean; `ruff` clean in both Python services; `mypy --strict` clean; `next lint`, `tsc --noEmit` and `next build` clean; `docker compose config` accepted for both Compose files. Not run: Docker image builds (no Docker daemon was available) and any test against real Gladia, Gemini or OpenAI.

## Phase 1: Security and correctness

| Task | Status | Notes |
|---|---|---|
| T1.1 Domain errors, one error format | Done | `core/errors.py`, `api/error_handlers.py`. Services contain no `HTTPException`. `DomainError.commit_changes` lets a failure persist its side effects (revoked token family, failed AI call record, expired proposal) because `get_db_session` otherwise rolls back. |
| T1.2 Shared dependencies | Done | `api/deps.py`. `get_current_user` returns `UserModel` and rejects refresh and agent tokens used as access tokens. |
| T1.3 MeetingAccessPolicy | Done | `services/access_policy.py`, `domain/enums.py`, `domain/actor.py`. Highest granted permission wins. `Actor` carries `via` (`user`, `share`, `agent`). |
| T1.4 Apply policy to all routes | Done | Nested `/meetings/{id}/...` routes plus deprecated aliases on the old paths. `tests/test_authorization.py` covers the route matrix by 7 roles, extended with the transcript-history, proposal and artifact routes. `GET /meetings/{id}/export` removed. |
| T1.5 Authentication for creation | Done | Create, list and both upload routes require a user. |
| T1.6 Project linking | Done | Requires EDIT on the meeting. |
| T1.7 Payments hardening | Done | Money is `Numeric(12,2)`. Event insert is the idempotency gate, order row is locked. PostgreSQL concurrency test included. |
| T1.8 Subscription and quota | Done | Plans are `free/pro/business`. History rows, lazy Free rollover, 402 at upload, export format gating by the meeting owner's plan. Quota is charged once per audio file from the probed duration. |
| T1.9 No fake AI output | Done | Mock engine only with `ENVIRONMENT=development` and `AUDIO_PIPELINE_ENGINE=mock`, flagged `is_demo`. |
| T1.10 Configuration and deploy | Done | Production validators in both services, `AI_SERVICE_TOKEN`, loopback-only ports in dev, docs and OpenAPI off in production, nginx blocks `/internal/`. |
| T1.11 Token hygiene | Done | `token_version`, refresh rotation with reuse detection, single-flight refresh. HttpOnly cookies not done (optional in the roadmap). |
| T1.12 Upload validation | Done | Streaming size limit with cleanup, id-based storage keys, containment check, header sniffing, `ffprobe` duration and codec validation. |

## Phase 2: Processing pipeline

| Task | Status | Notes |
|---|---|---|
| T2.1 State machine | Done | `services/processing/state.py`. Invalid transitions raise a 409. |
| T2.2 Job table, outbox, retries | Done | `processing_jobs`, `outbox_events`, `dispatch_outbox` on a 2 s beat with `SKIP LOCKED`. Retry counter and backoff live in the job row (`job_max_attempts=3`, exponential). Steps are idempotent. |
| T2.3 Split the worker | Done | `transcribe`, `summarize` and `index` are separate job kinds driven by `run_processing_job`; `TranscriptReplaced` enqueues summarize and index independently. Per-process event loop and engine disposal kept. |
| T2.4 Audio probe | Done | `services/audio_probe.py` (`ffprobe`), injected so tests use a fake; Dockerfile installs `ffmpeg`. |
| T2.5 AI audio contract | Done | `POST /audio/transcribe` submits and returns a `provider_job_id`; `GET /audio/transcribe/{id}` polls. The worker polls through Celery retry, not a blocking loop. |
| T2.6 pgvector hybrid retrieval | Done | `transcript_chunks` with `vector(384)` + HNSW and `tsvector` + GIN; one SQL statement fuses both ranks (RRF), filtered by meeting. Chunking moved from ai-service to `backend-api/app/services/chunking.py`; ai-service only embeds. |
| T2.7 Dead code | Done | `asr.py`, `diarization.py`, `live_ws.py`, `passlib` removed; `vad.py` moved to `ai-service/research/`; the old in-memory retriever was deleted. |

## Phase 3: Transcript editing as a command module

| Task | Status | Notes |
|---|---|---|
| T3.1 Revisions and optimistic concurrency | Done | `meetings.transcript_revision`, `transcript_segments.version`, `transcript_change_sets`, `transcript_segment_changes` (migration 0003). Stale `expected_revision` returns 409 `TRANSCRIPT_REVISION_CONFLICT`. |
| T3.2 TranscriptEditor | Done | `apply`, `preview`, `revert` with a row lock, seven operations (update text, replace text, rename speaker, reassign speaker, delete, split, merge), a pure `TranscriptPlanner`, and a unique-order parking step so split, merge and delete never violate `UNIQUE (meeting_id, sequence_order)`. New endpoints: `operations`, `operations:preview`, `change-sets`, `change-sets/{id}`, `change-sets/{id}/revert`. Old segment, rename and delete endpoints call the same editor. |
| T3.3 Event handlers | Done | `EventBus` (sync, same transaction). `TranscriptEdited`: summary and index to `stale`, debounced `index` job keyed by revision. `TranscriptReplaced`: pending summary and index. `POST /meetings/{id}/summary:regenerate` and `.../reindex` exist; the UI shows an outdated-summary banner with a regenerate button. |

## Phase 4: Quality and frontend

| Task | Status | Notes |
|---|---|---|
| T4.1 Alembic | Done | Five revisions (`0001`..`0005`). Timestamps are `timestamptz` through the `UTCDateTime` type (migration 0004); SQLite tests get tz-aware values too. |
| T4.2 Export registry | Done | `services/export/` with `registry.py`, `MeetingDocumentLoader`, one renderer per format (DOCX, TXT, SRT, VTT, JSON). Chat, export and agent tools reuse the loader. |
| T4.3 AIServiceClient | Done | Protocol plus HTTP adapter; forwards `X-Service-Token` and `X-Request-ID`; maps provider failures to `AIUnavailableError` with a `retryable` flag. |
| T4.4 Transaction ownership | Done | Only `get_db_session`, the worker runner, the startup seed and `AssistantService` (deliberately, before opening the SSE stream) commit. |
| T4.5 Logging | Done except tracing | structlog JSON renderer, `request_id` bound in both services and propagated from backend to ai-service through `X-Request-ID`, `user_id` bound in the backend, latency and token usage logged per LLM call. Langfuse tracing (optional) not added. |
| T4.6 ai-service DI | Done | Lifespan builds the HTTP client, embedder and agent runner; routers use `Depends` providers. |
| T4.7 Frontend | Done | `@tanstack/react-query`, typed API modules in `src/lib/api/`, hooks (`useMeeting`, `useTranscript`, `useTranscriptOperations`, `useSummary`, `useAssistant`, `useAgentActions`, `useChangeSets`, `useArtifacts`, ...), the meeting page split into `MeetingHeader`, `MeetingWorkspace`, `SummaryPanel`, `ActionItemsPanel`, `ShareDialog`, share token context, signed audio URL, polling that stops on `ready`/`failed` with failure reason and retry. `openapi-typescript` generation (optional) not used; DTOs are hand-written in `src/types/api.ts`. |
| T4.8 CI | Done | Backend on a PostgreSQL service with `alembic upgrade head` and `alembic check`; ai-service with PostgreSQL and LangGraph dependencies; `ruff`; `mypy --strict` on the two typed areas; frontend on Node 22 with `lint`, `typecheck`, `test`, `build`. |

## Phase 5: Meeting Assistant agent

| Task | Status | Notes |
|---|---|---|
| 5.1 Use-case changes | Done | UC-06 rewritten, UC-11 (history and undo) and UC-12 (documents) added in `use-cases.md`. |
| 5.3 Data model | Done | `agent_conversations`, `agent_messages`, `agent_actions`, `meeting_artifacts` (migration 0005). The old `chat_sessions` and `chat_messages` were migrated into them (the downgrade copies back). |
| 5.4 Backend tool API | Done | `/internal/agent/v1` with seven routes (overview, search, segments, find, summary, propose, artifacts), excluded from OpenAPI, blocked at nginx. Needs `X-Service-Token` plus a delegated JWT (`aud=agent`, 5 minutes, `scope=meeting:{id}`, `conv`, `tv`). |
| 5.5 ai-service agent | Done | LangGraph agent with nine tools (five read, three proposal, one artifact), recursion limit 8, `AsyncPostgresSaver` in schema `langgraph`, SSE endpoint `POST /agent/turn`, transcript text wrapped in `<transcript>` as untrusted data. |
| 5.6 Frontend | Done | `AssistantPane` (SSE through `fetch`), `ProposalCard` with editable operations, `ChangeHistoryDrawer`, `UndoToast`, `ArtifactsPanel`. |
| 5.7 Acceptance tests | Done with a caveat | Authorization of every tool, scope and expiry, proposal approve, reject, stale and expiry, revert of an agent edit, plan gating, hijacked agent, end-to-end rename then reindex then DOCX (`test_assistant_turns.py`). The agent in these tests is scripted: model behaviour (choosing tools, resisting injection) is **not** verified against a real LLM. |

## Deviations from the roadmap

- Proposal expiry (30 minutes) is a constant in `agent_actions.py` compared against `created_at`; there is no `expires_at` column.
- A proposal is also rejected as stale when the transcript revision moved, not only when it is old (`PROPOSAL_STALE` versus `PROPOSAL_EXPIRED`).
- `AssistantService` commits the user message before streaming because the agent calls back into the API through other requests.
- Free-plan users and share-link guests use the same `POST /meetings/{id}/assistant/turns` endpoint and get plain cited Q&A (events `token`, `citation`, `done`); the older `POST /meetings/{id}/chat` still works.
- Roadmap section 6 items not built: `share_expires_at` and share revocation, `assignee_user_id` on action items, versioned summaries (`is_current`), a daily beat task for subscription expiry (rollover stays lazy), the cross-meeting `search_project` tool.

## Known gaps and risks

- Real model behaviour is unverified: no test used live Gemini, OpenAI or Gladia. Tool selection quality, prompt-injection resistance and cost per assistant turn need an evaluation with real keys.
- LLM model names are fixed per provider in code (`gemini-2.0-flash`, `gpt-4o-mini`); they should come from the environment.
- ai-service `requirements.txt` still uses `>=` ranges; backend dependencies are pinned to tested versions.
- No browser end-to-end test (Playwright) and no Docker image build was run in this environment.
- No rate limiting, no dead-letter queue, no audit log for reads, tokens still in `localStorage`.
- Deleting a meeting is a soft delete and keeps audio, chunks, conversations and checkpoints.
- Operational note: during this work a `ruff check . --fix` was started from the home directory by mistake and stopped within seconds. Scans for recently modified Python and notebook files in the home subfolders found nothing changed, but the scan of `Downloads` did not finish; a manual look at recently touched files outside this repository is advisable.

## Behaviour changes to be aware of

- Existing development databases created by `create_all` lack new columns. Recreate them (`docker compose down -v`) or run `alembic upgrade head` on an empty database.
- Anonymous meeting creation, listing and uploading no longer exist. Guests only act through share links.
- Share editors without an account cannot upload (upload requires a user) and cannot use agent tools.
- The signed audio URL lasts 10 minutes. On a playback error the page fetches a new URL.
- Export format availability follows the plan of the meeting owner, not of the person downloading.
- `POST /users/me/change-password` returns a fresh token pair; the previous tokens stop working immediately.
- The WebSocket endpoint and its nginx upgrade configuration were removed.
- Chat history now lives in `agent_conversations` and `agent_messages`.
- The production stack has two more processes: `celery-beat` and the PostgreSQL schema `langgraph` used by the agent checkpointer (`AGENT_CHECKPOINT_DB_URL`).

## Documentation

Updated in Vietnamese per roadmap section 5: `01-requirements/{prd,srs,use-cases,traceability-matrix}.md`, `03-architecture/{system-architecture,sequence-diagrams,security-threat-model,api-first-architecture}.md`, `04-design/{database-erd,api-communication-guide}.md`, `04-design/api-specification.yaml` (generated from the application, checked by `test_openapi_contract.py`), `05-testing/test-plan.md`, `06-thesis-report/chapter-3-system-analysis-design.md`, `chapter-4-implementation.md`, and `README.md`.

Thesis chapters 1, 2 and 5 were not touched; chapter 5 still needs measured results (WER, DER, citation quality, latency, cost) instead of targets.
