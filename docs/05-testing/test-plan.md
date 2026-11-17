# KẾ HOẠCH KIỂM THỬ

**Cập nhật:** 17/11/2026

## 1. Phạm vi

Kiểm thử auth, project, audio pipeline (job, outbox, retry), transcript editor (đồng thời, hoàn tác), truy xuất lai, trợ lý (công cụ, đề xuất, SSE, bảo mật), summary, export, tài liệu sinh ra, share, billing, frontend contracts và production Compose.

## 2. Tầng kiểm thử

| Tầng | Mục tiêu | Công cụ |
|---|---|---|
| Unit | Parser Gladia, chunking, planner thao tác transcript, state machine, renderer export, parser sự kiện SSE | pytest, Node test runner |
| API integration | Auth, chat, trợ lý, transcript, export, payment với DB SQLite test (nhanh) | pytest + httpx ASGITransport |
| API integration trên PostgreSQL | Truy xuất vector, khóa dòng, đồng thời thanh toán, checkpoint của agent, migration | pytest với `TEST_DATABASE_URL` / `AGENT_TEST_PG_URL` |
| Bảo mật | Ma trận quyền 7 vai trò, token ủy quyền, agent bị chiếm | pytest |
| Contract | Frontend path/payload khớp OpenAPI; file `api-specification.yaml` khớp ứng dụng | TypeScript build, `test_openapi_contract.py` |
| Container | Image build, health, volume/network | Docker Compose |
| E2E thật | Browser, queue, providers, DB, export/payment | Checklist thủ công có bằng chứng |
| AI evaluation | WER/DER/citation/faithfulness | Dataset có ground truth |

Test chạy trên SQLite bỏ qua các test cần PostgreSQL (đánh dấu rõ lý do). Tiêu chí phát hành là chạy lại **toàn bộ** trên PostgreSQL với 0 test bị bỏ qua.

## 3. Lệnh kiểm thử

```bash
# Backend, nhanh (SQLite)
cd /Users/plxg/workspace/meeting-voice-assistant/backend-api
python -m pytest tests -q

# Backend, đầy đủ (PostgreSQL có pgvector)
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_test python -m pytest tests -q

# Migration khớp model
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_test alembic upgrade head
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/meeting_test alembic check

# Lint và kiểu
ruff check .
mypy --strict --follow-imports=silent app/domain app/services/access_policy.py

# AI Service (kèm checkpoint PostgreSQL)
cd /Users/plxg/workspace/meeting-voice-assistant/ai-service
AGENT_TEST_PG_URL=postgresql://postgres:postgres@localhost:5432/meeting_test python -m pytest -q

# Frontend
cd /Users/plxg/workspace/meeting-voice-assistant/frontend
npm run lint && npm run typecheck && npm test && npm run build

# Compose
cd /Users/plxg/workspace/meeting-voice-assistant
docker compose config --quiet
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
```

Khi đổi API công khai, cập nhật contract: `python scripts/export_openapi.py` trong `backend-api`.

CI (`.github/workflows/ci.yml`) chạy: backend trên PostgreSQL service (kèm `alembic check`), ai-service với PostgreSQL và LangGraph, frontend (Node 22: lint, typecheck, test, build).

## 4. Kết quả lần chạy gần nhất (17/11/2026)

| Bộ test | Kết quả |
|---|---|
| Backend, SQLite | 415 đạt, 7 bỏ qua (cần PostgreSQL) |
| Backend, PostgreSQL | 422 đạt, 0 bỏ qua |
| AI Service, kèm checkpoint PostgreSQL | 75 đạt |
| Frontend (Node test) | 12 đạt |
| `ruff check` (backend, ai-service), `mypy --strict` (5 file), `alembic check`, `next lint`, `tsc`, `next build` | Không lỗi |

## 5. Bản đồ test theo năng lực

| Năng lực | Test chính |
|---|---|
| Phân quyền | `test_authorization.py` (ma trận route x vai trò), `test_projects.py`, `test_tokens.py` |
| Upload và xử lý | `test_uploads.py`, `test_processing.py`, `test_outbox.py`, `test_audio_probe.py`, `test_worker_container.py`, `test_ai_client.py` |
| Transcript | `test_transcript_ops.py` (planner), `test_transcript_editor.py` (đồng thời, hoàn tác, thứ tự), `test_transcript_api.py` |
| Truy xuất và hỏi đáp | `test_retrieval.py` (PostgreSQL), `test_chat.py` |
| Trợ lý | `test_agent_internal_api.py` (hai credential, scope, hết hạn), `test_agent_actions.py` (duyệt, lỗi thời, hết hạn, hoàn tác), `test_assistant_turns.py` (SSE, gói, E2E, injection), ai-service `test_agent_tools.py`, `test_agent_graph.py`, `test_agent_router.py` |
| Tài liệu sinh ra | `test_artifacts.py`, `test_exports.py` |
| Thanh toán | `test_payments.py`, `test_payments_concurrency.py` (PostgreSQL) |
| Quan sát | `test_logging.py`, ai-service `test_llm_logging.py` |
| Contract | `test_openapi_contract.py`, frontend `assistant-events.test.ts`, `proposal-edits.test.ts` |

## 6. Test case E2E bắt buộc

| ID | Kịch bản | Kết quả |
|---|---|---|
| E2E-01 | Register/login/profile/password | Phiên và dữ liệu đúng |
| E2E-02 | Tạo project, upload audio thật | Meeting liên kết project và chuyển `ready` |
| E2E-03 | Transcript edit/rename/delete/reload | Dữ liệu giữ sau reload; lịch sử ghi đúng người sửa |
| E2E-04 | Summary/action item | Nội dung xuất phát từ audio thật |
| E2E-05 | Hỏi đáp + citation seek | Trả lời grounded, seek đúng đoạn |
| E2E-06 | Export DOCX/JSON/SRT | File tải và mở được |
| E2E-07 | Share viewer incognito | Xem được; không sửa được; chỉ hỏi đáp có trích dẫn, không có công cụ của trợ lý |
| E2E-08 | VietQR + SePay webhook | Order completed, subscription đổi, webhook trùng idempotent |
| E2E-09 | Restart Compose | DB/audio còn, container healthy |
| E2E-10 | `/live` qua HTTPS | Browser cấp mic, WebM upload và xử lý batch |
| E2E-11 | Trợ lý: "đổi tên Speaker 1 thành An" | Thẻ đề xuất có diff; duyệt thì transcript đổi, tóm tắt/chỉ mục thành stale rồi tự dựng lại; hoàn tác trả về nguyên trạng |
| E2E-12 | Hai tab sửa cùng meeting | Tab sau nhận thông báo xung đột, không ghi đè |
| E2E-13 | Trợ lý soạn biên bản DOCX với tiêu đề tiếng Việt | Tải về được, mở được, tên file đúng |
| E2E-14 | Dừng Redis giữa lúc upload, bật lại | Job vẫn chạy (outbox) |
| E2E-15 | Gói Free hỏi trợ lý sửa transcript | Không có công cụ; hỏi đáp thuần hoạt động |
| E2E-16 | `curl https://<domain>/internal/agent/v1/...` | 404 từ Nginx |

E2E-11 đến E2E-16 chưa được thực hiện trên môi trường thật; mô phỏng tự động tương ứng nằm trong `test_assistant_turns.py` và `test_outbox.py`.

## 7. Phân biệt smoke và E2E AI

- `AUDIO_PIPELINE_ENGINE=mock` hoặc key rỗng: chỉ smoke infrastructure (và chỉ được ở môi trường development).
- Full E2E: key thật, audio fixture biết trước nội dung, transcript không chứa câu từ adapter giả lập.
- Trợ lý trong test dùng agent giả lập có kịch bản; hành vi của mô hình thật (chọn công cụ đúng, kháng prompt injection) chỉ kiểm chứng được bằng E2E với key thật.

## 8. Gap test hiện tại

- Chưa có browser automation (Playwright) cho luồng upload, trợ lý, duyệt, hoàn tác.
- Chưa có test container/volume recovery tự động.
- Chưa có bộ đánh giá chất lượng trợ lý (đúng công cụ, đúng thao tác, từ chối khi bị tiêm lệnh) trên mô hình thật.
- Chưa có load/cost benchmark, đặc biệt cho lượt trợ lý gọi nhiều công cụ.
- Chưa có test cho rate limit (chưa có tính năng).

Các gap phải được ưu tiên theo [traceability matrix](../01-requirements/traceability-matrix.md).
