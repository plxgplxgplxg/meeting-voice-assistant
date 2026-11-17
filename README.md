# Meeting Voice Assistant

Web app chuyển audio cuộc họp tiếng Việt thành transcript phân tách người nói, summary/action items, RAG chat có citation và biên bản xuất đa định dạng.

## Stack

- Next.js 14 + TypeScript + Tailwind CSS
- FastAPI + SQLAlchemy async + PostgreSQL 16/pgvector
- Redis + Celery
- Gladia API v2 cho ASR/diarization
- Gemini/OpenAI cho summary và RAG
- Nginx + Docker Compose

## Chạy local

```bash
cp .env.example .env
# Điền key thật nếu muốn kiểm thử AI thật
docker compose up --build -d
docker compose ps
```

- Frontend: `http://localhost:3000`
- Backend Swagger: `http://localhost:8000/docs`
- AI Swagger: `http://localhost:8001/docs`

Thiếu provider key sẽ kích hoạt dữ liệu fallback demo; không coi đó là full E2E.

## Tài liệu chuẩn

- [SRS](docs/01-requirements/srs.md)
- [Use cases](docs/01-requirements/use-cases.md)
- [Kiến trúc hệ thống](docs/03-architecture/system-architecture.md)
- [Database ERD](docs/04-design/database-erd.md)
- [Test plan](docs/05-testing/test-plan.md)
- [Runbook full E2E và AWS EC2](docs/deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md)

## Production Compose

```bash
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

Production chỉ public Nginx ở 80/443. Đọc runbook trước khi bật HTTPS, SePay hoặc dùng dữ liệu nhạy cảm.
