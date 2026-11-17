# MA TRẬN TRUY VẾT YÊU CẦU

**Cập nhật:** 17/11/2026

## 1. Use case → yêu cầu → implementation → kiểm thử

| Use case | Yêu cầu | Implementation chính | Kiểm thử | Trạng thái |
|---|---|---|---|---|
| UC-01 | FR-AUTH-01..05, FR-USER-02 | `auth_service.py`, `core/security.py`, `api/deps.py`, `lib/api/client.ts` | `test_auth.py`, `test_tokens.py` (rotation, reuse, đổi mật khẩu, loại token) | Covered |
| UC-02 | FR-PROJ-01..05 | `project_service.py`, `access_policy.py` | `test_projects.py` (leo thang qua liên kết, danh sách theo quyền) | Covered |
| UC-03 | FR-MTG-01, FR-AUD-01..06, FR-AI-01..07, FR-PROC-01..04 | `audio_service.py`, `processing/pipeline.py`, `processing/jobs.py`, `processing/outbox.py`, `audio_probe.py`, `workers/*`, `gladia.py` | `test_uploads.py`, `test_processing.py`, `test_outbox.py`, `test_audio_probe.py`, `test_worker_container.py`, `test_ai_client.py`, ai-service `test_gladia_pipeline.py`, `test_routers.py` | Covered |
| UC-04 | FR-TR-01..07, FR-REV-01..03 | `transcript_editor.py`, `transcript_ops.py`, `event_bus.py`, `processing/handlers.py` | `test_transcript_ops.py`, `test_transcript_editor.py`, `test_transcript_api.py` | Covered |
| UC-05 | FR-SUM-01..05 | `summary_service.py`, `processing/commands.py`, `processing/pipeline.py` | `test_processing.py`, `test_transcript_api.py`, ai-service `test_summary_generator.py` | Covered |
| UC-06 | FR-RAG-01..06, FR-AGENT-01..08 | `retrieval_service.py`, `chat_service.py`, `assistant_service.py`, `agent_actions.py`, `agent_tools.py`, `api/internal_deps.py`, ai-service `app/agent/*`, `AssistantPane.tsx`, `ProposalCard.tsx` | `test_chat.py`, `test_retrieval.py` (PostgreSQL), `test_agent_internal_api.py`, `test_agent_actions.py`, `test_assistant_turns.py` (E2E, injection), ai-service `test_agent_tools.py`, `test_agent_graph.py`, `test_agent_router.py`, frontend `assistant-events.test.ts`, `proposal-edits.test.ts` | Covered |
| UC-07 | FR-EXP-01..02 | `export/` (registry, loader, renderers) | `test_exports.py` | Covered |
| UC-08 | FR-SHARE-01..03 | `access_policy.py`, `api/deps.py`, `lib/share-token.tsx` | `test_authorization.py` (26 route × 7 vai trò) | Covered |
| UC-09 | FR-PLAN-01..02, FR-PLAN-06..07 | `billing/plan_service.py`, `billing/subscription_service.py`, `billing/quota_service.py` | `test_billing.py`, `test_uploads.py` (402 khi hết quota) | Covered |
| UC-10 | FR-PLAN-03..05, FR-PLAN-08 | `billing/payment_service.py`, `VietQRModal.tsx` | `test_payments.py`, `test_payments_concurrency.py` (PostgreSQL) | Covered |
| UC-11 | FR-REV-01..03, FR-AGENT-04 | `transcript_editor.py`, `ChangeHistoryDrawer.tsx`, `UndoToast.tsx` | `test_transcript_editor.py`, `test_agent_actions.py` (duyệt rồi hoàn tác) | Covered |
| UC-12 | FR-AGENT-05 | `artifact_service.py`, `export/markdown_docx.py`, `ArtifactsPanel.tsx` | `test_artifacts.py` | Covered |
| UC-S01 | FR-REC-01..02 | `/live/page.tsx`, audio upload | Chưa có browser E2E | Gap |
| UC-S02 | FR-USER-01..02 | `users.py`, `user_service.py`, profile page | `test_tokens.py` (đổi mật khẩu) | Partial |

## 2. Yêu cầu chưa hoàn chỉnh

| ID | Khoảng trống | Việc cần làm |
|---|---|---|
| FR-REC-03 | Không có live transcript thật | Tích hợp streaming ASR (Gladia live) như một use case riêng |
| FR-SHARE-04 | Không revoke/expire link | Thêm expiry/revocation và audit log truy cập |
| NFR-SEC-05 | Token trình duyệt trong `localStorage` | Chuyển sang cookie HttpOnly kèm chiến lược CSRF |
| Browser E2E | Chưa có Playwright cho luồng UI | Thêm kịch bản upload → trợ lý → duyệt → hoàn tác |

## 3. Kiểm thử bắt buộc trước deploy

| Kiểm thử | Lệnh/Phương pháp | Tiêu chí |
|---|---|---|
| Backend (PostgreSQL) | `TEST_DATABASE_URL=... pytest tests -q` trong `backend-api` | 0 failed, 0 skipped |
| Migration | `alembic upgrade head && alembic check` | Không có khác biệt so với model |
| AI service | `AGENT_TEST_PG_URL=... pytest -q` trong `ai-service` | 0 failed |
| Lint/type | `ruff check .`; `mypy --strict --follow-imports=silent app/domain app/services/access_policy.py` | exit 0 |
| Frontend | `npm run lint && npm run typecheck && npm test && npm run build` | exit 0 |
| Compose syntax | `docker compose ... config` | exit 0 với `.env` hợp lệ |
| Container health | `docker compose -f docker-compose.prod.yml ps` | tất cả service có healthcheck là healthy |
| E2E thật | Checklist trong runbook | transcript/summary phản ánh đúng audio, không dữ liệu giả |

## 4. Tài liệu liên quan

- [SRS](srs.md)
- [Use cases](use-cases.md)
- [Test plan](../05-testing/test-plan.md)
- [Runbook E2E và EC2](../deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md)
