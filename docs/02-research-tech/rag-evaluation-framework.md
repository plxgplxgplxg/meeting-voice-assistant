# Khung Đánh Giá RAG & Cơ Chế Trích Dẫn Nguồn (Citations)

## 1. Phương Pháp Chunking Dành Riêng Cho Cuộc Họp
- Phân đoạn theo lượt nói (Speaker Turns) thay vì chia theo số ký tự cố định.
- Kỹ thuật Window Context: Ghép lượt nói mục tiêu với lượt nói liền trước và liền sau để giữ trọn vẹn ngữ cảnh giao tiếp.

## 2. Cơ Chế Gắn Nhãn Trích Dẫn (Citation Grounding)
- Mỗi đoạn chunk lưu trữ metadata: `meeting_id`, `speaker_name`, `start_time`, `end_time`.
- Khi LLM sinh câu trả lời, yêu cầu xuất format có kèm `[citation:segment_id]`.
- Frontend phân giải ID để hiển thị badge nhấp vào tua ngay đến mốc phát.

## 3. Tiêu Chí Đo Lường Chất Lượng RAG
- **Faithfulness:** Mức độ câu trả lời hoàn toàn dựa vào context được truy hồi (chống hallucination).
- **Answer Relevance:** Mức độ câu trả lời đúng trọng tâm câu hỏi.
- **Context Recall:** Tỷ lệ thông tin cần thiết được tìm thấy trong top-k chunks.
