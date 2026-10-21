# Software Requirements Specification (SRS)
*Tuân theo tiêu chuẩn IEEE 830 và mô hình chất lượng phần mềm ISO/IEC 25010.*

## 1. Yêu Cầu Chức Năng (Functional Requirements)
- **FR-01: Thu âm và Phiên âm trực tiếp (Real-time ASR):** Hỗ trợ nhận luồng âm thanh qua WebSocket và phiên âm tức thời.
- **FR-02: Tải lên và Xử lý tệp âm thanh (Batch Processing):** Tiếp nhận file định dạng MP3, WAV, M4A và xử lý qua hàng đợi Redis.
- **FR-03: Nhận diện và Phân đoạn người nói (Speaker Diarization):** Gán nhãn từng đoạn hội thoại theo Speaker ID.
- **FR-04: Hiệu chỉnh biên bản (Transcript Studio):** Cho phép sửa văn bản, gộp câu, đổi tên người nói và cập nhật chỉ mục.
- **FR-05: Tóm tắt & Trích xuất công việc (Meeting Summarization):** Sinh danh sách quyết định và Action Items dạng có cấu trúc.
- **FR-06: Hỏi đáp có căn cứ (Grounded RAG QA):** Trả lời câu hỏi dựa trên nội dung cuộc họp kèm link trích dẫn mốc thời gian.

## 2. Yêu Cầu Phi Chức Năng (Non-Functional Requirements)
- **NFR-01: Độ chính xác (Accuracy):** WER < 15% đối với âm thanh rõ ràng; DER < 18%.
- **NFR-02: Độ trễ (Latency):** Phản hồi câu hỏi RAG < 3 giây với luồng streaming SSE.
- **NFR-03: Độ tin cậy (Reliability):** Không đánh mất dữ liệu âm thanh khi ngắt kết nối đột ngột.
- **NFR-04: Tính khả dụng (Usability):** Giao diện tinh giản, dễ sử dụng theo chuẩn Clean Minimalist.
