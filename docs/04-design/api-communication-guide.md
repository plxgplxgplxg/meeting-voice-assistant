# QUY ƯỚC GIAO TIẾP API

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
- Header `X-Request-ID` được trả về trong mọi response và có trong `error.request_id`.
- `204 No Content` không có JSON body.

## 4. Trạng thái xử lý

`meeting.status` đi theo máy trạng thái `draft -> uploaded -> transcribing -> summarizing -> (indexing) -> ready`, hoặc `failed` kèm `failure_stage` và `failure_reason`. Client không được gán `status`. Client polling cho tới khi `ready` hoặc `failed`; khi `failed` hiển thị lý do và nút thử lại (`POST /meetings/{id}/reprocess`). `summary_status` (`none|pending|ready|stale|failed`) mô tả riêng bản tóm tắt. Meeting xử lý bằng engine mock (chỉ development) có `is_demo=true`.

Task Celery chỉ được dispatch sau khi transaction của request commit.

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
| Summary | `GET /meetings/{id}/summary` |
| Action items | `GET /meetings/{id}/action-items`, `PATCH /meetings/{id}/action-items/{item_id}` |
| Chat history | `GET /meetings/{id}/chat/messages` (lịch sử riêng theo người dùng) |
| Ask | `POST /meetings/{id}/chat` với `{ "query": "..." }` |
| Export | `GET /meetings/{id}/exports/{format}` (định dạng phụ thuộc gói của chủ meeting) |
| Upload vào meeting | `POST /meetings/{id}/audio` |
| Upload tạo meeting mới | `POST /audio/upload` |
| Subscription | `GET /plans/my-subscription` |
| Đổi mật khẩu | `POST /users/me/change-password` (trả token mới) |

Các đường dẫn cũ (`/transcripts/...`, `/summaries/...`, `/chat/...`, `/exports/...`, `/audio/{id}/...`) vẫn hoạt động như alias deprecated và đi qua cùng kiểm tra quyền. Route `GET /meetings/{id}/export` và WebSocket `/live/ws` đã bị xóa.

## 7. AI Service

| Route | Mục đích |
|---|---|
| `POST /audio/transcribe` | `{meeting_id, storage_key, language}`; key được resolve trong `STORAGE_ROOT`, không nhận đường dẫn tuyệt đối hay URL. Trả `is_demo`. |
| `POST /rag/query` | Hỏi đáp có trích dẫn. |
| `POST /rag/summarize` | Tóm tắt và action items. |
| `GET /health` | `healthy` hoặc `degraded` kèm `reasons`. |

AI Service trả lỗi cùng envelope; `PROVIDER_NOT_CONFIGURED` (503) khi thiếu key/model. Không bao giờ trả dữ liệu giả ở production.

OpenAPI runtime tại `/openapi.json` (tắt ở production) là nguồn contract cuối cùng.
