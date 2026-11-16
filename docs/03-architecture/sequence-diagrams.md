# Sơ Đồ Tuần Tự Hệ Thống (Runtime View - Sequence Diagrams)

**Dự án:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp (Meeting Voice Assistant)  
**Tiêu chuẩn áp dụng:** arc42 Mục 6 (Runtime View), UML 2.5 Sequence Specification (Analysis Level)  
**Tài liệu liên quan:** [docs/03-architecture/system-architecture.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/03-architecture/system-architecture.md), [docs/02-research-tech/asr-diarization-survey.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/asr-diarization-survey.md), [docs/02-research-tech/rag-evaluation-framework.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/rag-evaluation-framework.md)  
**Phiên bản:** 2.2 · **Ngày cập nhật:** 2026-10-22  

---

## 1. Tổng Quan Runtime View (Analysis Level)

Tài liệu này đặc tả 6 luồng tương tác cốt lõi theo chuẩn UML quốc tế (Analysis Level):
1. **Luồng 1:** Ghi âm trực tiếp (UC-01: Live Recording)
2. **Luồng 2:** Xử lý tệp âm thanh (UC-02: Batch Processing)
3. **Luồng 3:** Hỏi đáp cuộc họp (UC-05: Meeting Q&A)
4. **Luồng 4:** Chỉnh sửa biên bản (UC-03: Transcript Editing)
5. **Luồng 5:** Xử lý sự cố & Phục hồi (Fault Recovery)
6. **Luồng 6:** Chia sẻ & Phân quyền qua Link (UC-07: Share Meeting & Access Control)

Các sơ đồ sử dụng thuật ngữ kỹ thuật chuyên ngành chuẩn hóa (Frontend UI, AudioWorklet, Backend API, Celery Worker, PostgreSQL + pgvector, Redis Streams, External LLM), tập trung vào các bước xử lý trọng yếu, loại bỏ việc chia lane/box rườm rà và được căn chỉnh layout để vừa vặn trên màn hình hiển thị.

---

## 2. Luồng 1: Ghi âm trực tiếp (UC-01: Live Recording)

Mô tả quá trình thu âm qua Microphone, phát hiện giọng nói (Silero VAD) và hiển thị văn bản nháp tức thời (Zipformer-vi) với độ trễ $\le 1.5$ giây.

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

actor "User" as User
boundary "Frontend UI\n(Next.js)" as UI
control "AudioWorklet" as AW
control "Live ASR Engine\n(Silero VAD + Zipformer)" as LiveASR
database "Audio Storage" as Storage
control "SSE Gateway" as SSE

User -> UI: Nhấn nút "Bắt đầu ghi âm"
UI -> AW: Khởi tạo luồng thu âm (PCM 16 kHz Mono)
UI -> LiveASR: Khởi tạo phiên truyền âm thanh (WebSocket /ws/live)
LiveASR --> UI: Xác nhận kết nối sẵn sàng (101 Switching Protocols)

loop Trong suốt phiên họp (Mỗi chunk âm thanh 100ms)
    AW -> LiveASR: Gửi khối nhị phân audio chunk qua WebSocket
    LiveASR -> Storage: Ghi nối tiếp dữ liệu vào tệp âm thanh lưu trữ
    LiveASR -> LiveASR: Silero VAD lọc khung 32ms (ngưỡng speech_prob >= 0.55)
    
    alt Phát hiện tiếng nói & tích lũy buffer >= 450ms
        LiveASR -> LiveASR: Zipformer-vi giải mã nhanh bộ đệm hiện tại
        LiveASR -> SSE: Phát sự kiện segment.draft_partial
        SSE -> UI: Server-Sent Event (Text preview chạy theo thời gian thực)
        UI -> UI: Render chữ chạy kiểu Karaoke trên giao diện
    end
    
    alt Khoảng lặng >= 500ms HOẶC câu dài >= 6.5s (Chốt câu nháp)
        LiveASR -> LiveASR: Zipformer-vi giải mã hoàn tất câu (Finalize text)
        LiveASR -> SSE: Phát sự kiện segment.draft_final kèm start_ms, end_ms
        LiveASR -> LiveASR: Xóa rỗng speech_buffer để đón câu phát biểu mới
        SSE -> UI: Server-Sent Event (Cố định câu nháp trên timeline)
    end
end

User -> UI: Nhấn nút "Kết thúc cuộc họp"
UI -> LiveASR: Gửi lệnh đóng phiên {action: "STOP_RECORDING"}
LiveASR -> Storage: Đóng tệp âm thanh hoàn chỉnh
LiveASR --> UI: Xác nhận hoàn tất thu âm, sẵn sàng kích hoạt Pass 2
@enduml
```

---

## 3. Luồng 2: Xử lý tệp âm thanh (UC-02: Batch Processing)

Mô tả quy trình tải file ghi âm lên hệ thống: tự động bóc băng, phân tách người nói, tạo bản tóm tắt và trích xuất danh sách việc cần làm.

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

actor "User" as User
boundary "Frontend UI" as UI
control "Backend API\n(FastAPI)" as API
control "Redis Queue\n& Streams" as Redis
control "Celery Worker\n(ai-service CPU)" as Worker
boundary "Gladia Cloud API\n(Solaria-1)" as Gladia
entity "PostgreSQL\n+ pgvector" as DB
boundary "External LLM\n(Gemini 2.0 Flash)" as LLM

User -> UI: Tải tệp âm thanh cuộc họp lên (WAV/MP3/M4A)
UI -> API: POST /api/v1/meetings/upload (Multipart Audio File)
API -> API: Xác thực ffprobe, lưu file vào Storage, tạo Meeting (QUEUED)
API -> Redis: Đẩy tác vụ ProcessAudioTask vào Celery Queue
API --> UI: Phản hồi 202 Accepted (kèm meeting_id, task_id)
UI -> API: Mở kết nối SSE /api/v1/meetings/{id}/events để theo dõi tiến độ

Worker -> Redis: Nhận tác vụ từ hàng đợi
Worker -> Redis: Phát sự kiện stage: "uploading_gladia" (Tiến độ 20%)
Worker -> Gladia: 1. POST /v2/upload (Tải file âm thanh lên Gladia)
Gladia --> Worker: Phản hồi audio_url tạm thời

Worker -> Redis: Phát sự kiện stage: "transcribing_diarizing" (Tiến độ 50%)
Worker -> Gladia: 2. POST /v2/pre-recorded {model: "solaria-1", diarization: true, lang: "vi"}
Gladia --> Worker: Phản hồi job_id và result_url
Worker -> Gladia: 3. Polling GET /v2/pre-recorded/{id} đến khi hoàn tất
Gladia --> Worker: Trả về kết quả JSON {utterances: [speaker, text, words]}

Worker -> DB: 4. INSERT phân đoạn và mốc từ vào bảng transcript_segments (source='final')

Worker -> Redis: Phát sự kiện stage: "indexing_vectors" (Tiến độ 85%)
Worker -> Worker: 5. Speaker-Turn Chunking & multilingual-e5-small trên CPU
Worker -> DB: 6. INSERT vector 384-dim vào bảng transcript_embeddings (HNSW)

Worker -> Redis: Phát sự kiện stage: "summarizing" (Tiến độ 95%)
Worker -> LLM: 7. Gửi toàn văn transcript tới Gemini 2.0 Flash (Structured JSON)
LLM --> Worker: JSON {executive_summary, key_points, action_items}
Worker -> DB: 8. INSERT vào bảng summaries và action_items

Worker -> DB: 9. UPDATE meetings SET status='COMPLETED'
Worker -> Redis: Phát sự kiện stage: "completed" (Tiến độ 100%)
Redis -> API: SSE Gateway bắt sự kiện completed
API -> UI: Server-Sent Event {event: "transcript.ready"}
UI -> API: GET /api/v1/meetings/{id}/workspace
API --> UI: Trả về transcript đầy đủ, tóm tắt và danh sách việc
UI -> User: Hiển thị đầy đủ biên bản họp trên Transcript Studio
@enduml
```

---

## 4. Luồng 3: Hỏi đáp cuộc họp (UC-05: Meeting Q&A)

Mô tả tính năng hỏi đáp nội dung cuộc thảo luận: tìm kiếm ngữ cảnh liên quan, sinh câu trả lời kèm mốc thời gian để người dùng bấm nghe lại âm thanh gốc.

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

actor "User" as User
boundary "Frontend UI\n& Audio Player" as UI
control "Backend API\n(RAG Core Engine)" as RAG
entity "PostgreSQL\n+ pgvector" as DB
boundary "External LLM\n(GPT-4o-mini)" as LLM

User -> UI: Nhập câu hỏi: "Ai phụ trách thiết kế CSDL và hạn chót khi nào?"
UI -> RAG: POST /api/v1/meetings/{id}/chat (kèm chat_history)

RAG -> RAG: 1. Condense Query (Viết lại câu hỏi độc lập) & Embedder sinh vector(384)
RAG -> DB: 2. Dense Search: Tìm Top-20 vector Cosine distance (<=>)
RAG -> DB: 3. Lexical Search: Tìm Top-20 văn bản khớp từ khóa FTS (tsvector @@)
DB --> RAG: 2 danh sách kết quả ứng viên

RAG -> RAG: 4. Hợp nhất thứ hạng RRF (Reciprocal Rank Fusion, k=60) -> Top-5 chunks

alt Điểm Top-1 RRF < Ngưỡng tin cậy tối thiểu tau (Không tìm thấy bằng chứng)
    RAG --> UI: Phản hồi từ chối: "Nội dung cuộc họp không đề cập đến thông tin này"
else Điểm Top-1 RRF >= tau (Tìm thấy ngữ cảnh hợp lệ)
    RAG -> DB: 5. Window Retrieval: Mở rộng lấy chunk liền kề (±1 chunk)
    DB --> RAG: Trả về ngữ cảnh mở rộng đầy đủ đại từ
    
    RAG -> RAG: 6. Đóng gói XML sandboxing có gắn mã thẻ trích dẫn:\n<excerpts>\n[S0105] (14:20) Nam: Dự án cần hoàn thành CSDL...\n[S0106] (14:26) Linh: Tôi sẽ phụ trách xong trước 15/11.\n</excerpts>
    
    RAG -> LLM: 7. Gửi System Prompt ràng buộc trung thực + Context + Query (stream=True)
    
    loop Truyền luồng câu trả lời (Streaming tokens qua SSE)
        LLM --> RAG: Token: "Linh phụ trách thiết kế CSDL trước 15/11 [S0106]."
        RAG -> RAG: Bóc tách mã thẻ trích dẫn [S0106]
        RAG -> DB: Tra cứu start_ms, speaker của phân đoạn S0106 trong PostgreSQL
        DB --> RAG: start_ms = 866000 (14:26), speaker = "Linh"
        RAG --> UI: SSE Stream: {token: "...", citation: {tag: "[S0106]", time_ms: 866000, speaker: "Linh"}}
        UI -> UI: Hiển thị câu trả lời và Citation Badge
    end
end

User -> UI: Nhấp chuột vào thẻ trích dẫn [Linh, 14:26]
UI -> UI: Audio Player tua đến mốc 866 giây (14:26) và phát âm thanh
UI -> UI: Tự động cuộn màn hình và highlight phân đoạn tương ứng trong Studio
@enduml
```

---

## 5. Luồng 4: Chỉnh sửa biên bản (UC-03: Transcript Editing)

Mô tả tính năng sửa lời thoại hoặc đổi tên người nói: hệ thống lưu lịch sử phiên bản và đồng bộ ngay với dữ liệu tìm kiếm, tóm tắt.

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

actor "User" as User
boundary "Transcript Studio\n(Frontend UI)" as UI
control "Backend API\n(FastAPI)" as API
control "AI Service\n(Embedder)" as Embedder
entity "PostgreSQL\n(ACID Transaction)" as DB

User -> UI: Sửa câu sai chính tả tại phân đoạn SID_105 ("ai ai" -> "AI")
User -> UI: Nhấn nút "Lưu thay đổi" (hoặc phím tắt Ctrl+S)

UI -> API: PATCH /api/v1/meetings/{id}/segments/SID_105\nBody: {content: "Hệ thống AI mới", speaker: "Linh"}

API -> DB: Lấy transcript_version hiện tại và các chunk bị ảnh hưởng
DB --> API: Trả về danh sách chunk ảnh hưởng: [CHUNK_42]

API -> Embedder: Yêu cầu tính lại vector cho nội dung mới của CHUNK_42
Embedder -> Embedder: multilingual-e5-small (CUDA) sinh vector(384) mới
Embedder --> API: Trả về vector mới: [v1, v2, ..., v384]

note over API, DB: BẮT ĐẦU GIAO DỊCH DATABASE NGUYÊN TỬ (BEGIN TRANSACTION)
API -> DB: 1. INSERT INTO transcript_segment_versions (Lưu snapshot cũ để audit)
API -> DB: 2. UPDATE transcript_segments SET content='Hệ thống AI mới' WHERE id='SID_105'
API -> DB: 3. UPDATE transcript_embeddings SET is_active=FALSE WHERE chunk_id='CHUNK_42'
API -> DB: 4. INSERT INTO transcript_embeddings (chunk_id='CHUNK_42_v2', embedding=vector, is_active=TRUE)
API -> DB: 5. UPDATE meetings SET transcript_version=transcript_version+1, summary_stale=TRUE
API -> DB: 6. Cam kết giao dịch (COMMIT)
note over API, DB: HOÀN TẤT GIAO DỊCH DATABASE AN TOÀN

API --> UI: 200 OK {status: "UPDATED", version: 2, summary_stale: true}
UI -> UI: Cập nhật giao diện tức thời & hiển thị banner "Bản tóm tắt đã cũ"
UI -> User: Hiển thị nút "Tạo lại tóm tắt (Regenerate Summary)"
@enduml
```

---

## 6. Luồng 5: Xử lý sự cố & Phục hồi (Fault Recovery)

Mô tả phản ứng tự động khi gặp trục trặc: rớt mạng khi ghi âm (đệm dữ liệu vào trình duyệt), lỗi phân tách người nói, hoặc dịch vụ AI ngoài quá tải.

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

boundary "Frontend UI" as UI
control "Backend API\n& Celery Worker" as Worker
control "Diarization Engine" as Diar
boundary "External Service\n(Cloud LLM / HF)" as ExtService

== KỊCH BẢN 1: LỖI HUGGING FACE TOKEN / PYANNOTE GATED REPO ==
Worker -> Diar: Khởi tạo Engine 1 (pyannote community-1)
Diar -> ExtService: Xác thực HF_TOKEN tải mô hình
ExtService --> Diar: 401 Unauthorized / 403 Gated Repo Access Denied

alt ALLOW_HEURISTIC_DIARIZATION = 1 (Chế độ Debug)
    Diar -> Worker: Kích hoạt ENGINE 2 (Standalone Acoustic Diarizer)
    Worker -> Worker: Phân cụm PyTorch FFT + Pitch K-means thuần
    Worker -> Worker: Gán nhãn tạm SPEAKER_00 / SPEAKER_01
else Mặc định Production (Chế độ An toàn)
    Diar --> Worker: Fallback to Safe Degraded Mode
    Worker -> Worker: Bỏ qua phân tách người nói, gán toàn bộ speaker = "SPEAKER_UNKNOWN"
    Worker -> Worker: Đặt cờ degraded_mode = true vào metadata cuộc họp
end
Worker --> UI: Cảnh báo: "Không thể tự động nhận dạng người nói. Vui lòng gán nhãn thủ công trong Studio."

== KỊCH BẢN 2: MẤT KẾT NỐI MẠNG KHI ĐANG GHI ÂM TRỰC TIẾP ==
UI -> UI: Phát hiện mất kết nối WebSocket đột ngột (Network drop)
UI -> UI: Tự động chuyển hướng lưu audio chunks vào bộ nhớ IndexedDB của trình duyệt
... Mạng Internet phục hồi ...
UI -> Worker: Tự động kết nối lại WebSocket thành công
UI -> Worker: Gửi bù liên tục toàn bộ các audio chunks đã đệm từ IndexedDB
Worker -> Worker: Đồng bộ dữ liệu nối tiếp, tiếp tục xử lý không làm hỏng file âm thanh

== KỊCH BẢN 3: DỊCH VỤ CLOUD LLM TẠM THỜI QUÁ TẢI (429 / TIMEOUT) ==
Worker -> ExtService: Gửi yêu cầu sinh tóm tắt cuộc họp (GPT-4o-mini)
ExtService --> Worker: 429 Too Many Requests (Rate limit reached)

loop Thử lại có giãn cách hàm mũ (Exponential Backoff tối đa 3 lần)
    Worker -> Worker: Chờ giãn cách thời gian (2s, 4s, 8s)
    Worker -> ExtService: Thử lại yêu cầu tóm tắt
end
ExtService --> Worker: Phản hồi thành công (200 OK kèm JSON biên bản)
Worker --> UI: Trả về kết quả tóm tắt và Action Items bình thường
@enduml
```

---

## 7. Luồng 6: Chia sẻ & Phân quyền qua Link (UC-07: Share Meeting & Access Control)

Mô tả quá trình Chủ cuộc họp (Owner) phát hành liên kết chia sẻ bảo mật với lựa chọn quyền (`Viewer` hoặc `Editor`), cách hệ thống kiểm soát quyền truy cập tại API Middleware và quy trình thu hồi liên kết (Revoke).

```plantuml
@startuml
autonumber
scale max 850 width
skinparam maxMessageSize 130
skinparam responseMessageBelowArrow true

actor "Meeting Owner" as Owner
boundary "Frontend UI\n(Share Modal)" as UI
control "Backend API\n(FastAPI Router)" as API
control "Auth & Access\nMiddleware" as Auth
database "PostgreSQL\n(meeting_shares)" as DB
actor "Collaborator\n(Editor / Viewer)" as Collab
boundary "Meeting View UI" as ViewUI

== GIAI ĐOẠN 1: TẠO VÀ PHÂN QUYỀN LINK CHIA SẺ ==
Owner -> UI: Mở hộp thoại Share, chọn quyền (permission="edit")
UI -> API: POST /api/v1/meetings/{id}/shares {"permission": "edit"}
API -> API: Sinh chuỗi cryptographic token ngẫu nhiên (UUIDv4)
API -> DB: INSERT INTO meeting_shares (meeting_id, token, permission, is_revoked=false)
DB --> API: Xác nhận đã lưu bản ghi chia sẻ
API --> UI: Trả về URL hoàn chỉnh kèm share token
UI -> UI: Tự động sao chép liên kết vào Clipboard
UI --> Owner: Hiển thị thông báo "Đã sao chép link chia sẻ (Quyền Chỉnh sửa)"

== GIAI ĐOẠN 2: CỘNG TÁC VIÊN TRUY CẬP VÀ XÁC THỰC QUYỀN ==
Owner -> Collab: Gửi liên kết chia sẻ (qua Chat / Email)
Collab -> ViewUI: Mở liên kết cuộc họp trên trình duyệt
ViewUI -> API: GET /api/v1/meetings/shared/{token}
API -> Auth: Xác thực token chia sẻ
Auth -> DB: SELECT * FROM meeting_shares WHERE token = :token AND is_revoked = false

alt Token hợp lệ & Đang hoạt động
    DB --> Auth: Trả về meeting_id và permission ("edit")
    Auth --> API: Gán ngữ cảnh phân quyền (Session Context: role=Editor)
    API -> DB: Lấy toàn bộ dữ liệu cuộc họp (audio, segments, summary)
    DB --> API: Bundle dữ liệu cuộc họp
    API --> ViewUI: Trả về dữ liệu + quyền EditMode = true
    ViewUI --> Collab: Hiển thị Studio cho phép chỉnh sửa văn bản & xuất file
else Token không hợp lệ HOẶC đã bị thu hồi
    DB --> Auth: Không tìm thấy HOẶC is_revoked = true
    Auth --> API: Từ chối truy cập (Access Denied)
    API --> ViewUI: HTTP 403 Forbidden {"detail": "Liên kết không hợp lệ hoặc đã hết hạn"}
    ViewUI --> Collab: Hiển thị màn hình từ chối truy cập
end

== GIAI ĐOẠN 3: KIỂM SOÁT THAO TÁC GHI THEO QUYỀN ==
opt Nếu người truy cập có quyền "Viewer" cố tình gửi request sửa
    Collab -> ViewUI: Gửi yêu cầu cập nhật phân đoạn
    ViewUI -> API: PUT /api/v1/transcripts/{id} (Kèm Viewer token)
    API -> Auth: Kiểm tra quyền hạn của token
    Auth --> API: Phát hiện token mang quyền "view" (Không có quyền ghi)
    API --> ViewUI: HTTP 403 Forbidden {"detail": "Quyền chỉ xem, không thể chỉnh sửa"}
    ViewUI --> Collab: Hiển thị cảnh báo từ chối sửa đổi
end

== GIAI ĐOẠN 4: THU HỒI LINK CHIA SẺ (REVOKE LINK) ==
Owner -> UI: Nhấn nút "Thu hồi liên kết" (Revoke Share Link)
UI -> API: DELETE /api/v1/meetings/{id}/shares/{share_id}
API -> DB: UPDATE meeting_shares SET is_revoked = true WHERE id = :share_id
DB --> API: Bản ghi đã cập nhật
API --> UI: Xác nhận thu hồi thành công
UI --> Owner: Thông báo liên kết đã bị vô hiệu hóa
@enduml
```

