# Meeting Intelligence System (Trợ Lý Cuộc Họp AI)

Hệ thống phiên âm, tách người nói (diarization), tóm tắt và hỏi đáp nội dung cuộc họp có trích dẫn nguồn.
Đồ án Tốt nghiệp Cử nhân CNTT - Trường CNTT&TT, Đại học Bách Khoa Hà Nội.

## 1. Cấu Trúc Dự Án

- `docs/`: Toàn bộ tài liệu phân tích nghiệp vụ, kiến trúc, đặc tả API, kế hoạch kiểm thử và báo cáo tốt nghiệp.
- `backend-api/`: Dịch vụ Backend nghiệp vụ (FastAPI, SQLAlchemy Async, Redis, Celery).
- `ai-service/`: Dịch vụ AI & Audio chuyên biệt (FastAPI, Faster-Whisper, Pyannote, RAG pgvector).
- `frontend/`: Giao diện người dùng hiện đại, tinh giản (Next.js 14+ App Router, Tailwind CSS).
- `data/`: Dữ liệu audio mẫu tiếng Việt và ground-truth dùng cho đánh giá thử nghiệm.

## 2. Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### Yêu cầu hệ thống
- Docker & Docker Compose
- Python 3.12+ (nếu chạy local)
- Node.js 18+ (nếu chạy local)

### Chạy bằng Docker Compose
```bash
cp .env.example .env
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend API Docs (Swagger): http://localhost:8000/docs
- AI Service Docs (Swagger): http://localhost:8001/docs
