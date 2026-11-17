# Chương 4: Hiện Thực Hóa & Cài Đặt Hệ Thống

## 4.1. Môi Trường & Công Cụ Phát Triển

Docker Compose đóng gói Nginx, Next.js 14 standalone, hai ứng dụng FastAPI, Celery worker và beat, PostgreSQL 16/pgvector và Redis 7. AI Service dùng PyTorch/sentence-transformers cho multilingual E5 và LangGraph cho agent; ASR thực gọi Gladia thay vì Faster-Whisper self-host. Backend dùng SQLAlchemy 2 bất đồng bộ, Alembic, structlog; kiểm tra chất lượng bằng ruff, mypy ở chế độ strict cho phần miền và chính sách quyền, và pytest. Frontend dùng React Query, kiểm tra bằng ESLint, `tsc` và bộ test của Node.

## 4.2. Cài Đặt Các Module Cốt Lõi

### 4.2.1. Chính sách quyền và lỗi miền

`services/access_policy.py` cài đặt `MeetingAccessPolicy`; các route chỉ khai báo quyền cần có qua dependency (`MeetingForView`, `MeetingForEdit`, `MeetingForManage`). Service ném `DomainError` (không biết gì về HTTP); một handler duy nhất chuyển thành envelope `{"error": {code, message, path, request_id}}`. Ma trận `test_authorization.py` kiểm tra các route theo meeting (kể cả route lịch sử, đề xuất và tài liệu) với bảy vai trò.

### 4.2.2. Xử lý audio bền vững

`processing/` gồm: `state.py` (máy trạng thái), `pipeline.py` (từng bước idempotent), `jobs.py` (số lần thử, backoff, kết quả bước), `outbox.py` (ghi và gửi sự kiện), `handlers.py` (phản ứng với sự kiện miền). Bước transcribe gửi file cho AI Service và nhận `provider_job_id`, sau đó Celery tự retry theo `retry_in` để poll kết quả mà không giữ worker. `ffprobe` kiểm tra thời lượng và codec trước khi tốn tiền ASR. Quota chỉ được ghi đúng một lần cho mỗi file audio nhờ khóa unique.

### 4.2.3. Transcript Studio và lịch sử

`TranscriptEditor` thực hiện apply, preview và revert; `transcript_ops.py` chứa các thao tác (union phân biệt theo `op`) và bộ lập kế hoạch thuần. Khóa `SELECT ... FOR UPDATE` trên dòng meeting tuần tự hóa các chỉnh sửa đồng thời; `expected_revision` biến xung đột thành lỗi 409 để giao diện tải lại thay vì ghi đè. Vì `UNIQUE (meeting_id, sequence_order)` có thể bị vi phạm tạm thời khi tách, gộp hoặc xóa, editor di chuyển các thứ tự sang vùng tạm trước khi ghi giá trị cuối. Frontend hiển thị lịch sử trong `ChangeHistoryDrawer` và thông báo hoàn tác nhanh qua `UndoToast`.

### 4.2.4. Truy xuất lai

`RetrievalService` thực hiện truy vấn hợp nhất vector và văn bản trong PostgreSQL; `chunking.py` (chuyển từ AI Service sang Backend) chia transcript theo lượt nói. Bước `index` luôn dựng lại từ transcript mới nhất, nên một loạt chỉnh sửa liên tiếp chỉ tốn một lần dựng. Kiểm thử truy xuất chạy trên PostgreSQL thật vì SQLite không có pgvector.

### 4.2.5. Export

`export/` gồm `MeetingDocumentLoader` (đọc dữ liệu một lần), `registry` (ánh xạ định dạng sang renderer, kèm kiểm tra gói) và các renderer cho DOCX, TXT, SRT, VTT và JSON. Thêm định dạng mới là thêm một renderer, không sửa service.

### 4.2.6. Trợ lý

Phía AI Service, `app/agent/` gồm `graph.py` (StateGraph agent, tools, agent), `tools.py` (chín công cụ cùng schema đầu vào: năm công cụ đọc, ba công cụ đề xuất và một công cụ tạo tài liệu), `backend_client.py` (HTTP client giữ token ủy quyền), `runner.py` (chuyển luồng sự kiện LangGraph thành SSE), `checkpoint.py` (PostgreSQL), và `fake.py` cho test. Phía Backend, `assistant_service.py` điều phối một lượt (kiểm tra quyền và gói, ký token, mở luồng SSE, lưu tin nhắn), `agent_tools.py` triển khai các công cụ đọc, `agent_actions.py` quản lý vòng đời đề xuất (tạo, duyệt, từ chối, hết hạn), và `artifact_service.py` tạo tài liệu.

Một số quyết định cài đặt đáng ghi lại:

- Sự kiện `proposal` gửi cho client được đọc lại từ cơ sở dữ liệu theo `action_id` và loại bỏ đề xuất không thuộc người dùng, nên nội dung do agent tự khai không tin cậy.
- Phiên cơ sở dữ liệu của request được commit trước khi mở luồng SSE vì agent sẽ gọi ngược về Backend trong các request khác và phải nhìn thấy tin nhắn vừa lưu.
- Khi công cụ lỗi do quyền hoặc gói, lỗi được trả cho mô hình dưới dạng văn bản để nó giải thích cho người dùng; lỗi kết nối được retry một lần; thao tác ghi không bao giờ được retry tự động.
- Tên tệp tài liệu không phải ASCII (ví dụ "Biên bản họp") được mã hóa theo RFC 5987 (`filename*=UTF-8''...`). Lỗi này được phát hiện nhờ test: header chỉ chứa Latin-1 làm hỏng phản hồi tải xuống.

### 4.2.7. Giao diện

`AssistantPane` đọc luồng SSE bằng `fetch` + `ReadableStream`, phân tích sự kiện trong module thuần `assistant-events.ts`. `ProposalCard` hiển thị diff của đề xuất (có thể sửa danh sách thao tác trước khi duyệt, logic ở `proposal-edits.ts`), `ArtifactsPanel` liệt kê và tải tài liệu. Các module thuần được kiểm thử bằng test runner có sẵn của Node. Giao diện theo chuẩn Clean Minimalist: nhãn tiếng Việt ngắn, không văn bản thừa.

### 4.2.8. Kiểm thử

| Thành phần | Số test | Ghi chú |
|---|---|---|
| Backend (SQLite) | 415 đạt, 7 bỏ qua | 7 test cần PostgreSQL bị bỏ qua |
| Backend (PostgreSQL) | xem [implementation-status.md](../07-improvement-plan/implementation-status.md) | Thêm truy xuất vector, đồng thời thanh toán, kiểm tra migration |
| AI Service | 75 đạt (kèm checkpoint PostgreSQL) | Agent, công cụ, router, pipeline |
| Frontend | 12 đạt | Sự kiện SSE, chỉnh sửa đề xuất |

Các test đáng chú ý: `test_authorization.py` (ma trận quyền), `test_transcript_editor.py` (đồng thời, hoàn tác, thứ tự), `test_outbox.py` (không mất việc khi crash giữa chừng), `test_assistant_turns.py` (từ yêu cầu "đổi tên người nói" đến duyệt, lỗi thời, dựng lại chỉ mục, tạo DOCX; và agent bị chiếm vẫn chỉ tạo được đề xuất).

## 4.3. Giới hạn implementation

- `/live` ghi WebM rồi xử lý batch; chưa có transcript thời gian thực. WebSocket đã được gỡ bỏ.
- Token trình duyệt vẫn lưu trong `localStorage`; cần cookie HttpOnly và chiến lược CSRF.
- Chưa có rate limit, chưa có expiry/revoke cho share link, chưa có audit log truy cập đọc.
- Chưa có kiểm thử trình duyệt tự động cho luồng upload, trợ lý, duyệt, hoàn tác.
- Tên model LLM còn gán cố định theo provider; chất lượng câu trả lời chưa có bộ đánh giá tự động (xem chương 5).
- Chưa có chính sách xóa dữ liệu hoàn chỉnh (xóa meeting là soft-delete và giữ chunk, hội thoại, audio).
