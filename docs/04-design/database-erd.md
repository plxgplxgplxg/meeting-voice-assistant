# THIẾT KẾ CƠ SỞ DỮ LIỆU (POSTGRESQL 16 + PGVECTOR)

**Dự án:** Hệ thống Trợ lý Giọng nói, Phiên âm, Tóm tắt và Hỏi đáp Cuộc họp Thông minh (Meeting Voice Assistant)  
**Công nghệ:** PostgreSQL 16, pgvector 0.5+, SQLAlchemy 2.0 Async, asyncpg  
**Phiên bản:** 2.1  
**Ngày cập nhật:** 2026-11-16  

---

## 1. Sơ đồ Thực thể Liên kết (Entity Relationship Diagram - ERD)

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : "sở hữu (owner)"
    USERS ||--o{ PROJECT_MEMBERS : "tham gia"
    USERS ||--o{ MEETINGS : "tạo (created_by)"
    USERS ||--o{ SUBSCRIPTIONS : "sở hữu gói cước"
    USERS ||--o{ PAYMENT_ORDERS : "thanh toán"
    USERS ||--o{ MEETING_QUOTA_USAGE_EVENTS : "tiêu thụ quota"

    PROJECTS ||--o{ PROJECT_MEMBERS : "chứa thành viên"
    PROJECTS ||--o{ PROJECT_MEETINGS : "liên kết cuộc họp"

    MEETINGS ||--o{ PROJECT_MEETINGS : "thuộc dự án"
    MEETINGS ||--o{ AUDIO_FILES : "chứa tệp ghi âm"
    MEETINGS ||--o{ TRANSCRIPT_SEGMENTS : "chứa các phân đoạn"
    MEETINGS ||--o| MEETING_SUMMARIES : "có bản tóm tắt"
    MEETINGS ||--o{ ACTION_ITEMS : "có danh mục việc"
    MEETINGS ||--o{ CHAT_SESSIONS : "có phiên hỏi đáp RAG"
    MEETINGS ||--o{ MEETING_QUOTA_USAGE_EVENTS : "phát sinh quota"

    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : "lưu trữ tin nhắn"

    PLAN_CONFIGS ||--o{ SUBSCRIPTIONS : "định nghĩa gói"
    PLAN_CONFIGS ||--o{ PAYMENT_ORDERS : "áp dụng cho đơn"

    PAYMENT_ORDERS ||--o| SEPAY_WEBHOOK_EVENTS : "đối soát webhook"

    USERS {
        uuid id PK
        string email UK
        string full_name
        string password_hash
        string role
        string avatar_url
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    PROJECTS {
        uuid id PK
        string name
        text description
        uuid owner_id FK
        timestamp created_at
        timestamp updated_at
    }

    PROJECT_MEMBERS {
        uuid id PK
        uuid project_id FK
        uuid user_id FK
        string role
        timestamp created_at
    }

    PROJECT_MEETINGS {
        uuid id PK
        uuid project_id FK
        uuid meeting_id FK
        uuid added_by FK
        timestamp added_at
    }

    MEETINGS {
        uuid id PK
        string title
        string status
        float duration_seconds
        uuid created_by FK
        string share_token UK
        string share_permission
        boolean is_deleted
        timestamp created_at
        timestamp updated_at
    }

    AUDIO_FILES {
        uuid id PK
        uuid meeting_id FK
        string file_name
        string storage_path
        string mime_type
        float duration_seconds
        bigint file_size_bytes
        string upload_status
        timestamp created_at
    }

    TRANSCRIPT_SEGMENTS {
        uuid id PK
        uuid meeting_id FK
        string speaker_label
        float start_time
        float end_time
        text content
        integer sequence_order
        timestamp created_at
    }

    MEETING_SUMMARIES {
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
        timestamp created_at
    }

    CHAT_SESSIONS {
        uuid id PK
        uuid meeting_id FK
        timestamp created_at
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid session_id FK
        string role
        text content
        jsonb citations
        timestamp created_at
    }

    PLAN_CONFIGS {
        uuid id PK
        string slug UK
        string name
        text description
        float price_amount
        string currency
        string billing_interval
        integer total_duration_limit_minutes
        jsonb features
        boolean is_default
        boolean is_active
        timestamp created_at
    }

    SUBSCRIPTIONS {
        uuid id PK
        uuid user_id FK
        uuid plan_config_id FK
        string status
        timestamp current_period_start
        timestamp current_period_end
        jsonb plan_snapshot
        timestamp created_at
    }

    MEETING_QUOTA_USAGE_EVENTS {
        uuid id PK
        uuid user_id FK
        uuid meeting_id FK
        float duration_seconds
        timestamp usage_at
    }

    PAYMENT_ORDERS {
        uuid id PK
        string order_code UK
        uuid user_id FK
        uuid plan_config_id FK
        float amount
        string currency
        string payment_method
        string status
        string qr_url
        string description
        timestamp paid_at
        timestamp expires_at
        timestamp created_at
    }

    SEPAY_WEBHOOK_EVENTS {
        uuid id PK
        string sepay_transaction_id UK
        uuid payment_order_id FK
        string code
        string reference_code
        float transfer_amount
        string account_number
        jsonb raw_payload
        string processing_status
        timestamp created_at
    }
```

---

## 2. Chi tiết Đặc tả các Bảng Dữ liệu

### 2.1. Phân hệ Quản lý Người dùng & Dự án
1. **`users`:** Lưu trữ định danh, thông tin bảo mật và vai trò quản trị hệ thống. Khóa chính `id` (UUID), `email` có ràng buộc duy nhất (Unique Index).
2. **`projects`:** Quản lý không gian làm việc theo nhóm hoặc phòng ban. Liên kết với `users` qua `owner_id`.
3. **`project_members`:** Quan hệ n-n giữa người dùng và dự án, phân định vai trò `owner`, `editor`, `viewer`.
4. **`project_meetings`:** Bảng nối liên kết giữa các cuộc họp và dự án tương ứng.

### 2.2. Phân hệ Cuộc họp & Phiên âm
5. **`meetings`:** Quản lý vòng đời cuộc họp (`created`, `processing`, `completed`, `failed`), thời lượng tính bằng giây, mã `share_token` (Unique Index) và phân quyền link (`viewer`, `editor`).
6. **`audio_files`:** Quản lý tệp ghi âm nguồn, kích thước tệp, đường dẫn vật lý trên ổ cứng (`storage_path`) và trạng thái upload.
7. **`transcript_segments`:** Lưu trữ từng câu thoại đã gỡ băng kèm nhãn người nói (`speaker_label`), mốc thời gian bắt đầu (`start_time`), kết thúc (`end_time`), và số thứ tự hiển thị (`sequence_order`).

### 2.3. Phân hệ Trí tuệ Nhân tạo & RAG
8. **`meeting_summaries`:** Lưu trữ Tóm tắt điều hành (`executive_summary`) và danh sách các luận điểm chính dưới dạng `JSONB` (`key_points`).
9. **`action_items`:** Lưu danh mục công việc phát sinh, người phụ trách (`assignee`), trạng thái hoàn thành (`status`: `pending` hoặc `completed`).
10. **`chat_sessions`:** Phiên đàm thoại hỏi đáp RAG gắn với từng cuộc họp.
11. **`chat_messages`:** Lịch sử tin nhắn hỏi đáp, mảng trích dẫn âm thanh đối chứng (`citations`) lưu dưới dạng JSONB gồm `segment_id`, `speaker_label`, `start_time`, `end_time`, `quote`.

### 2.4. Phân hệ Gói cước & Cổng thanh toán VietQR
12. **`plan_configs`:** Cấu hình 3 gói cước dịch vụ (`free`, `pro`, `unlimited`), giá tiền VNĐ, hạn mức số phút ghi âm tối đa.
13. **`subscriptions`:** Quản lý gói cước đang có hiệu lực của người dùng, thời điểm bắt đầu và hết hạn gói.
14. **`meeting_quota_usage_events`:** Lưu vết chi tiết từng lần tiêu thụ hạn mức sau mỗi phiên xử lý âm thanh để tính tổng thời lượng trong chu kỳ 30 ngày.
15. **`payment_orders`:** Quản lý đơn hàng chuyển khoản nâng cấp gói, mã đơn duy nhất `order_code` (ví dụ `DH123456`), link mã VietQR động Napas247 và thời gian hết hạn 30 phút.
16. **`sepay_webhook_events`:** Nhật ký lưu vết toàn bộ payload webhook do SePay bắn về để đối soát giao dịch và chống gian lận.

---

## 3. Chiến lược Đánh Chỉ mục (Indexing Strategy)
- **B-tree Indexes:**
  - Khóa chính (PK) của tất cả 16 bảng là UUID ngẫu nhiên.
  - Khóa ngoại (FK) kết nối giữa các bảng: `user_id`, `meeting_id`, `project_id`, `session_id`, `plan_config_id`.
  - Các trường tra cứu tốc độ cao: `users.email`, `meetings.share_token`, `payment_orders.order_code`, `sepay_webhook_events.sepay_transaction_id`.
- **Composite Indexes:**
  - `(meeting_id, sequence_order ASC)` trên bảng `transcript_segments` để tải danh sách câu thoại theo thứ tự thời gian có độ trễ dưới 5ms.
  - `(user_id, usage_at DESC)` trên bảng `meeting_quota_usage_events` để tính tổng hạn mức tiêu thụ tức thì.
- **JSONB GIN Indexes:**
  - Đánh chỉ mục GIN trên `chat_messages.citations` và `meeting_summaries.key_points` để hỗ trợ truy vấn các phần tử trong mảng JSON tốc độ cao.
