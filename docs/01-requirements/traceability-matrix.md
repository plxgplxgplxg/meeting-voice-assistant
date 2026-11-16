# MA TRẬN TRUY VẾT YÊU CẦU (REQUIREMENTS TRACEABILITY MATRIX - RTM)

**Dự án:** Hệ thống Trợ lý Giọng nói, Phiên âm, Tóm tắt và Hỏi đáp Cuộc họp Thông minh (Meeting Voice Assistant)  
**Tiêu chuẩn áp dụng:** IEEE Std 830-1998, ISO/IEC/IEEE 29148:2018 và ISO/IEC/IEEE 29119  
**Giai đoạn hiện tại:** Hoàn thiện Toàn diện (Full Implementation & Verification Phase)  
**Phiên bản:** 2.1  
**Ngày cập nhật:** 2026-11-16  
**Tác giả:** Nguyễn Phương Linh (MSSV: 20224871)  

---

## 1. Giới thiệu và Mục tiêu của RTM

Tài liệu Ma trận truy vết yêu cầu (Requirements Traceability Matrix - RTM) này đóng vai trò liên kết chặt chẽ giữa:
1. **Yêu cầu nghiệp vụ (Business Requirements trong PRD, User Stories)**
2. **Yêu cầu chức năng và Phi chức năng (SRS: FR-01 -> FR-23, NFR-01 -> NFR-12)**
3. **Các Ca sử dụng hệ thống (Use Cases: UC-01 -> UC-12, UC-S01 -> UC-S03)**
4. **Mã nguồn hiện thực (Backend API, AI Service, Frontend Components, Celery Worker)**
5. **Kịch bản và Bộ kiểm thử thực tế (Pytest Suites, UAT Cases)**

---

## 2. Ma trận truy vết Yêu cầu Chức năng (Functional Requirements RTM)

| Requirement ID | Tên Yêu cầu chức năng | Nguồn yêu cầu | Thiết kế & Mã nguồn hiện thực (Implementation File) | Kịch bản kiểm thử (Test File) | Trạng thái kiểm thử (Status) |
|---|---|---|---|---|:---:|
| **REQ-FR-01** | Đăng ký & Đăng nhập (JWT Access/Refresh) | SRS: FR-01<br>UC: UC-01 | `backend-api/app/services/auth_service.py`<br>`backend-api/app/api/v1/endpoints/auth.py`<br>`frontend/src/app/(auth)/login/page.tsx` | `backend-api/tests/test_auth.py` | **PASSED (100%)** |
| **REQ-FR-02** | Quản lý Hồ sơ cá nhân & Cấp lại Token | SRS: FR-02<br>UC: UC-01, S01 | `backend-api/app/api/v1/endpoints/users.py`<br>`frontend/src/app/settings/profile/page.tsx` | `backend-api/tests/test_auth.py` | **PASSED (100%)** |
| **REQ-FR-03** | Khởi tạo Không gian làm việc / Dự án | SRS: FR-03<br>UC: UC-02 | `backend-api/app/services/project_service.py`<br>`backend-api/app/api/v1/endpoints/projects.py`<br>`frontend/src/components/project/ProjectSelector.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-04** | Phân quyền thành viên & Phân nhóm cuộc họp | SRS: FR-04<br>UC: UC-02 | `backend-api/app/models/project.py`<br>`frontend/src/app/page.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-05** | Tải lên tệp ghi âm đa định dạng (WAV/MP3/M4A/MP4) | SRS: FR-05<br>UC: UC-03 | `backend-api/app/services/audio_service.py`<br>`backend-api/app/api/v1/endpoints/audio.py`<br>`frontend/src/app/page.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-06** | Phát luồng âm thanh HTTP Range Scrubbing | SRS: FR-06<br>UC: UC-06 | `backend-api/app/api/v1/endpoints/audio.py`<br>`frontend/src/components/meeting/SpeakerTimeline.tsx` | Browser Range Test | **PASSED (100%)** |
| **REQ-FR-07** | Nhận diện tiếng Việt & Diarization qua Gladia API | SRS: FR-07<br>UC: UC-04 | `ai-service/app/pipelines/gladia.py`<br>`backend-api/app/workers/celery_worker.py` | `ai-service/tests/test_gladia_pipeline.py` | **PASSED (100%)** |
| **REQ-FR-08** | Cơ chế dự phòng ngoại tuyến Mock Pipeline | SRS: FR-08<br>UC: UC-04 | `ai-service/app/pipelines/gladia.py`<br>`backend-api/app/workers/celery_worker.py` | `ai-service/tests/test_gladia_pipeline.py` | **PASSED (100%)** |
| **REQ-FR-09** | Ghi âm & Phiên âm trực tiếp qua WebSocket | SRS: FR-09<br>UC: UC-05 | `backend-api/app/api/v1/endpoints/live_ws.py`<br>`frontend/src/app/live/page.tsx` | Live WS Mock & Test | **PASSED (100%)** |
| **REQ-FR-10** | Hiệu chỉnh câu thoại & Đổi tên người nói đồng loạt | SRS: FR-10<br>UC: UC-06 | `backend-api/app/services/transcript_service.py`<br>`frontend/src/components/meeting/TranscriptFeed.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-11** | Thêm mới, Xóa & Tách gộp phân đoạn thoại | SRS: FR-11<br>UC: UC-06 | `backend-api/app/api/v1/endpoints/transcripts.py`<br>`frontend/src/components/meeting/TranscriptFeed.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-12** | Tóm tắt điều hành & Luận điểm qua Gemini 2.0 Flash | SRS: FR-12<br>UC: UC-07 | `ai-service/app/rag/generator.py`<br>`ai-service/app/routers/rag.py`<br>`frontend/src/app/meetings/[id]/page.tsx` | `ai-service/tests/test_summary_generator.py` | **PASSED (100%)** |
| **REQ-FR-13** | Trích xuất và Quản lý trạng thái Action Items | SRS: FR-13<br>UC: UC-07 | `backend-api/app/api/v1/endpoints/summaries.py`<br>`frontend/src/app/meetings/[id]/page.tsx` | `ai-service/tests/test_summary_generator.py` | **PASSED (100%)** |
| **REQ-FR-14** | Tái tạo tóm tắt thông minh sau khi sửa văn bản | SRS: FR-14<br>UC: UC-S02 | `backend-api/app/api/v1/endpoints/meetings.py` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-15** | RAG Hybrid Search với Multilingual E5 & RRF | SRS: FR-15<br>UC: UC-08 | `ai-service/app/rag/retriever.py`<br>`ai-service/app/routers/rag.py` | `ai-service/tests/test_retriever.py` | **PASSED (100%)** |
| **REQ-FR-16** | Trợ lý RAG phản hồi kèm trích dẫn âm thanh đối chứng | SRS: FR-16<br>UC: UC-08 | `backend-api/app/services/chat_service.py`<br>`frontend/src/components/meeting/AssistantChatPane.tsx` | `backend-api/tests/test_chat.py` | **PASSED (100%)** |
| **REQ-FR-17** | Fallback tìm kiếm từ khóa khi AI Service ngoại tuyến | SRS: FR-17<br>UC: UC-08 | `backend-api/app/services/chat_service.py` | `backend-api/tests/test_chat.py` | **PASSED (100%)** |
| **REQ-FR-18** | Xuất biên bản cuộc họp DOCX, PDF, TXT, MD, JSON | SRS: FR-18<br>UC: UC-09 | `backend-api/app/services/export_service.py`<br>`frontend/src/components/meeting/ExportDropdown.tsx` | `backend-api/tests/test_exports.py` | **PASSED (100%)** |
| **REQ-FR-19** | Sinh link chia sẻ bảo mật có mã Token & Phân quyền | SRS: FR-19<br>UC: UC-10 | `backend-api/app/services/meeting_service.py`<br>`frontend/src/app/meetings/[id]/page.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-20** | Cấu hình phân tầng 3 gói cước (Free, Pro, Unlimited) | SRS: FR-20<br>UC: UC-11 | `backend-api/app/services/plan_service.py`<br>`frontend/src/components/billing/PricingModal.tsx` | `backend-api/tests/test_payments.py` | **PASSED (100%)** |
| **REQ-FR-21** | Kiểm soát và Cảnh báo hạn mức Quota thời lượng | SRS: FR-21<br>UC: UC-11 | `backend-api/app/services/quota_service.py`<br>`frontend/src/components/billing/QuotaBadge.tsx` | Integration Unit Suite | **PASSED (100%)** |
| **REQ-FR-22** | Tạo đơn hàng & Sinh mã VietQR động Napas247 | SRS: FR-22<br>UC: UC-12 | `backend-api/app/services/payment_service.py`<br>`frontend/src/components/billing/VietQRModal.tsx` | `backend-api/tests/test_payments.py` | **PASSED (100%)** |
| **REQ-FR-23** | Nhận Webhook SePay & Tự động kích hoạt gói tức thì | SRS: FR-23<br>UC: UC-12 | `backend-api/app/api/v1/endpoints/payments.py`<br>`backend-api/app/services/payment_service.py` | `backend-api/tests/test_payments.py` | **PASSED (100%)** |

---

## 3. Ma trận truy vết Yêu cầu Phi Chức năng (Non-Functional Requirements RTM)

| Requirement ID | Nội dung yêu cầu phi chức năng | Tiêu chuẩn chất lượng | Hiện thực trong mã nguồn | Phương pháp xác minh | Kết quả |
|---|---|---|---|---|:---:|
| **REQ-NFR-01** | Thời gian phản hồi RAG < 2.5s | ISO 25010 Hiệu năng | `ai-service/app/rag/generator.py` | Pytest Execution & Benchmark | **ĐẠT** |
| **REQ-NFR-02** | Xử lý âm thanh Gladia < 20% thời lượng tệp | Hiệu năng xử lý | `ai-service/app/pipelines/gladia.py` | Gladia Cloud API Benchmark | **ĐẠT** |
| **REQ-NFR-03** | Tua âm thanh HTTP Range có độ trễ < 300ms | Trải nghiệm người dùng | `backend-api/app/api/v1/endpoints/audio.py` | Browser Partial Content Seeking | **ĐẠT** |
| **REQ-NFR-04** | Xử lý đối soát Webhook SePay < 1.0s | Tự động hóa thanh toán | `backend-api/app/api/v1/endpoints/payments.py` | `tests/test_payments.py` | **ĐẠT** |
| **REQ-NFR-05** | Tỷ lệ lỗi nhận dạng tiếng Việt (WER) < 12% | Độ chính xác AI | Gladia Whisper v2 Engine | Đánh giá mẫu audio tiếng Việt | **ĐẠT** |
| **REQ-NFR-06** | Tỷ lệ lỗi phân tách người nói (DER) < 15% | Độ chính xác AI | Gladia Diarization Model | Đối soát 3-5 người nói | **ĐẠT** |
| **REQ-NFR-07** | 100% câu trả lời có trích dẫn liên kết đúng phân đoạn | Chống ảo giác (Hallucination) | `ai-service/app/rag/retriever.py` | `tests/test_retriever.py` | **ĐẠT** |
| **REQ-NFR-08** | Mã hóa an toàn mật khẩu (bcrypt) và mã xác thực JWT | An toàn bảo mật | `backend-api/app/core/security.py` | `tests/test_auth.py` | **ĐẠT** |
| **REQ-NFR-09** | Xác thực khóa bí mật Webhook SePay | Phòng chống gian lận | `backend-api/app/services/payment_service.py` | `tests/test_payments.py` | **ĐẠT** |
| **REQ-NFR-10** | Tự động phục hồi & Khởi động lại (restart: always) | Độ tin cậy (Reliability) | `docker-compose.yml`, `docker-compose.prod.yml` | Docker Daemon Healthcheck | **ĐẠT** |
| **REQ-NFR-11** | Tự động dự phòng ngầm (Fallback Async & Fallback Search) | Tính sẵn sàng | `audio_service.py`, `chat_service.py` | `tests/test_chat.py` | **ĐẠT** |
| **REQ-NFR-12** | Decoupled Microservices & CPU-first architecture | Khả năng mở rộng & Bảo trì | Docker Compose, FastAPIs, Next.js | Toàn bộ hệ thống chạy trên CPU EC2 | **ĐẠT** |
