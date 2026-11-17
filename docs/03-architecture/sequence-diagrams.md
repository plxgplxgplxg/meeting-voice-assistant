# SƠ ĐỒ TUẦN TỰ THEO CODE HIỆN TẠI

## 1. UC-01 — Đăng ký

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Next.js
    participant API as Backend API
    participant DB as PostgreSQL
    U->>UI: Nhập hồ sơ và mật khẩu
    UI->>API: POST /api/v1/auth/register
    API->>DB: Kiểm tra email, insert user/subscription
    API-->>UI: user + access/refresh token
    UI->>UI: Lưu token, cập nhật AuthContext
```

## 2. UC-03 — Upload và xử lý audio

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Next.js
    participant API as Backend
    participant FS as Shared Volume
    participant Q as Redis
    participant W as Celery
    participant AI as AI Service
    participant G as Gladia
    participant L as Gemini/OpenAI
    participant DB as PostgreSQL

    U->>UI: Chọn project, title, audio
    UI->>API: POST /meetings
    API->>DB: meeting=created
    API-->>UI: meeting_id
    opt Có project
        UI->>API: POST /projects/{project}/meetings/{meeting}
        API->>DB: insert project_meetings
    end
    UI->>API: POST /audio/meetings/{id}/upload
    API->>FS: Lưu file
    API->>DB: audio metadata, meeting=processing
    API->>Q: process_audio_task
    API-->>UI: 201
    Q->>W: Deliver task
    W->>AI: POST /audio/process(path)
    AI->>G: Upload/create job/poll
    G-->>AI: Utterances
    AI-->>W: Segments
    W->>DB: Insert transcript segments
    W->>AI: POST /rag/summarize
    AI->>L: Chat completion
    L-->>AI: Structured text
    AI-->>W: Summary/action items
    W->>DB: Save result, usage, status=completed
    loop Mỗi 4 giây khi processing
        UI->>API: GET /meetings/{id}
        API-->>UI: status
    end
```

## 3. UC-04 — Biên tập transcript

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Transcript Studio
    participant API as Backend
    participant DB as PostgreSQL
    U->>UI: Sửa một segment
    UI->>API: PATCH /transcripts/segments/{id}
    API->>DB: UPDATE content/speaker
    API-->>UI: Segment mới
    U->>UI: Rename speaker toàn meeting
    UI->>API: POST /transcripts/{meeting}/rename-speaker
    API->>DB: Bulk UPDATE
    API-->>UI: affected_segments
    U->>UI: Xóa segment
    UI->>API: POST /transcripts/{meeting}/delete-segments
    API->>DB: DELETE selected IDs
    API-->>UI: deleted_segments
```

## 4. UC-06 — Hỏi đáp RAG

```mermaid
sequenceDiagram
    actor U as User
    participant UI as AssistantChatPane
    participant API as Backend
    participant DB as PostgreSQL
    participant AI as AI Service
    participant E as E5 Retriever
    participant L as Gemini/OpenAI
    U->>UI: Nhập câu hỏi
    UI->>API: POST /chat/{meeting} {query}
    API->>DB: Load segments + recent chat; save user message
    API->>AI: POST /rag/query
    AI->>E: Rank lexical + embeddings
    AI->>L: Query + top segments + history
    L-->>AI: Answer
    AI-->>API: answer + citations
    API->>DB: Save assistant message
    API-->>UI: ChatMessageResponse
    U->>UI: Click citation
    UI->>UI: audio.currentTime=start_time; play()
```

## 5. UC-10 — VietQR/SePay

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Pricing/VietQR UI
    participant API as Backend
    participant DB as PostgreSQL
    participant Bank as Bank/VietQR
    participant S as SePay
    UI->>API: POST /payments/checkout {plan_slug}
    API->>DB: Insert pending order
    API-->>UI: bank info + qr_url + order_code
    U->>Bank: Chuyển khoản đúng amount/content
    Bank->>S: Biến động số dư
    S->>API: POST /payments/sepay/webhook
    API->>API: Verify key, code, amount, idempotency
    API->>DB: Complete order + activate subscription
    loop 2.5 giây
        UI->>API: GET /payments/orders/{code}
        API-->>UI: pending/completed
    end
```

## 6. UC-S01 — Ghi microphone rồi xử lý batch

```mermaid
sequenceDiagram
    actor U as User
    participant UI as /live
    participant B as Browser MediaRecorder
    participant API as Backend
    U->>UI: Bắt đầu
    UI->>B: getUserMedia + MediaRecorder.start
    B-->>UI: WebM chunks trong bộ nhớ
    U->>UI: Dừng và phân tích
    UI->>B: MediaRecorder.stop
    UI->>API: Upload WebM
    API-->>UI: queued
    UI->>UI: Chuyển /meetings/{id}
```

Luồng này không dùng WebSocket và không có transcript live. WebSocket hiện tại chỉ là interface thử nghiệm sinh segment mô phỏng.
