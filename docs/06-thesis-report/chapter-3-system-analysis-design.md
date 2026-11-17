# Chương 3: Phân Tích & Thiết Kế Hệ Thống

## 3.1. Phân Tích Yêu Cầu Phần Mềm
Hệ thống có 10 ca sử dụng chính: xác thực, dự án, nạp/xử lý audio, Transcript Studio, summary/action item, RAG, export, share, quota và payment; cùng các use case phụ về ghi microphone, hồ sơ, tìm kiếm và playback.

## 3.2. Thiết Kế Kiến Trúc
Kiến trúc gồm Next.js, FastAPI Backend, Celery Worker, FastAPI AI Service, PostgreSQL, Redis, Nginx và shared audio volume. Gladia xử lý ASR/diarization; Gemini/OpenAI xử lý generation. Phần self-host chạy trên EC2 CPU.

## 3.3. Thiết Kế Cơ Sở Dữ Liệu
Mô hình quan hệ gồm 15 bảng cho user/project, meeting, AI và billing. Extension pgvector được bật nhưng chưa có vector column/HNSW; retrieval hiện tính embedding trong memory. Schema versioned bằng Alembic là hạng mục tiếp theo.
