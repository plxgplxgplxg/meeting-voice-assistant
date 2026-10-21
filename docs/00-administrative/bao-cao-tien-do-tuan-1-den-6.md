# Báo Cáo Tiến Độ Đồ Án Tốt Nghiệp (Tuần 1 — Tuần 6)

**Đề tài:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp  
**Sinh viên thực hiện:** Nguyễn Phương Linh — MSSV: 20224871 — Lớp: IT1-02  
**Giảng viên hướng dẫn:** Thầy Cao Tuấn Dũng  
**Thời gian:** Học kỳ 2024.1 (Giai đoạn nước rút bù tiến độ)

---

## 1. Tóm Tắt Tình Hình Thực Hiện
Báo cáo quá trình hoàn thiện các nội dung thuộc Tuần 1 đến Tuần 6 sau khi thống nhất chuyển hướng đề tài:
- Khảo sát và hoàn thiện đặc tả yêu cầu người dùng (PRD, SRS, Use Cases).
- Hoàn thiện nghiên cứu công nghệ ASR, Diarization, và cơ chế RAG có trích dẫn nguồn.
- Thiết kế kiến trúc C4 Model, cơ sở dữ liệu quan hệ PostgreSQL tích hợp vector pgvector.
- Thiết kế hợp đồng API (OpenAPI 3.0) và UI/UX Wireframe tinh giản.
- Xây dựng khung mã nguồn (skeleton) chạy được bằng Docker Compose.

## 2. Chi Tiết Kết Quả Bàn Giao Theo Tuần
### Tuần 1 - 2: Nghiên cứu bài toán & Yêu cầu phần mềm
- Đã hoàn thành PRD, SRS theo tiêu chuẩn IEEE 830 / ISO 25010.
- Chi tiết 5 Use Case chính: UC-01 (Ghi âm trực tiếp), UC-02 (Tải tệp âm thanh), UC-03 (Chỉnh sửa biên bản), UC-04 (Tóm tắt & Việc cần làm), UC-05 (Hỏi đáp RAG có trích dẫn).

### Tuần 2 - 4: Khảo sát công nghệ & Mô hình AI
- Đánh giá ASR: Faster-Whisper, PhoWhisper; VAD Silero; Speaker Diarization Pyannote.
- Thiết kế luồng trích xuất ngữ cảnh hội thoại theo lượt nói và cơ chế đánh chỉ mục vector.

### Tuần 3 - 6: Thiết kế kiến trúc, CSDL & API
- Sơ đồ C4 Context & Container.
- Thiết kế ERD với 8 bảng chính và mở rộng pgvector.
- Đặc tả API chuẩn OpenAPI 3.0.

## 3. Kế Hoạch Tuần Tiếp Theo (Tuần 7)
- Bắt đầu cài đặt chi tiết dịch vụ `backend-api` và `ai-service`.
- Tích hợp pipeline Faster-Whisper với tiếng Việt và cấu hình Redis Queue.
