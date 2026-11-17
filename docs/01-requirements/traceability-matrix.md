# MA TRẬN TRUY VẾT YÊU CẦU

**Cập nhật:** 16/11/2026

## 1. Use case → yêu cầu → implementation → kiểm thử

| Use case | Yêu cầu | Implementation chính | Kiểm thử hiện có | Trạng thái |
|---|---|---|---|---|
| UC-01 | FR-AUTH-01..04 | `auth.py`, `auth_service.py`, `auth-context.tsx` | `test_auth.py` | Covered |
| UC-02 | FR-PROJ-01..05 | `projects.py`, `project_service.py`, `ProjectSelector.tsx` | Chưa có integration test riêng | Gap |
| UC-03 | FR-MTG-01, FR-AUD-01..05, FR-AI-01..05 | `audio_service.py`, `processing/pipeline.py`, `workers/tasks.py`, `gladia.py` | `test_gladia_pipeline.py`, `test_routers.py` | Partial |
| UC-04 | FR-TR-01..05 | `transcripts.py`, `transcript_service.py`, `TranscriptFeed.tsx` | Chưa có API regression test | Gap |
| UC-05 | FR-SUM-01..04 | `summaries.py`, `generator.py`, `processing/pipeline.py`, `workers/tasks.py` | `test_summary_generator.py`, `test_routers.py` | Partial |
| UC-06 | FR-RAG-01..04 | `chat_service.py`, `retriever.py`, `AssistantChatPane.tsx` | `test_chat.py`, `test_retriever.py`, `test_rag_generator.py` | Covered |
| UC-07 | FR-EXP-01..02 | `export_service.py`, `ExportDropdown.tsx` | `test_exports.py` | Covered |
| UC-08 | FR-SHARE-01..03 | `meeting_service.py`, meeting detail page | Chưa có share-token integration test | Gap |
| UC-09 | FR-PLAN-01..02, FR-PLAN-06 | `plan_service.py`, `quota_service.py`, `QuotaBadge.tsx` | Payment test chỉ kiểm tra seed/checkout | Partial |
| UC-10 | FR-PLAN-03..05 | `payment_service.py`, `VietQRModal.tsx` | `test_payments.py` | Covered |
| UC-S01 | FR-REC-01..02 | `/live/page.tsx`, audio upload | Chưa có browser E2E | Gap |
| UC-S02 | FR-USER-01..02 | `users.py`, `user_service.py`, profile page | Chưa có test riêng | Gap |

## 2. Yêu cầu chưa hoàn chỉnh

| ID | Khoảng trống | Việc cần làm |
|---|---|---|
| FR-AUTH-05 | Frontend không tự refresh token | Thêm refresh/retry một lần và logout khi refresh thất bại |
| FR-AI-06 | Production vẫn có fallback demo | Tách `ALLOW_AI_FALLBACK`; production phải fail meeting rõ ràng |
| FR-REC-03 | Không có live transcript thật | Tích hợp streaming ASR hoặc bỏ WebSocket khỏi phạm vi |
| FR-TR-06 | Sửa transcript không làm mới summary/RAG | Thêm regenerate workflow và version dữ liệu |
| FR-RAG-05 | Không có persistent vector index | Lưu embedding/tsvector và cập nhật khi segment thay đổi |
| FR-SHARE-03 | Authorization tài nguyên con không đồng nhất | Gom kiểm tra meeting access thành dependency dùng chung |
| FR-SHARE-04 | Không revoke/expire link | Thêm expiry/revocation và audit log |
| FR-PLAN-06 | Chưa chặn upload khi hết quota | Gọi `QuotaService.assert_within_quota` tại upload boundary |

## 3. Kiểm thử bắt buộc trước deploy

| Kiểm thử | Lệnh/Phương pháp | Tiêu chí |
|---|---|---|
| Backend unit/integration | `pytest -q` trong `backend-api` | 0 failed |
| AI unit/integration | `pytest -q` trong `ai-service` | 0 failed |
| Frontend type/build | `pnpm run build` trong `frontend` | exit 0 |
| Compose syntax | `docker compose ... config` | exit 0 với `.env` hợp lệ |
| Container health | `docker compose -f docker-compose.prod.yml ps` | tất cả service có healthcheck là healthy |
| E2E thật | Checklist trong runbook | transcript/summary phản ánh đúng audio, không fallback |

## 4. Tài liệu liên quan

- [SRS](srs.md)
- [Use cases](use-cases.md)
- [Test plan](../05-testing/test-plan.md)
- [Runbook E2E và EC2](../deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md)
