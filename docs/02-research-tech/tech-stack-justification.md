# Luận Giải Lựa Chọn Công Nghệ (Tech Stack Justification)

## 1. Kiến Trúc Tổng Thể
- **Backend:** FastAPI (Python 3.12+) với async lifespan và dependency injection hiện đại. Phù hợp xử lý I/O không đồng bộ và tích hợp hệ sinh thái AI.
- **Database:** PostgreSQL 16 kết hợp pgvector extension. Cho phép lưu trữ đồng thời dữ liệu quan hệ và vector embeddings trong cùng một hệ quản trị.
- **Hàng đợi tác vụ:** Redis kết hợp Celery / Async workers giúp xử lý các tác vụ âm thanh nặng ngoài tiến trình chính.
- **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS theo phong cách Clean Minimalist.

## 2. So Sánh & Đánh Giá
| Thành phần | Lựa chọn | Phương án thay thế | Lý do lựa chọn |
|---|---|---|---|
| Backend Web | FastAPI | Django / Flask | Tốc độ cao, native async, Pydantic v2 validation, OpenAPI tự động |
| Vector DB | pgvector | Pinecone / Qdrant | Miễn phí, đồng bộ transactional ACID với Postgres, giảm chi phí hạ tầng |
| Frontend | Next.js | Vite + React SPA | App Router tối ưu render, SEO nội bộ, cấu trúc thư mục rõ ràng |
