# KIẾN TRÚC API-FIRST CHO MEETING VOICE ASSISTANT

**Cập nhật theo implementation:** 16/11/2026

## 1. Phân bổ xử lý

| Năng lực | Adapter hiện tại | Chạy ở đâu | GPU EC2 |
|---|---|---|---|
| Upload/lưu audio | FastAPI + filesystem volume | EC2 | Không |
| Queue/orchestration | Redis + Celery | EC2 | Không |
| ASR/diarization/timestamp | Gladia API v2 | Cloud provider | Không |
| Embedding | `intfloat/multilingual-e5-small` | AI Service CPU | Không |
| Lexical ranking | Python/Numpy | AI Service CPU | Không |
| Summary/RAG generation | Gemini hoặc OpenAI adapter | Cloud provider | Không |
| Export DOCX/subtitle | Python | Backend CPU | Không |

## 2. Gladia adapter

`GladiaAudioPipeline` thực hiện:

1. Upload file local lên `/v2/upload`.
2. Tạo job `/v2/pre-recorded` với tiếng Việt, code switching và diarization.
3. Poll `result_url` tối đa 300 giây.
4. Chuyển utterance thành `speaker`, `start`, `end`, `text`, confidence và word timestamps.

Nếu key rỗng hoặc `AUDIO_PIPELINE_ENGINE=mock`, adapter trả segment demo. Production E2E phải dùng `gladia` và key thật.

## 3. LLM adapter

`OpenAICompatibleLLMClient` dùng một interface cho:

- Google Gemini OpenAI-compatible endpoint, model hiện hardcode `gemini-2.0-flash`.
- OpenAI Chat Completions, model hiện hardcode `gpt-4o-mini`.

`LLM_PROVIDER` chọn `gemini` hoặc `openai`; key tương ứng là `GEMINI_API_KEY` hoặc `OPENAI_API_KEY`.

Model hardcode là rủi ro vòng đời. Việc còn lại là đưa model name thành biến môi trường và kiểm tra model còn được provider hỗ trợ trước deploy.

## 4. Retrieval hiện tại

`MeetingRetriever` nhận danh sách transcript segment từ Backend cho mỗi câu hỏi, sau đó kết hợp:

- lexical token overlap;
- cosine similarity từ multilingual E5;
- xếp hạng hybrid trong memory.

PostgreSQL cài extension pgvector nhưng code hiện chưa lưu embedding hoặc tạo HNSW index. Vì vậy kiến trúc hiện tại phù hợp meeting nhỏ/trung bình; chưa phải persistent vector RAG.

## 5. Cost và capacity

Repo không chứa bảng giá provider có thể dùng làm cam kết vì giá/model thay đổi theo thời gian. Khi chuẩn bị demo cần ghi lại:

- đơn giá Gladia tại ngày chạy;
- quota/rate limit tài khoản;
- đơn giá token Gemini/OpenAI;
- thời lượng audio thử nghiệm;
- chi phí EC2/EBS/data transfer.

Không suy ra chi phí production từ dữ liệu fallback hoặc free tier.

## 6. Trade-off

| Lợi ích | Đánh đổi |
|---|---|
| Không cần GPU EC2 | Phụ thuộc mạng/provider/quota |
| Pipeline code nhỏ, dễ deploy | Audio phải gửi sang dịch vụ ngoài |
| Có adapter mock để test | Fallback có thể che lỗi cấu hình |
| Có thể đổi Gemini/OpenAI | Model name và payload vẫn cần quản lý vòng đời |
| Embedding CPU tại chỗ | Image AI lớn, cold start và RAM cao |

## 7. Điều kiện vận hành production

- Có sự đồng ý/chính sách phù hợp trước khi gửi nội dung cuộc họp cho provider.
- Tắt hoặc giám sát chặt fallback demo.
- Log request ID và provider error nhưng không log secret/audio content nhạy cảm.
- Đặt timeout/retry/backoff; hiện Gladia có polling nhưng chưa có retry policy tổng thể.
- Theo dõi queue depth, meeting stale ở `processing`, latency và cost.
- Pin/kiểm thử model name định kỳ.
