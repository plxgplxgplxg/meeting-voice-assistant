# QUY ƯỚC GIAO TIẾP API

**Cập nhật:** 17/11/2026

## 1. Base URL

- Production sau Nginx: same-origin `/api/v1`.
- Local Docker: `http://localhost:8000/api/v1`.
- Frontend đọc `NEXT_PUBLIC_BACKEND_API_URL`; nếu rỗng sẽ dùng same-origin.
- AI Service chỉ dùng nội bộ: `http://ai-service:8001`, mọi request kèm header `X-Service-Token`. Port 8001 không được publish ra ngoài (dev chỉ bind `127.0.0.1`).

## 2. Xác thực và phân quyền

- REST endpoint được bảo vệ dùng `Authorization: Bearer <access_token>`. Access token chứa claim `tv` (token_version); đổi mật khẩu làm mọi token cũ mất hiệu lực.
- Refresh token dùng một lần (rotation). Dùng lại token đã dùng sẽ thu hồi cả chuỗi token (`REFRESH_TOKEN_REUSED`). Client phải gọi refresh theo kiểu single-flight, vì gọi song song sẽ bị coi là reuse.
- Mọi route theo meeting đi qua `MeetingAccessPolicy`: `GET` cần VIEW, thay đổi cần EDIT, xóa/chia sẻ cần MANAGE. Quy tắc: người tạo = MANAGE; owner/editor project = EDIT; viewer project = VIEW; share token = VIEW hoặc EDIT tùy `share_permission`, không bao giờ MANAGE.
- Share token truyền bằng query `?share=<token>` trên **mọi** request thuộc meeting (không chỉ `GET /meetings/{id}`). Frontend gắn tự động trong `fetchApi`.
- Webhook SePay: header `Authorization: Apikey <key>`; thiếu hoặc sai key trả `401`.
- Tạo meeting, upload audio và liệt kê meeting yêu cầu đăng nhập.

## 3. Payload và lỗi

- JSON dùng `snake_case` để khớp Pydantic.
- Upload dùng `multipart/form-data` với field `file`; giới hạn `MAX_UPLOAD_MB`, kiểm tra extension và magic bytes.
- Mọi lỗi (domain, HTTP, validation) dùng một envelope:

```json
{"error": {"code": "MEETING_FORBIDDEN", "message": "...", "path": "/api/v1/...", "request_id": "..."}}
```

- Mã lỗi thường gặp: `AUTHENTICATION_REQUIRED` 401, `MEETING_FORBIDDEN` 403, `MEETING_NOT_FOUND` 404, `INVALID_MEETING_STATE` 409, `QUOTA_EXCEEDED` 402, `PLAN_FEATURE_REQUIRED` 402, `UPLOAD_TOO_LARGE` 413, `AI_UNAVAILABLE` 503, `VALIDATION_FAILED` 422.
- Mã lỗi của chỉnh sửa và trợ lý (đều 409 trừ khi ghi khác): `TRANSCRIPT_REVISION_CONFLICT` (revision đã đổi), `EXPECTED_REVISION_REQUIRED` (422, agent thiếu revision), `NO_CHANGES` (422), `ALREADY_REVERTED`, `TRANSCRIPT_REVERT_CONFLICT`, `PROPOSAL_STALE`, `PROPOSAL_EXPIRED`, `ALREADY_DECIDED`, `PROPOSAL_FORBIDDEN` (403), `INDEX_NOT_READY`, `RAG_QUESTION_LIMIT` (402).
- Header `X-Request-ID` được trả về trong mọi response và có trong `error.request_id`.
- `204 No Content` không có JSON body.

## 4. Trạng thái xử lý

`meeting.status` đi theo máy trạng thái `draft -> uploaded -> transcribing -> summarizing -> (indexing) -> ready`, hoặc `failed` kèm `failure_stage` và `failure_reason`. Client không được gán `status`. Client polling cho tới khi `ready` hoặc `failed`; khi `failed` hiển thị lý do và nút thử lại (`POST /meetings/{id}/reprocess`). `summary_status` và `index_status` (`none|pending|ready|stale|failed`) mô tả riêng bản tóm tắt và chỉ mục tìm kiếm; `transcript_revision` là số phiên bản của transcript. Meeting xử lý bằng engine mock (chỉ development) có `is_demo=true`.

Việc chạy nền đi qua transactional outbox: request chỉ ghi `processing_jobs` và `outbox_events` trong transaction của nó, beat chuyển sự kiện sang Celery sau khi commit. Có thể kích hoạt riêng `POST /meetings/{id}/reindex` và `POST /meetings/{id}/summary:regenerate` (cùng trả 202).

## 5. Audio

- `GET /meetings/{id}/audio/stream-url` trả URL ký HMAC, hết hạn sau 10 phút; dùng trực tiếp làm `src` của `<audio>` vì thẻ này không gửi được Bearer token.
- `GET /meetings/{id}/audio/stream` chấp nhận hoặc quyền VIEW hoặc chữ ký `?exp=&sig=` hợp lệ. Nginx forward `Range`/`If-Range`.

## 6. Contract chính frontend–backend

| Nhu cầu | Endpoint |
|---|---|
| Transcript list | `GET /meetings/{id}/transcript` |
| Segment update | `PATCH /meetings/{id}/transcript/segments/{segment_id}` |
| Rename speaker | `POST /meetings/{id}/transcript/rename-speaker` |
| Delete segments | `POST /meetings/{id}/transcript/delete-segments` |
| Áp dụng nhiều thao tác (một change set) | `POST /meetings/{id}/transcript/operations` với `{operations, expected_revision}` |
| Xem trước thay đổi | `POST /meetings/{id}/transcript/operations:preview` |
| Lịch sử chỉnh sửa | `GET /meetings/{id}/transcript/change-sets`, `GET .../change-sets/{change_set_id}` |
| Hoàn tác | `POST /meetings/{id}/transcript/change-sets/{change_set_id}/revert` |
| Summary | `GET /meetings/{id}/summary` |
| Action items | `GET /meetings/{id}/action-items`, `PATCH /meetings/{id}/action-items/{item_id}` |
| Chat history | `GET /meetings/{id}/chat/messages` (lịch sử riêng theo người dùng) |
| Ask (không stream) | `POST /meetings/{id}/chat` với `{ "query": "..." }` |
| Lượt trợ lý (SSE) | `POST /meetings/{id}/assistant/turns` với `{ "message": "..." }` |
| Đề xuất của trợ lý | `GET /meetings/{id}/agent-actions[?status=]`, `POST .../agent-actions/{action_id}:approve`, `POST .../agent-actions/{action_id}:reject` |
| Tài liệu sinh ra | `GET /meetings/{id}/artifacts`, `POST /meetings/{id}/artifacts`, `GET .../artifacts/{artifact_id}/download`, `DELETE .../artifacts/{artifact_id}` |
| Export | `GET /meetings/{id}/exports/{format}` (định dạng phụ thuộc gói của chủ meeting) |
| Upload vào meeting | `POST /meetings/{id}/audio` |
| Upload tạo meeting mới | `POST /audio/upload` |
| Subscription | `GET /plans/my-subscription` |
| Đổi mật khẩu | `POST /users/me/change-password` (trả token mới) |

Các đường dẫn cũ (`/transcripts/...`, `/summaries/...`, `/chat/...`, `/exports/...`, `/audio/{id}/...`) vẫn hoạt động như alias deprecated và đi qua cùng kiểm tra quyền. Route `GET /meetings/{id}/export` và WebSocket `/live/ws` đã bị xóa.

## 7. Lượt trợ lý (Server-Sent Events)

`POST /meetings/{id}/assistant/turns` trả `text/event-stream`. Client dùng `fetch` với `ReadableStream` (không dùng `EventSource` vì cần header `Authorization` và phương thức POST). Frame có dạng `event: <loại>` và `data: <JSON>`. Nginx tắt buffering cho route này (`X-Accel-Buffering: no`).

| Sự kiện | `data` | Ý nghĩa |
|---|---|---|
| `token` | `{text}` | Một đoạn văn bản của câu trả lời |
| `tool_start` | `{name, args?}` | Agent bắt đầu gọi một công cụ |
| `tool_end` | `{name, summary?}` | Công cụ xong |
| `proposal` | `AgentAction` | Một đề xuất cần người dùng duyệt (được đọc lại từ DB, không tin payload của agent) |
| `citation` | `Citation` | Trích dẫn kèm khoảng thời gian trong audio |
| `done` | `{message_id}` | Lượt kết thúc, tin nhắn đã lưu |
| `error` | `{code, message}` | Lỗi giữa chừng; tin nhắn lỗi cũng được lưu để hiển thị khi tải lại |

Lỗi xảy ra **trước** khi stream bắt đầu (không đủ quyền, gói không hỗ trợ, `INDEX_NOT_READY`, hết hạn mức) trả JSON error envelope với mã HTTP bình thường, không phải một stream. Gói không có `features.agent_tools` và khách share-link nhận cùng stream nhưng chỉ có `token`, `citation`, `done`.

Quyền: cần VIEW; công cụ ghi chỉ tạo đề xuất. Duyệt đề xuất cần EDIT và phải do chính người tạo hội thoại thực hiện.

## 8. API công cụ nội bộ cho agent

Prefix `/internal/agent/v1`, **không** có trong OpenAPI công khai và bị Nginx chặn (`location /internal/ { return 404; }`). Mỗi request cần cả hai header:

- `X-Service-Token: <AI_SERVICE_TOKEN>`
- `Authorization: Bearer <token ủy quyền>`: JWT `aud="agent"`, sống 5 phút, `scope=meeting:{id}`, kèm `conv` (id hội thoại) và `tv` (token_version của người dùng). Token này bị từ chối ở API công khai và ngược lại.

| Route | Mục đích |
|---|---|
| `GET /meetings/{id}/overview` | Tiêu đề, thời lượng, người nói, revision, trạng thái |
| `POST /meetings/{id}/search` | Tìm kiếm lai trong transcript (cùng `RetrievalService`) |
| `GET /meetings/{id}/segments` | Đọc segment theo khoảng thời gian/người nói (giới hạn số lượng mỗi lần) |
| `POST /meetings/{id}/find` | Tìm văn bản nguyên văn (có thể phân biệt hoa thường) |
| `GET /meetings/{id}/summary` | Tóm tắt, ý chính, action item |
| `POST /meetings/{id}/agent-actions` | Tạo đề xuất (`transcript_ops`, `action_item_ops`, `summary_regenerate`); không ghi vào meeting |
| `POST /meetings/{id}/artifacts` | Tạo tài liệu (`minutes_docx`, `email_draft`, `srt`, `custom_md`) |

Mọi route kiểm tra: hai credential, `aud` và hạn token, `scope` khớp meeting trong URL, hội thoại thuộc đúng người dùng và meeting, `token_version` còn hiệu lực, quyền thực tế của người dùng (không bao giờ dùng share token), gói có `agent_tools`. Nội dung transcript trả về cho agent luôn do agent bọc trong thẻ `<transcript>` kèm cảnh báo dữ liệu không tin cậy.

Các thao tác transcript mà đề xuất có thể chứa: `update_text`, `replace_text`, `rename_speaker`, `reassign_speaker`, `delete_segments`, `split_segment`, `merge_segments`. Thao tác action item: `create`, `update`, `delete`.

## 9. AI Service

| Route | Mục đích |
|---|---|
| `POST /audio/transcribe` | `{meeting_id, storage_key, language, min_speakers, max_speakers}`; trả `provider_job_id`. Key được resolve trong `STORAGE_ROOT`, không nhận đường dẫn tuyệt đối hay URL. |
| `GET /audio/transcribe/{provider_job_id}` | Trạng thái: đang xử lý, hoàn tất (kèm segment), hoặc lỗi. Trả `is_demo`. |
| `POST /embeddings` | Embedding cho danh sách văn bản (chunk khi dựng chỉ mục, câu hỏi khi truy vấn). |
| `POST /rag/answer` | Trả lời có trích dẫn từ các chunk đã chọn ở Backend. |
| `POST /llm/summarize` | Tóm tắt và action items từ transcript. |
| `POST /agent/turn` | Một lượt agent (SSE): `{thread_id, conversation_id, meeting_id, message, delegated_token, base_revision}`. |
| `GET /health` | `healthy` hoặc `degraded` kèm `reasons`. |

AI Service trả lỗi cùng envelope; `PROVIDER_NOT_CONFIGURED` (503) khi thiếu key/model. Không bao giờ trả dữ liệu giả ở production. Mọi route trừ `/health` cần `X-Service-Token`.

OpenAPI runtime tại `/openapi.json` (tắt ở production) là nguồn contract cuối cùng; file [api-specification.yaml](api-specification.yaml) là bản xuất từ code (`python scripts/export_openapi.py` trong `backend-api`, không gồm `/internal`), và `tests/test_openapi_contract.py` báo lỗi khi file này lệch với ứng dụng.
