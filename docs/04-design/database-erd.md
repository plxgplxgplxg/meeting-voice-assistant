# Thiết Kế Cơ Sở Dữ Liệu (PostgreSQL + pgvector)

## 1. Sơ Đồ Thực Thể Liên Kết (ERD)
```mermaid
erDiagram
    MEETINGS ||--o{ TRANSCRIPT_SEGMENTS : contains
    MEETINGS ||--o| SUMMARIES : has
    MEETINGS ||--o{ ACTION_ITEMS : assigns
    MEETINGS ||--o{ CHAT_SESSIONS : includes
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : records
    TRANSCRIPT_SEGMENTS ||--o| TRANSCRIPT_EMBEDDINGS : vectors

    MEETINGS {
        uuid id PK
        string title
        string status
        float duration_seconds
        timestamp created_at
        timestamp updated_at
    }

    TRANSCRIPT_SEGMENTS {
        uuid id PK
        uuid meeting_id FK
        string speaker_label
        float start_time
        float end_time
        text content
        integer sequence_order
    }

    TRANSCRIPT_EMBEDDINGS {
        uuid id PK
        uuid segment_id FK
        vector embedding
        timestamp created_at
    }

    SUMMARIES {
        uuid id PK
        uuid meeting_id FK
        text executive_summary
        jsonb key_points
        timestamp created_at
    }

    ACTION_ITEMS {
        uuid id PK
        uuid meeting_id FK
        text description
        string assignee
        string status
        timestamp due_date
    }
```

## 2. Kỹ Thuật Chỉ Mục (Indexing)
- Khóa chính và khóa ngoại: B-tree index tiêu chuẩn.
- Bảng `transcript_embeddings`: Chỉ mục HNSW (Hierarchical Navigable Small World) sử dụng khoảng cách Cosine `vector_cosine_ops` để tối ưu tìm kiếm lân cận tốc độ cao.
