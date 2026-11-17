# KIẾN TRÚC API-FIRST CHO MEETING VOICE ASSISTANT

**Cập nhật theo implementation:** 17/11/2026

## 1. Phân bổ xử lý

| Năng lực | Adapter hiện tại | Chạy ở đâu | GPU EC2 |
|---|---|---|---|
| Upload/lưu audio | FastAPI + filesystem volume | EC2 | Không |
| Kiểm tra audio (thời lượng, codec) | `ffprobe` | Worker | Không |
| Queue/orchestration | Redis + Celery + transactional outbox | EC2 | Không |
| ASR/diarization/timestamp | Gladia API v2 (bất đồng bộ: submit rồi poll) | Cloud provider | Không |
| Embedding | `intfloat/multilingual-e5-small` (384 chiều) | AI Service CPU | Không |
| Lưu vector và tìm kiếm lai | pgvector (HNSW cosine) + `tsvector` (GIN), hợp nhất RRF | PostgreSQL trên EC2 | Không |
| Summary/RAG generation | Gemini hoặc OpenAI adapter | Cloud provider | Không |
| Agent (tool calling) | LangGraph + ChatOpenAI (endpoint tương thích OpenAI) | AI Service | Không |
| Export DOCX/SRT/Markdown | Python (registry renderer) | Backend CPU | Không |

## 2. Gladia adapter

`GladiaAudioPipeline` được tách thành hai bước để Worker không bị chiếm khi provider chậm:

1. `submit(storage_key)`: upload file lên `/v2/upload`, tạo job `/v2/pre-recorded` (tiếng Việt, code switching, diarization), trả về `provider_job_id`.
2. `get_result(provider_job_id)`: trả `processing`, `completed` (kèm utterance) hoặc `failed`.

Backend lưu `provider_job_id` trong dòng `processing_jobs`; Worker poll bằng cơ chế Celery retry (`StepOutcome.retry_in`) thay vì vòng lặp chờ trong một tác vụ. Tổng thời gian chờ tối đa theo `GLADIA_MAX_WAIT_SECONDS` (mặc định 1800 giây). Utterance được chuyển thành `speaker`, `start`, `end`, `text`, confidence và word timestamps.

Engine `mock` chỉ tồn tại ở `ENVIRONMENT=development`; production từ chối khởi động với engine này. Meeting sinh bởi mock được gắn `is_demo`.

## 3. LLM adapter

`OpenAICompatibleLLMClient` (sinh tóm tắt, trả lời RAG) và `build_chat_model` (agent) dùng cùng một cấu hình provider:

- Google Gemini qua endpoint OpenAI-compatible, model mặc định `gemini-2.0-flash`.
- OpenAI Chat Completions, model mặc định `gpt-4o-mini`.

`LLM_PROVIDER` chọn `gemini` hoặc `openai`; key tương ứng là `GEMINI_API_KEY` hoặc `OPENAI_API_KEY`. Mỗi lần gọi LLM ghi một dòng log có cấu trúc: provider, model, độ trễ, số token (không ghi nội dung).

Hạn chế còn lại: tên model được gán cố định theo provider trong code. Cần đưa vào biến môi trường và kiểm tra model còn được provider hỗ trợ trước khi deploy.

## 4. Retrieval

Retrieval nằm ở Backend, không còn nằm trong AI Service:

1. Bước `index` chia transcript thành chunk (`chunking.py`, gộp theo lượt nói của từng người, giới hạn số token mỗi chunk), gọi `/embeddings`, lưu vào `transcript_chunks` với cột `embedding vector(384)` và cột sinh `tsv` (`tsvector`).
2. Khi hỏi, Backend nhúng câu hỏi rồi chạy **một câu SQL** hợp nhất hạng cosine (HNSW) và `ts_rank` (GIN) bằng Reciprocal Rank Fusion, lọc `WHERE meeting_id = :id`.
3. Chỉ top-k chunk (kèm khoảng thời gian) được gửi tới `/rag/answer`.

Hệ quả: độ trễ và số token của một câu trả lời không tăng theo độ dài cuộc họp; AI Service không cần nhận cả transcript; chỉ mục được đánh dấu `stale` khi transcript đổi và được dựng lại bởi job `index`.

## 5. Agent

Agent chạy trong AI Service, nhận yêu cầu `POST /agent/turn` từ Backend (SSE) và gọi công cụ ngược về `/internal/agent/v1` của Backend bằng `X-Service-Token` cùng token ủy quyền ngắn hạn. Công cụ ghi chỉ tạo đề xuất, con người duyệt qua endpoint công khai. Chi tiết xem [system-architecture.md](system-architecture.md#agent-runtime) và [sequence-diagrams.md](sequence-diagrams.md#6-lượt-trợ-lý-với-đề-xuất-và-phê-duyệt).

## 6. Cost và capacity

Repo không chứa bảng giá provider có thể dùng làm cam kết vì giá/model thay đổi theo thời gian. Khi chuẩn bị demo cần ghi lại:

- đơn giá Gladia tại ngày chạy;
- quota/rate limit tài khoản;
- đơn giá token Gemini/OpenAI; lượt trợ lý gọi mô hình nhiều lần (tối đa 8 bước) nên tốn token hơn hỏi đáp thuần, đó là lý do tính năng này giới hạn ở gói trả phí;
- thời lượng audio thử nghiệm;
- chi phí EC2/EBS/data transfer.

Không suy ra chi phí production từ dữ liệu giả lập hoặc free tier.

## 7. Trade-off

| Lợi ích | Đánh đổi |
|---|---|
| Không cần GPU EC2 | Phụ thuộc mạng/provider/quota |
| Pipeline code nhỏ, dễ deploy | Audio phải gửi sang dịch vụ ngoài |
| Có adapter mock cho development và test | Mock phải bị khóa ở production (validator khi khởi động) |
| Có thể đổi Gemini/OpenAI | Model name vẫn gán cố định trong code |
| Embedding CPU tại chỗ, vector trong PostgreSQL | Image AI lớn, cold start và RAM cao; chỉ mục cần dựng lại sau khi sửa transcript |
| Agent dùng chung quyền với người dùng | Mỗi lượt gọi LLM nhiều lần, tăng chi phí và độ trễ |

## 8. Điều kiện vận hành production

- Có sự đồng ý/chính sách phù hợp trước khi gửi nội dung cuộc họp cho provider.
- Không dùng engine mock ở production (validator đã chặn).
- Log có `request_id` và lỗi provider nhưng không log secret hay nội dung audio/transcript.
- Timeout/retry/backoff nằm ở bước xử lý (3 lần, luỹ thừa); chưa có dead-letter queue riêng, job hết lượt chuyển `failed` để người dùng thử lại.
- Theo dõi: số sự kiện outbox chưa gửi, meeting kẹt ở `transcribing/summarizing`, độ trễ và chi phí.
- Pin/kiểm thử model name định kỳ.
