# Tài Liệu Kiến Trúc Hệ Thống (System Architecture Document)

**Dự án:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp (Meeting Transcription, Summarization, and Question Answering System)  
**Tiêu chuẩn áp dụng:** arc42 (v8.2), C4 Model (Simon Brown), IEEE 42010  
**Tài liệu tham chiếu:** [docs/01-requirements/srs.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/01-requirements/srs.md), [docs/02-research-tech/tech-stack-justification.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/tech-stack-justification.md)  
**Phiên bản:** 2.0 · **Ngày cập nhật:** 2026-10-22  

---

## 1. Giới Thiệu & Bối Cảnh Hệ Thống (Scope & Context - arc42 Section 1 & 3)

### 1.1. Mục tiêu kiến trúc
Hệ thống giải quyết bài toán tự động hóa biên bản cuộc họp tiếng Việt đa người nói, hướng tới 3 chỉ số chất lượng then chốt:
1. **Rút ngắn thời gian lập biên bản:** Giảm thời gian hoàn thành biên bản cuộc họp 60 phút từ 45 phút xuống dưới 10 phút (North Star Metric).
2. **Xử lý hai lượt tối ưu (Two-Pass ASR):** Bản nháp trực tiếp có độ trễ $\le 1.5$s; bản lưu trữ chính thức đạt RTF $\le 0.15$ trên GPU.
3. **Truy vấn RAG minh bạch có bằng chứng:** 100% câu khẳng định kèm trích dẫn mốc thời gian `[Speaker, mm:ss]` chính xác đến từng giây.

### 1.2. Ràng buộc kiến trúc cốt lõi (Kiến trúc Tối giản API-First)
- **Hạ tầng CPU tinh gọn:** Loại bỏ hoàn toàn yêu cầu thuê máy chủ GPU chuyên dụng đắt đỏ. Toàn bộ hệ thống chạy mượt mà trên máy chủ CPU tiêu chuẩn (2-4 vCPU, 4-8GB RAM) hoặc laptop cá nhân qua Docker Compose tiêu chuẩn.
- **Tầng Xử lý Âm thanh Hợp nhất (Pass 2):** Ủy thác toàn bộ tác vụ nhận dạng ASR, phân tách người nói (Speaker Diarization) và bóc tách mốc từ (Word Timestamps) cho **Gladia API (Solaria-1)**. Giải pháp này giúp triệt tiêu mã căn chỉnh phức tạp, tiết kiệm hơn 85% chi phí hạ tầng và tối ưu xử lý đàm thoại tiếng Việt có pha trộn từ ngữ công nghệ (Code-switching).
- **Tầng LLM & Tóm tắt:** Sử dụng **Google Gemini 2.0 Flash** (kết hợp **OpenAI GPT-4o-mini** làm adapter dự phòng) với context 1M tokens, chi phí siêu rẻ (~50 VNĐ/cuộc họp) và hỗ trợ Structured Outputs JSON Schema.
- **Thành phần chạy Local trên CPU (0 VNĐ):** `Silero VAD v6` (ONNX) lọc tiếng người và `sherpa-onnx Zipformer-vi INT8` cho Pass 1 streaming draft; `multilingual-e5-small` (384 dims) chạy trực tiếp trên CPU để nhúng vector vào PostgreSQL.
- **Cơ sở dữ liệu duy nhất:** Sử dụng duy nhất **PostgreSQL 16/17 tích hợp extension `pgvector`** cho toàn bộ dữ liệu quan hệ, vector 384 chiều và Full-Text Search; đảm bảo tính toàn vẹn giao dịch ACID.

### 1.3. C4 Level 1: System Context Diagram

Sơ đồ ngữ cảnh hệ thống xác định phạm vi ranh giới và các tác nhân tương tác với hệ thống:

```plantuml
@startuml
!includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

scale max 850 width
skinparam wrapWidth 220
LAYOUT_WITH_LEGEND()

title System Context Diagram - Meeting Voice Assistant (C4 Level 1)

Person(owner, "Chủ cuộc họp (Meeting Owner)", "Người tải file hoặc ghi âm trực tiếp, sở hữu toàn quyền cuộc họp và quản lý liên kết chia sẻ (Shareable Link).")
Person(collaborator, "Thành viên nhận link (Collaborator)", "Người truy cập qua liên kết chia sẻ với quyền Chỉnh sửa (Editor: sửa văn bản, đổi tên người nói) hoặc quyền Xem (Viewer: nghe audio, đọc tóm tắt, hỏi đáp RAG).")

System(mva_system, "Meeting Voice Assistant System", "Hệ thống phiên âm tiếng Việt hai lượt, phân tách người nói, tóm tắt tự động và hỏi đáp RAG có trích dẫn mốc giây.")

System_Ext(llm_cloud, "External Cloud LLM API", "OpenAI (GPT-4o-mini), Anthropic (Claude 3.5 Haiku), Google (Gemini 2.0 Flash) qua lớp Adapter.")
System_Ext(mic_device, "Client Audio Worklet", "Microphone thu nhận tín hiệu âm thanh PCM 16 kHz Mono từ trình duyệt của người dùng.")

Rel(owner, mva_system, "Ghi âm, tải file, quản lý link chia sẻ, toàn quyền sửa và xóa", "HTTPS / WSS")
Rel(collaborator, mva_system, "Xem biên bản, nghe audio, hỏi đáp RAG, chỉnh sửa (nếu là Editor)", "HTTPS / SSE")
Rel(mic_device, mva_system, "Truyền luồng audio chunks 100ms", "WebSocket (WSS)")
Rel(mva_system, llm_cloud, "Gửi prompt tóm tắt & context RAG (Structured Outputs)", "HTTPS JSON API")
@enduml
```

---

## 2. Kiến Trúc Phân Rã Container (Building Block View Level 1 - arc42 Section 5)

Hệ thống được thiết kế theo kiến trúc Microservices phân tách độc lập giữa tầng phục vụ nghiệp vụ Web và tầng tính toán AI nặng:

### 2.1. C4 Level 2: Container Diagram

```plantuml
@startuml
!includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

scale max 850 width
skinparam wrapWidth 220
LAYOUT_WITH_LEGEND()

title Container Diagram - Meeting Voice Assistant (C4 Level 2)

Person(user, "Người dùng", "Thư ký, quản lý hoặc thành viên tham dự cuộc họp")

System_Boundary(c1, "Meeting Voice Assistant Platform") {
    Container(proxy, "Reverse Proxy Gateway", "Nginx / Caddy", "Điều phối lưu lượng, kết thúc TLS, cân bằng tải, định tuyến REST, SSE và WebSocket")
    Container(frontend, "Frontend Web Application", "Next.js 14, React, TypeScript, Tailwind CSS, wavesurfer.js", "Giao diện người dùng: Audio Intake, Transcript Studio đồng bộ mốc từ Karaoke, Chat RAG và Quản lý Action Items")
    Container(backend, "Backend API Service", "FastAPI, Python 3.12, SQLAlchemy 2.0 (asyncpg), Pydantic v2", "Cung cấp REST API nghiệp vụ, điều phối phiên, phân phối sự kiện qua SSE Gateway, đóng gói RAG Engine và LLM Adapter")
    Container(ai_service, "AI Worker & Live Gateway", "Python 3.12, FastAPI, Celery, Silero VAD, sentence-transformers CPU", "Xử lý âm thanh: Pass 1 Live ASR (Zipformer-vi INT8 CPU), Pass 2 Batch Pipeline (ủy thác Gladia API v2 Solaria-1 trọn gói ASR + Diarization + Timestamps), Embedding e5-small CPU")
    ContainerDb(db, "Primary Database & Vector Store", "PostgreSQL 16/17 + pgvector + pg_trgm", "Lưu trữ dữ liệu quan hệ (meetings, segments, summaries, actions) và vector 384-dim (transcript_embeddings) với HNSW Index")
    ContainerDb(redis, "Task Queue & Event Broker", "Redis 7 (Alpine)", "Điều phối hàng đợi Celery Worker và lưu vết lịch sử tiến độ qua Redis Streams (hỗ trợ Last-Event-ID)")
    ContainerDb(storage, "Audio Object Storage", "SeaweedFS (S3-compatible) / Local Storage", "Lưu trữ tệp âm thanh gốc và các tệp âm thanh chuẩn hóa 16 kHz Mono")
}

System_Ext(gladia_cloud, "Gladia Audio Cloud API", "Dịch vụ nhận dạng giọng nói, phân tách người nói và mốc từ theo thời gian thực (Solaria-1)")
System_Ext(llm_cloud, "Cloud LLM Provider", "Google Gemini 2.0 Flash / OpenAI GPT-4o-mini API")

Rel(user, frontend, "Tương tác giao diện trình duyệt", "HTTPS")
Rel(frontend, proxy, "Yêu cầu API, luồng sự kiện và âm thanh", "HTTPS / WSS")

Rel(proxy, frontend, "Chuyển tiếp tài nguyên tĩnh và trang", "HTTP :3000")
Rel(proxy, backend, "Định tuyến /api/v1 và /events", "HTTP :8000")
Rel(proxy, ai_service, "Định tuyến luồng ghi âm trực tiếp /ws/live", "WS :8001")

Rel(backend, db, "Thực thi CRUD và Hybrid Search RRF", "asyncpg / SQL :5432")
Rel(backend, redis, "Đẩy task xử lý và đọc sự kiện tiến độ", "Redis Protocol :6379")
Rel(backend, storage, "Lưu file tải lên và sinh Presigned URL", "S3 API / HTTP :8333")
Rel(backend, llm_cloud, "Gửi prompt tóm tắt & hỏi đáp RAG", "HTTPS JSON")

Rel(ai_service, redis, "Nhận Celery task và xuất sự kiện Redis Streams", "Redis Protocol :6379")
Rel(ai_service, storage, "Đọc file âm thanh nguồn để xử lý", "S3 API / Local I/O")
Rel(ai_service, gladia_cloud, "Gửi audio phân tích Pass 2 (ASR + Diarization)", "HTTPS API :443")
Rel(ai_service, db, "Lưu segments, mốc từ và vector embeddings", "asyncpg / SQL :5432")
@enduml
```

### 2.2. Trách nhiệm các Container trong Cụm Docker Compose

| Tên Container | Hình ảnh / Công nghệ | Cổng ánh xạ | Trách nhiệm chính |
|---|---|---|---|
| **meeting_nginx** | Nginx:alpine | 80, 443 | Kết thúc TLS/SSL, Reverse Proxy định tuyến `/` tới frontend, `/api/` tới backend-api, duy trì WebSocket `/api/v1/live/ws`, hỗ trợ HTTP Range streaming. |
| **meeting_frontend** | Next.js 14, React 18, TailwindCSS | 3000 | Giao diện người dùng: Dashboard danh sách cuộc họp, ProjectSelector, Transcript Studio đồng bộ timeline audio scrubbing, Chat RAG trích dẫn, Modal thanh toán VietQR. |
| **meeting_backend_api** | FastAPI, Python 3.12, asyncpg | 8000 | Xác thực JWT (Argon2/bcrypt), phân quyền RBAC, quản lý dự án, tiếp nhận upload audio, phát luồng Range, tạo đơn hàng VietQR và xử lý Webhook SePay. |
| **meeting_celery_worker** | Celery 5.4+, Python 3.12 | Nội bộ | Tiến trình chạy nền điều phối Pass 2: đọc audio từ `/tmp/meeting_storage`, gọi AI Service (Gladia ASR & Diarization), gọi Gemini Summarize, lưu CSDL và trừ Quota. |
| **meeting_ai_service** | FastAPI, Python 3.12, PyTorch CPU | 8001 | Đóng gói bộ điều phối Gladia API v2 (ASR + Diarization), bộ truy xuất ngữ nghĩa lai Hybrid Search (e5-small + RRF), và bộ sinh tóm tắt/hỏi đáp Gemini 2.0 Flash. |
| **meeting_postgres** | PostgreSQL 16 + pgvector:pg16 | 5432 | Cơ sở dữ liệu duy nhất lưu trữ 16 bảng dữ liệu quan hệ ACID và hỗ trợ chỉ mục vector HNSW. |
| **meeting_redis** | Redis 7:alpine | 6379 | Message broker cho Celery Worker và bộ nhớ đệm phục vụ đếm hạn mức/phiên làm việc. |

---

## 3. Kiến Trúc Phân Rã Thành Phần (Building Block View Level 2 - arc42 Section 5)

### 3.1. C4 Level 3: Component Diagram - Backend API Service

Dịch vụ `backend-api` được xây dựng theo kiến trúc phân lớp sạch (Clean Architecture / Hexagonal Architecture):

```plantuml
@startuml
!includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

scale max 850 width
skinparam wrapWidth 220
LAYOUT_WITH_LEGEND()

title Component Diagram - Backend API Service (C4 Level 3)

Container_Boundary(api_boundary, "Backend API Service (FastAPI)") {
    Component(meeting_router, "Meeting API Router", "FastAPI APIRouter", "Tiếp nhận tệp audio, quản lý thông tin cuộc họp, tạo phiên")
    Component(transcript_router, "Transcript API Router", "FastAPI APIRouter", "Truy xuất danh sách phân đoạn, cập nhật inline editing, đổi tên speaker")
    Component(chat_router, "RAG Chat Router", "FastAPI APIRouter", "Tiếp nhận câu hỏi truy vấn, khởi tạo luồng trả lời qua SSE")
    Component(export_router, "Export Router", "FastAPI APIRouter", "Tổng hợp và xuất biên bản cuộc họp ra DOCX, TXT, JSON, SRT")
    
    Component(sse_gateway, "SSE Gateway Manager", "Async Event Streamer", "Lắng nghe Redis Streams và truyền trực tiếp tiến độ/token về client")
    Component(rag_engine, "RAG Orchestration Core", "Python Domain Service", "Query condensation, Hybrid Search builder (Dense + FTS), RRF fusion, Window retrieval")
    Component(citation_mgr, "Citation Binding Engine", "Python Service", "Đối soát mã thẻ trích dẫn [S...] với CSDL, trích xuất mốc giây start_ms/end_ms")
    Component(llm_adapter, "LLM Multi-provider Adapter", "Adapter Pattern", "Giao diện chuẩn hóa tương tác với OpenAI GPT-4o-mini, Anthropic, Google Gemini")
    Component(tx_manager, "Transaction Manager", "Unit of Work / SQLAlchemy", "Đảm bảo tính nguyên tử: Sửa text -> Sinh vector mới -> Lưu DB trong 1 Transaction")
}

ContainerDb(db, "PostgreSQL + pgvector", "Database")
ContainerDb(redis, "Redis Streams", "Event Broker")
ContainerDb(storage, "Object Storage", "Audio Store")
System_Ext(llm_ext, "External Cloud LLM", "Cloud API")

Rel(meeting_router, storage, "Lưu file tải lên", "S3 Client")
Rel(meeting_router, redis, "Đẩy task ProcessAudio vào Celery", "Redis Client")
Rel(meeting_router, db, "Ghi trạng thái cuộc họp", "SQLAlchemy")

Rel(transcript_router, tx_manager, "Yêu cầu cập nhật phân đoạn", "Internal Call")
Rel(tx_manager, db, "Commit phân đoạn mới & vô hiệu hóa chunk cũ", "ACID Tx")

Rel(chat_router, rag_engine, "Chuyển tiếp câu hỏi RAG", "Internal Call")
Rel(rag_engine, db, "Thực thi truy vấn Dense + Lexical RRF", "SQL Query")
Rel(rag_engine, llm_adapter, "Gửi prompt kèm ngữ cảnh", "Async Call")
Rel(llm_adapter, llm_ext, "Gọi API sinh streaming", "HTTPS")
Rel(llm_adapter, citation_mgr, "Stream token kèm mã thẻ [S...]", "Internal Stream")
Rel(citation_mgr, sse_gateway, "Đóng gói sự kiện SSE kèm timestamp", "Internal Stream")

Rel(sse_gateway, redis, "XREADGROUP từ Redis Streams", "Redis Protocol")
@enduml
```

### 3.2. C4 Level 3: Component Diagram - AI Service & Celery Worker

Phân hệ xử lý AI chịu trách nhiệm biến đổi tín hiệu âm thanh thô thành phân đoạn văn bản có cấu trúc và vector ngữ nghĩa:

```plantuml
@startuml
!includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

scale max 850 width
skinparam wrapWidth 220
LAYOUT_WITH_LEGEND()

title Component Diagram - AI Service & Worker (C4 Level 3 - API-First)

Container_Boundary(ai_boundary, "AI Service & Worker Layer (CPU)") {
    Component(rt_gateway, "Realtime WS Gateway", "FastAPI WebSocket", "Tiếp nhận luồng PCM 16kHz mono 100ms từ trình duyệt")
    Component(live_vad, "Silero VAD Live Filter", "Silero VAD v6 ONNX", "Lọc khung tiếng người trên CPU, cắt ranh giới câu nói (threshold=0.55)")
    Component(live_asr, "Zipformer-vi Engine", "sherpa-onnx INT8 RNN-T", "Pass 1: Giải mã nháp trực tiếp trên CPU (độ trễ <= 1.5s, RTF ~0.01)")
    
    Component(celery_worker, "Audio Pipeline Task Worker", "Celery Task Runner", "Điều phối chuỗi xử lý Pass 2 không cần GPU")
    Component(gladia_client, "Gladia API Client", "Gladia v2 SDK / httpx", "Pass 2: Gửi file audio, nhận kết quả trọn gói ASR + Diarization + Timestamps")
    Component(gemini_gen, "Gemini Summary Generator", "Google Gemini 2.0 Flash / OpenAI", "Sinh Executive Summary và trích xuất Action Items chuẩn JSON Schema")
    Component(embedder, "Vector Embedding Engine", "multilingual-e5-small CPU", "Sinh vector 384-dim cho từng chunk văn bản theo lượt nói trên CPU")
}

ContainerDb(redis, "Redis Streams", "Broker & Progress")
ContainerDb(db, "PostgreSQL + pgvector", "Database")
ContainerDb(storage, "Object Storage", "Audio Store")
System_Ext(gladia_ext, "Gladia Audio Cloud API", "Dịch vụ ASR + Diarization ngoài")
System_Ext(gemini_ext, "Google Gemini Cloud API", "Dịch vụ LLM ngoài")

Rel(rt_gateway, live_vad, "Truyền khung audio 32ms", "In-memory")
Rel(live_vad, live_asr, "Gửi speech buffer khi phát hiện lời nói", "In-memory")
Rel(live_asr, redis, "Phát sự kiện segment.draft_partial/final", "Redis Streams")

Rel(celery_worker, storage, "Đọc file âm thanh nguồn", "S3 / File I/O")
Rel(celery_worker, gladia_client, "1. Yêu cầu xử lý audio", "Async Call")
Rel(gladia_client, gladia_ext, "2. Upload và chạy transcription job", "HTTPS /v2/pre-recorded")
Rel(gladia_ext, gladia_client, "3. Trả về utterances, speaker và words", "JSON Payload")
Rel(gladia_client, db, "4. Lưu transcript_segments (source=final)", "SQL Insert")
Rel(celery_worker, gemini_gen, "5. Yêu cầu tóm tắt toàn bộ transcript", "Async Call")
Rel(gemini_gen, gemini_ext, "6. Prompt trích xuất structured summary", "HTTPS JSON")
Rel(gemini_gen, db, "7. Lưu summary và action items", "SQL Insert")
Rel(gladia_client, embedder, "8. Chuyển văn bản theo lượt nói", "Text Batches")
Rel(embedder, db, "9. Ghi transcript_embeddings vector(384)", "SQL Insert")
Rel(celery_worker, redis, "Cập nhật tiến độ xử lý (0% - 100%)", "Redis Streams")
@enduml
```

---

## 4. Kiến Trúc Triển Khai Hạ Tầng (Deployment View - arc42 Section 7)

### 4.1. C4 Level 4: Deployment Diagram trên Máy Chủ GPU ~24GB VRAM

```plantuml
@startuml
!includeurl https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Deployment.puml

scale max 850 width
skinparam wrapWidth 220
LAYOUT_WITH_LEGEND()

title Deployment Diagram - Dedicated GPU Server ~24GB VRAM (C4 Level 4)

Deployment_Node(host, "Dedicated AI Server", "Ubuntu 22.04 LTS, 8 vCPU x86_64, 32GB RAM, 1TB NVMe SSD") {
    
    Deployment_Node(gpu, "NVIDIA GPU Hardware", "RTX 3090 / RTX 4090 / A10G (24GB VRAM GDDR6X, CUDA Compute 8.6+)") {
        Artifact(cuda_rt, "NVIDIA Container Toolkit & CUDA 12.2 Driver", "GPU Passthrough Runtime")
    }

    Deployment_Node(docker, "Docker Engine 26.x & Docker Compose", "Container Virtualization") {
        
        Deployment_Node(c_proxy, "Container: mva-proxy", "nginx:alpine") {
            Artifact(proxy_art, "Nginx Reverse Proxy", "Port 80/443 SSL termination")
        }
        
        Deployment_Node(c_fe, "Container: mva-frontend", "node:18-alpine") {
            Artifact(fe_art, "Next.js 14 Standalone App", "Port 3000")
        }
        
        Deployment_Node(c_be, "Container: mva-backend", "python:3.11-slim") {
            Artifact(be_art, "FastAPI ASGI Application (uvicorn)", "Port 8000 (4 workers)")
        }
        
        Deployment_Node(c_ai, "Container: mva-ai-service", "nvidia/cuda:12.2.2-runtime-ubuntu22.04") {
            Artifact(ai_art, "Celery Worker & WS Gateway", "Port 8001 (GPU Runtime Enabled)")
        }
        
        Deployment_Node(c_db, "Container: mva-postgres", "pgvector/pgvector:pg17") {
            Artifact(db_art, "PostgreSQL 17 + pgvector", "Port 5432, 100GB Data Volume")
        }
        
        Deployment_Node(c_redis, "Container: mva-redis", "redis:7-alpine") {
            Artifact(redis_art, "Redis Server", "Port 6379, AOF Persisted Volume")
        }
        
        Deployment_Node(c_store, "Container: mva-storage", "chrislusf/seaweedfs:latest") {
            Artifact(store_art, "SeaweedFS S3-Compatible Server", "Port 8333 / 9000, 500GB NVMe Volume")
        }
    }
}

Rel(c_ai, cuda_rt, "Cấp quyền truy cập trực tiếp CUDA Tensor Cores", "NVIDIA Container Runtime")
Rel(proxy_art, fe_art, "Chuyển tiếp UI traffic", "HTTP :3000")
Rel(proxy_art, be_art, "Chuyển tiếp API/SSE traffic", "HTTP :8000")
Rel(proxy_art, ai_art, "Chuyển tiếp WS live audio", "HTTP/WS :8001")
Rel(be_art, db_art, "Kết nối CSDL", "TCP :5432")
Rel(be_art, redis_art, "Kết nối Event Broker", "TCP :6379")
Rel(ai_art, db_art, "Ghi dữ liệu kết quả", "TCP :5432")
Rel(ai_art, redis_art, "Nhận task & phát sự kiện", "TCP :6379")
@enduml
```

### 4.2. Bản đồ phân bổ VRAM trên GPU 24GB

Khi vận hành pipeline đầy đủ trên máy chủ GPU 24GB VRAM, tài nguyên được phân bổ như sau:

| Tiến trình / Mô hình hoạt động | Mức chiếm dụng VRAM | Tỷ lệ trên 24GB | Ghi chú vận hành |
|---|---|---|---|
| **CUDA Driver & PyTorch Context** | ~0.8 - 1.0 GB | ~3.8% | Khởi tạo môi trường runtime CUDA |
| **Silero VAD v6 Gatekeeper** | ~0.1 - 0.2 GB | ~0.8% | Xử lý khung 32ms siêu nhẹ trên GPU |
| **sherpa-onnx Zipformer-vi INT8** | ~0.2 - 0.3 GB | ~1.2% | Phục vụ Pass 1 Live ASR |
| **PhoWhisper-medium-ct2 (FP16)** | ~1.8 - 2.2 GB | ~8.3% | Pass 2 Batch ASR giải mã Tensor Cores |
| **pyannote community-1 (CUDA)** | ~2.2 - 2.8 GB | ~10.4% | Phân cụm người nói Dual-Engine 1 |
| **multilingual-e5-small (CUDA)** | ~0.4 - 0.5 GB | ~1.9% | Tính vector 384-dim cho từng chunk |
| **TỔNG ĐỈNH VRAM (1 PIPELINE)** | **~5.5 - 7.0 GB** | **~26.5%** | **Chiếm chưa tới 30% tổng VRAM** |
| **VRAM DỰ PHÒNG TRỐNG (FREE)** | **~17.0 - 18.5 GB** | **~73.5%** | **Cho phép chạy song song 2-3 worker** |

---

## 5. Các Nguyên Lý Kiến Trúc Xuyên Suốt (Cross-cutting Concepts - arc42 Section 8)

### 5.1. Kiến trúc Hai Lượt (Two-Pass Architecture)
- **Vấn đề giải quyết:** Xung đột giữa độ trễ hiển thị văn bản khi đang họp ($\le 1.5$s) và độ chính xác cao của bản lưu trữ lâu dài kèm định danh người nói.
- **Giải pháp:**
  - **Pass 1 (Draft Streaming):** Microphone $\to$ Silero VAD $\to$ `sherpa-onnx Zipformer-vi INT8` (mô hình RNN-T ~75MB). Phát sóng trực tiếp bản nháp không dấu câu/người nói để người dùng có phản hồi thị giác tức thì.
  - **Pass 2 (Offline Batch):** Tệp âm thanh hoàn chỉnh $\to$ FFmpeg $\to$ `PhoWhisper-medium-ct2 FP16` (WER 26.85% hội thoại khó, đủ dấu câu và word-timestamps) kết hợp `pyannote community-1` (min_speakers=2) $\to$ Căn chỉnh Turn-taking $\to$ Sinh Embedding. Bản Pass 2 ghi đè hoàn toàn Pass 1 và là nguồn dữ liệu duy nhất cho RAG.

### 5.2. Cơ chế Đồng bộ Dữ liệu An toàn khi Chỉnh sửa Lời thoại (Compute-then-Commit)
Khi người dùng sửa văn bản hoặc đổi tên người nói trong Transcript Studio:
1. Backend nhận yêu cầu sửa đổi, tính toán trước vector embedding mới cho các chunk bị ảnh hưởng thông qua `multilingual-e5-small`.
2. Mở một **PostgreSQL Transaction** duy nhất:
   - Lưu bản ghi cũ vào bảng lịch sử phiên bản (`transcript_segment_versions`).
   - Cập nhật nội dung mới vào `transcript_segments`.
   - Đánh dấu các chunk cũ `is_active = false`, chèn các chunk vector mới vào `transcript_embeddings`.
   - Đánh dấu bản tóm tắt hiện tại `is_stale = true`.
3. Thực hiện `COMMIT`. Nếu có bất kỳ lỗi nào xảy ra trong quá trình tính toán, transaction rollback hoàn toàn, ngăn chặn tình trạng dữ liệu văn bản một đằng, vector một nẻo.

### 5.3. Cơ chế Dự phòng và Tự động Phục hồi khi có Sự cố (Fault Tolerance & Graceful Fallback)
Hệ thống thiết lập cơ chế chịu lỗi nhiều tầng nhằm đảm bảo không bao giờ dừng đột ngột (crash):
- **Lỗi Hugging Face Token / Pyannote:** Tự động kích hoạt **Engine 2 (Standalone Acoustic Diarizer)** hoặc chuyển về chế độ an toàn gán nhãn `SPEAKER_UNKNOWN` kèm cảnh báo trên UI, bảo toàn 100% văn bản nhận dạng được từ ASR.
- **Mất kết nối mạng WebSocket:** Client tự động lưu các audio chunks vào IndexedDB của trình duyệt; tự động kết nối lại và gửi bù dữ liệu khi đường truyền phục hồi.
- **LLM API Timeout hoặc Rate Limit:** Áp dụng Exponential Backoff Retry (tối đa 3 lần) qua HTTP Client; nếu thất bại hoàn toàn, thông báo lỗi rõ ràng và giữ nguyên trạng thái phiên làm việc.

---

## 6. Bảng Nhật Ký Quyết Định Kiến Trúc Tóm Tắt (ADR Summary - arc42 Section 9)

| Mã ADR | Quyết định kỹ thuật | Lý do lựa chọn cốt lõi |
|---|---|---|
| **ADR-001** | Phân tách `backend-api` và `ai-service` | Tách biệt ranh giới tài nguyên; cho phép backend nhẹ nhàng scale độc lập, AI worker gắn kết chặt với runtime GPU CUDA. |
| **ADR-002** | Mô hình hai lượt: Zipformer-vi $\to$ PhoWhisper | Thỏa mãn song song hai tiêu chí: Phản hồi thị giác thời gian thực ($\le 1.5$s) và độ chính xác lưu trữ cao kèm word-timestamps. |
| **ADR-003** | PostgreSQL + pgvector làm CSDL duy nhất | Đảm bảo toàn vẹn ACID trong 1 transaction khi sửa transcript; loại bỏ rủi ro bất đồng bộ giữa DB quan hệ và DB vector rời. |
| **ADR-004** | Redis Streams thay cho Pub/Sub thuần | Lưu vết lịch sử sự kiện tiến độ theo thời gian; hỗ trợ khôi phục kết nối SSE liền mạch với `Last-Event-ID`. |
| **ADR-005** | Chuẩn hóa PhoWhisper-medium-ct2 FP16 | Giảm WER xuống 26.85% trên hội thoại khó; RTF ~0.03x nhờ tăng tốc Tensor Cores CUDA; tiêu thụ chỉ ~2.0 GB VRAM. |
| **ADR-006** | Dùng duy nhất Cloud LLM API qua Adapter | Tiết kiệm 10–18 GB VRAM cho GPU 24GB; tận dụng Structured Outputs ép kiểu JSON Schema chuẩn 100%; không vendor lock-in. |
| **ADR-007** | Dual-Engine Diarization ép min_speakers=2 | Ngăn ngừa lỗi gom toàn bộ cuộc họp về 1 người nói; cung cấp phương án dự phòng Zero-Token khi thiếu kết nối Hugging Face. |
