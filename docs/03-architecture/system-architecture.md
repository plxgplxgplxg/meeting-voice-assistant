# Kiến Trúc Hệ Thống (C4 Model)

## 1. Level 1: System Context Diagram
Hệ thống tương tác với Người dùng cuộc họp và các dịch vụ AI bên ngoài.

```mermaid
C4Context
    title System Context diagram for Meeting Intelligence System
    Person(user, "Người dùng cuộc họp", "Thư ký, quản lý hoặc thành viên tham dự cuộc họp")
    System(meeting_system, "Meeting Intelligence System", "Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp")
    System_Ext(llm_api, "LLM Service", "OpenAI / Claude / Gemini API")

    Rel(user, meeting_system, "Ghi âm, xem biên bản, hỏi đáp", "HTTPS / WebSocket")
    Rel(meeting_system, llm_api, "Gửi prompt sinh tóm tắt & RAG", "HTTPS")
```

## 2. Level 2: Container Diagram
Kiến trúc phân rã thành các dịch vụ độc lập:

```mermaid
graph TD
    Client[Frontend: Next.js 14] -->|REST / WebSocket| Backend[Backend API: FastAPI]
    Backend -->|Async Task| Redis[Redis Queue & Pub/Sub]
    Backend -->|CRUD & Relations| DB[(PostgreSQL + pgvector)]
    Redis --> Worker[Background Task Worker]
    Worker -->|Audio Pipeline & Embedding| AIService[AI Service: FastAPI]
    AIService -->|Vector Search & Similarity| DB
    AIService -->|Summarization & QA| LLM[LLM API]
```
