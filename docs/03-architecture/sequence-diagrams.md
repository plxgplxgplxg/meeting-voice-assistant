# SƠ ĐỒ TUẦN TỰ THEO CODE HIỆN TẠI

**Phiên bản:** 3.0 — đối chiếu code ngày 17/11/2026

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

Việc gửi task nằm trong transaction của request thông qua outbox; tiến trình API không còn tự chạy tác vụ nền.

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Next.js
    participant API as Backend
    participant DB as PostgreSQL
    participant FS as Shared Volume
    participant Beat as Celery beat
    participant Q as Redis
    participant W as Celery Worker
    participant AI as AI Service
    participant G as Gladia

    U->>UI: Chọn project, title, audio
    UI->>API: POST /meetings, POST /meetings/{id}/audio (multipart)
    API->>API: Kiểm tra quota, kích thước, định dạng
    API->>FS: Lưu file theo storage_key tương đối
    API->>DB: audio_file, meeting=uploaded, processing_job(transcribe), outbox_event (1 commit)
    API-->>UI: 201

    loop mỗi 2 giây
        Beat->>DB: dispatch_outbox: lấy sự kiện chưa gửi (SKIP LOCKED)
        DB-->>Beat: sự kiện
        Beat->>Q: run_processing_job(job_id)
    end

    Q->>W: giao task
    W->>W: ffprobe, kiểm tra thời lượng theo gói
    W->>AI: POST /audio/transcribe {storage_key}
    AI->>G: upload + tạo job
    AI-->>W: provider_job_id
    loop poll bằng Celery retry (retry_in)
        W->>AI: GET /audio/transcribe/{provider_job_id}
        AI->>G: lấy kết quả
        AI-->>W: processing hoặc completed
    end
    W->>DB: thay segment, revision +1, phát TranscriptReplaced
    Note over W,DB: handler xếp job summarize và index, meeting=summarizing
    W->>AI: POST /llm/summarize
    W->>AI: POST /embeddings (các chunk)
    W->>DB: summary, transcript_chunks, summary_status=ready, index_status=ready
    W->>DB: meeting=ready, ghi quota đúng một lần

    loop khi chưa ready/failed
        UI->>API: GET /meetings/{id}
        API-->>UI: status, summary_status, index_status
    end
```

Lỗi tạm thời (AI Service, Gladia 5xx, timeout) khiến bước tự retry với backoff luỹ thừa, tối đa `job_max_attempts = 3`. Hết lượt, job và meeting chuyển `failed` kèm `failure_reason`; người dùng thử lại bằng `POST /meetings/{id}/reprocess`.

## 3. UC-04 — Biên tập transcript

Mọi thao tác ghi đi qua `TranscriptEditor`. Client gửi `expected_revision` để tránh ghi đè chỉnh sửa của người khác.

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Transcript Studio
    participant API as Backend
    participant ED as TranscriptEditor
    participant DB as PostgreSQL
    participant EB as EventBus

    U->>UI: Rename speaker, sửa, xóa, gộp, tách
    UI->>API: POST /meetings/{id}/transcript/operations:preview
    API->>ED: preview(operations)
    ED-->>UI: diff (không ghi)
    U->>UI: Xác nhận
    UI->>API: POST /meetings/{id}/transcript/operations {ops, expected_revision}
    API->>ED: apply(actor, ops, expected_revision)
    ED->>DB: SELECT meeting FOR UPDATE
    alt revision đã đổi
        ED-->>API: ConflictError
        API-->>UI: 409 TRANSCRIPT_REVISION_CONFLICT
        UI->>UI: Tải lại transcript, hỏi người dùng
    else hợp lệ
        ED->>DB: ghi segment, change set, segment_changes, revision +1
        ED->>EB: TranscriptEdited
        EB->>DB: summary/index ready thành stale, xếp job index (trễ vài giây)
        API-->>UI: ChangeSetResult {revision, change_set_id}
        UI->>UI: Hiển thị toast "Hoàn tác"
    end
```

Các endpoint cũ (`PATCH /transcripts/segments/{id}`, `rename-speaker`, `delete-segments`) vẫn hoạt động, được đánh dấu deprecated và cùng gọi `TranscriptEditor`.

## 4. UC-06 — Hỏi đáp có trích dẫn

```mermaid
sequenceDiagram
    actor U as User
    participant UI as AssistantPane
    participant API as Backend
    participant DB as PostgreSQL + pgvector
    participant AI as AI Service
    participant L as Gemini/OpenAI

    U->>UI: Nhập câu hỏi
    UI->>API: POST /meetings/{id}/chat {query}
    API->>API: check_can_ask (gói, giới hạn câu hỏi)
    API->>AI: POST /embeddings (câu hỏi)
    AI-->>API: vector 384 chiều
    API->>DB: Một câu SQL: cosine HNSW + ts_rank GIN, hợp nhất RRF, WHERE meeting_id
    DB-->>API: top-k chunk kèm khoảng thời gian
    API->>AI: POST /rag/answer {query, chunks, history}
    AI->>L: Câu hỏi + ngữ cảnh đã chọn
    L-->>AI: Câu trả lời
    AI-->>API: answer + citations
    API->>DB: Lưu agent_messages (user và assistant)
    API-->>UI: ChatMessageResponse
    U->>UI: Bấm trích dẫn
    UI->>UI: audio.currentTime = start_time; play()
```

Khi meeting chưa có chỉ mục (`index_status` là `none`, `pending` hoặc `failed`), Backend trả `INDEX_NOT_READY` thay vì trả lời bằng dữ liệu không đầy đủ.

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
    S->>API: POST /payments/sepay/webhook (Apikey bắt buộc)
    API->>API: Verify key, code, amount, idempotency
    API->>DB: Complete order + activate subscription
    loop 2.5 giây
        UI->>API: GET /payments/orders/{code}
        API-->>UI: pending/completed
    end
```

## 6. Lượt trợ lý với đề xuất và phê duyệt

Chỉ gói có `features.agent_tools` (Pro, Business) dùng được; gói khác nhận `PLAN_FEATURE_REQUIRED` và vẫn dùng hỏi đáp thuần ở mục 4.

```mermaid
sequenceDiagram
    actor U as User
    participant UI as AssistantPane
    participant API as Backend (public)
    participant DB as PostgreSQL
    participant AI as AI Service (agent)
    participant CP as langgraph checkpoint
    participant L as LLM
    participant TOOL as Backend (/internal/agent/v1)

    U->>UI: "Đổi tên Speaker 1 thành An"
    UI->>API: POST /meetings/{id}/assistant/turns (SSE)
    API->>API: Quyền VIEW, assert_agent_allowed
    API->>DB: lưu tin nhắn user, commit
    API->>API: Ký token ủy quyền (aud=agent, 5 phút, scope=meeting:{id}, tv)
    API->>AI: POST /agent/turn {message, thread_id, token}
    AI->>CP: nạp trạng thái hội thoại
    loop tối đa 8 bước
        AI->>L: lịch sử + công cụ
        L-->>AI: tool_calls
        AI-->>API: tool_start
        API-->>UI: tool_start
        AI->>TOOL: gọi công cụ (X-Service-Token + token ủy quyền)
        TOOL->>TOOL: Xác thực, kiểm tra token_version, meeting, quyền
        TOOL-->>AI: kết quả trong thẻ transcript (dữ liệu không tin cậy)
        AI-->>API: tool_end
    end
    AI->>TOOL: POST propose_transcript_edits {operations, base_revision}
    TOOL->>DB: agent_actions (status=proposed, base_revision, preview diff)
    TOOL-->>AI: action_id + diff
    AI-->>API: proposal {action, diff}
    API-->>UI: proposal
    AI-->>API: token (câu trả lời), citation
    API-->>UI: token, citation
    AI-->>API: done
    API->>DB: lưu tin nhắn assistant, commit
    API-->>UI: done
    UI->>UI: Hiển thị ProposalCard (diff, Áp dụng, Sửa, Bỏ qua)

    U->>UI: Áp dụng
    UI->>API: POST /meetings/{id}/agent-actions/{action_id}:approve
    API->>API: Quyền EDIT, đúng người đề xuất, chưa quá 30 phút
    alt revision đã đổi hoặc hết hạn
        API-->>UI: 409 PROPOSAL_STALE hoặc PROPOSAL_EXPIRED
    else hợp lệ
        API->>DB: TranscriptEditor.apply(actor_type=agent, expected_revision=base_revision)
        API->>DB: action=applied, change_set_id
        API-->>UI: AgentActionResponse + toast "Hoàn tác"
    end
```

Tóm tắt các bất biến bảo mật: token ủy quyền không do mô hình nhìn thấy; mọi công cụ dùng quyền của User khởi tạo lượt, không phải của share token; công cụ ghi chỉ tạo đề xuất; duyệt luôn do con người thực hiện qua endpoint công khai; `/internal/*` không được nginx chuyển ra ngoài.

## 7. UC-11 — Xem lịch sử và hoàn tác

```mermaid
sequenceDiagram
    actor U as User
    participant UI as ChangeHistoryDrawer
    participant API as Backend
    participant ED as TranscriptEditor
    participant DB as PostgreSQL
    U->>UI: Mở lịch sử chỉnh sửa
    UI->>API: GET /meetings/{id}/transcript/change-sets
    API-->>UI: danh sách (actor user hoặc agent, tóm tắt, thời gian)
    U->>UI: Chọn một lần chỉnh sửa
    UI->>API: GET /transcript/change-sets/{cs}
    API-->>UI: before/after từng segment
    U->>UI: Hoàn tác
    UI->>API: POST /transcript/change-sets/{cs}/revert
    API->>ED: revert(actor, cs)
    alt đã hoàn tác hoặc có chỉnh sửa muộn hơn chạm cùng segment
        ED-->>UI: 409 ALREADY_REVERTED hoặc TRANSCRIPT_REVERT_CONFLICT
    else hợp lệ
        ED->>DB: áp dụng phép nghịch đảo như change set mới, revision +1
        ED-->>UI: ChangeSetResult
    end
```

## 8. UC-12 — Tạo biên bản và tài liệu

```mermaid
sequenceDiagram
    actor U as User
    participant UI as AssistantPane / ArtifactsPanel
    participant AI as AI Service (agent)
    participant TOOL as Backend (/internal/agent/v1)
    participant ART as ArtifactService
    participant DB as PostgreSQL
    participant FS as Storage
    U->>UI: "Soạn biên bản họp dạng Word"
    UI->>AI: lượt trợ lý (qua Backend, SSE)
    AI->>TOOL: POST /artifacts {kind: minutes_docx}
    TOOL->>ART: create(meeting, kind, actor)
    ART->>DB: MeetingDocumentLoader (transcript, summary, action items)
    ART->>FS: ghi file .docx
    ART->>DB: meeting_artifacts
    TOOL-->>AI: artifact_id, tên file
    AI-->>UI: câu trả lời kèm liên kết
    U->>UI: Tải xuống
    UI->>API: GET /meetings/{id}/artifacts/{artifact}/download
    Note over UI,API: tên file không ASCII dùng RFC 5987 filename*=UTF-8''
```

## 9. UC-S01 — Ghi microphone rồi xử lý batch

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
    UI->>API: Upload WebM (như mục 2)
    API-->>UI: 201
    UI->>UI: Chuyển /meetings/{id}
```

Luồng này không có transcript live và hệ thống không còn kênh WebSocket nào; Nginx cũng không cấu hình WebSocket upgrade nữa.
