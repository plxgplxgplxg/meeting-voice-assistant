# Chương 4: Hiện Thực Hóa & Cài Đặt Hệ Thống

## 4.1. Môi Trường & Công Cụ Phát Triển
Docker Compose đóng gói Nginx, Next.js 14 standalone, hai ứng dụng FastAPI, Celery, PostgreSQL 16/pgvector và Redis 7. AI Service dùng PyTorch/sentence-transformers cho multilingual E5; ASR thực gọi Gladia thay vì Faster-Whisper self-host.

## 4.2. Cài Đặt Các Module Cốt Lõi
- Xử lý âm thanh và pipeline ASR/Diarization.
- Quản lý dự án/cuộc họp, lưu audio shared volume và tác vụ Celery.
- Transcript Studio, summary/action items và export.
- Module RAG hybrid in-memory và citation timestamp.
- JWT auth, share token, quota và VietQR/SePay.
- Giao diện người dùng theo chuẩn Clean Minimalist.

## 4.3. Giới hạn implementation

WebSocket chỉ sinh transcript mô phỏng; `/live` ghi WebM rồi xử lý batch. Production còn cần authorization thống nhất, tắt fallback demo, Alembic, cookie HttpOnly và browser E2E.
