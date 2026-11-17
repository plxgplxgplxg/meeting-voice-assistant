# Chương 3: Phân Tích & Thiết Kế Hệ Thống

## 3.1. Phân Tích Yêu Cầu Phần Mềm

Hệ thống có 12 ca sử dụng chính: xác thực, dự án, nạp/xử lý audio, Transcript Studio, summary/action item, hỏi đáp có trích dẫn, export, chia sẻ, quota, thanh toán, **hoàn tác chỉnh sửa** và **tạo tài liệu bằng trợ lý**; cùng các use case phụ về ghi microphone và hồ sơ người dùng. Chi tiết nằm ở [use-cases.md](../01-requirements/use-cases.md) và [srs.md](../01-requirements/srs.md).

Hai yêu cầu có ảnh hưởng thiết kế lớn nhất là:

- **Trợ lý biết thao tác** (FR-AGENT): người dùng yêu cầu bằng ngôn ngữ tự nhiên ("đổi tên Speaker 1 thành An", "soạn biên bản") và hệ thống thực hiện được, nhưng mọi thay đổi dữ liệu phải do con người duyệt và hoàn tác được.
- **Dữ liệu chỉnh sửa phải truy vết được** (FR-REV): ai sửa, sửa gì, lúc nào, và có thể đảo ngược; đồng thời hai người sửa đồng thời không làm mất thay đổi của nhau.

## 3.2. Thiết Kế Kiến Trúc

Kiến trúc gồm Next.js, FastAPI Backend, Celery Worker và beat, FastAPI AI Service, PostgreSQL (kèm pgvector), Redis, Nginx và shared audio volume. Gladia xử lý ASR/diarization; Gemini/OpenAI xử lý generation. Phần self-host chạy trên EC2 CPU. Sơ đồ container và module xem [system-architecture.md](../03-architecture/system-architecture.md).

### 3.2.1. Nguyên tắc phân chia trách nhiệm

Backend sở hữu dữ liệu và phân quyền; AI Service chỉ tính toán (ASR adapter, embedding, sinh văn bản, agent) và không bao giờ ghi vào cơ sở dữ liệu nghiệp vụ. Lựa chọn này cho phép thay mô hình hoặc nhà cung cấp mà không đụng tới logic nghiệp vụ, và bảo đảm chỉ có một nơi quyết định "ai được làm gì".

### 3.2.2. Điểm kiểm soát quyền duy nhất

`MeetingAccessPolicy` nhận `Actor` (người dùng, khách share-link, hoặc agent thay mặt người dùng) và quyền cần có (VIEW, EDIT, MANAGE). Quyền cao nhất trong các nguồn (người tạo, vai trò trong project, share token) được chọn. REST, Worker và các công cụ của agent đều gọi cùng một hàm này, nên không thể có hai bộ quy tắc lệch nhau.

### 3.2.3. Tầng lệnh cho transcript và sự kiện miền

Mọi thao tác sửa transcript đi qua `TranscriptEditor`, gồm ba bước: **lập kế hoạch** (`TranscriptPlanner`, hàm thuần chuyển danh sách thao tác thành danh sách thay đổi từng segment), **áp dụng** (khóa dòng meeting, kiểm tra `expected_revision`, ghi segment và change set trong một transaction) và **hoàn tác** (áp dụng phép nghịch đảo như một change set mới). Bảy loại thao tác được hỗ trợ: sửa nội dung, thay thế văn bản, đổi tên người nói, gán lại người nói, xóa, tách và gộp segment.

Sau khi áp dụng, sự kiện `TranscriptEdited` được phát qua `EventBus`; handler đánh dấu tóm tắt và chỉ mục là `stale` và xếp một job dựng lại chỉ mục với độ trễ ngắn. Cách tách này giữ cho `TranscriptEditor` không biết gì về tóm tắt hay chỉ mục (coupling thấp), và cho phép thêm phản ứng mới mà không sửa nơi sửa transcript.

### 3.2.4. Xử lý nền bền vững

Mỗi lần upload ghi `processing_jobs` và `outbox_events` trong cùng transaction. Một tiến trình beat đọc outbox mỗi hai giây và chuyển sang Celery; vì vậy không có tình huống "đã commit nhưng chưa có task" hay "đã có task nhưng chưa commit", và việc Redis tạm ngừng chỉ làm chậm hệ thống. Mỗi bước (`transcribe`, `summarize`, `index`) idempotent, số lần thử và lịch retry nằm trong dòng job, và máy trạng thái của meeting chỉ cho phép các chuyển trạng thái hợp lệ.

### 3.2.5. Truy xuất tăng cường (RAG) nằm ở Backend

Transcript được chia theo lượt nói, nhúng thành vector 384 chiều và lưu trong PostgreSQL. Truy vấn hợp nhất xếp hạng cosine (HNSW) và xếp hạng văn bản đầy đủ (GIN trên `tsvector`) bằng Reciprocal Rank Fusion trong **một câu SQL**, luôn lọc theo `meeting_id`. Nhờ đó chỉ top-k đoạn được gửi cho mô hình, độ trễ và chi phí không tăng theo độ dài cuộc họp.

### 3.2.6. Agent: đề xuất trước, ghi sau

Agent (LangGraph) chạy trong AI Service. Nó gọi công cụ của Backend qua một API nội bộ, xác thực bằng `X-Service-Token` **và** một token ủy quyền ngắn hạn (5 phút, giới hạn một meeting, mang quyền của chính người dùng). Công cụ đọc trả dữ liệu (được bọc trong thẻ đánh dấu là dữ liệu không tin cậy); công cụ ghi chỉ tạo bản ghi `agent_actions` kèm diff xem trước. Người dùng duyệt qua endpoint công khai; khi duyệt, Backend gọi `TranscriptEditor.apply` với `actor_type=agent` và `base_revision`, nên đề xuất tự vô hiệu nếu transcript đã đổi hoặc quá 30 phút.

Lựa chọn này cho các tính chất mong muốn:

| Tính chất | Cơ chế |
|---|---|
| Prompt injection không vượt quyền | Token giới hạn một meeting và bằng quyền người dùng; công cụ ghi không ghi trực tiếp |
| Con người luôn có lần xem cuối | Mọi thay đổi là đề xuất với diff; duyệt là hành động tách biệt |
| Hoàn tác được | Thay đổi được áp dụng là một change set, có thể đảo ngược |
| Bền qua nhiều request | Đề xuất lưu ở DB, không cần giữ tiến trình agent chờ phê duyệt |
| Không phụ thuộc thư viện LLM ở Backend | Agent nằm trong AI Service; Backend chỉ nói chuyện HTTP/SSE |

Luồng chi tiết xem [sequence-diagrams.md](../03-architecture/sequence-diagrams.md).

## 3.3. Thiết Kế Cơ Sở Dữ Liệu

Mô hình quan hệ gồm 24 bảng, chia thành các nhóm: người dùng/dự án (5, gồm `refresh_tokens`), cuộc họp và nội dung (5), xử lý nền và truy xuất (3: `processing_jobs`, `outbox_events`, `transcript_chunks`), lịch sử chỉnh sửa (2), trợ lý (4: hội thoại, tin nhắn, đề xuất, tài liệu) và gói/thanh toán (5). Extension pgvector lưu vector trong `transcript_chunks` với chỉ mục HNSW cosine và GIN cho `tsvector`. Schema được quản lý bằng năm revision Alembic và CI kiểm tra `alembic check`; mọi timestamp là `timestamptz`. Chi tiết xem [database-erd.md](../04-design/database-erd.md).

Quyết định đáng chú ý:

- `meetings.transcript_revision` là bộ đếm tăng theo mỗi thay đổi, dùng cho khóa lạc quan và để vô hiệu hóa đề xuất cũ.
- `transcript_segment_changes` lưu `before`/`after` dạng JSON thay vì ràng buộc khóa ngoại tới segment, vì segment bị xóa vẫn phải khôi phục được.
- Trạng thái nội bộ của LangGraph nằm ở schema riêng `langgraph`, tách khỏi schema nghiệp vụ do Alembic quản lý.
