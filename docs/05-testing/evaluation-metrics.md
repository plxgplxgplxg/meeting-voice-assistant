# Định Nghĩa Chỉ Số Đánh Giá Đo Lường (Evaluation Metrics)

## 1. Đánh Giá Phiên Âm Tiếng Nói (ASR)
- **Word Error Rate (WER):**
  $$WER = \frac{S + D + I}{N}$$
  Trong đó: $S$ là số từ thay thế, $D$ là số từ bị xóa, $I$ là số từ chèn thêm, $N$ là tổng số từ tham chiếu.

## 2. Đánh Giá Tách Người Nói (Diarization)
- **Diarization Error Rate (DER):** Tổng tỷ lệ lỗi gán nhãn người nói sai, bỏ sót tiếng nói và nhận diện nhầm tiếng ồn.

## 3. Đánh Giá Tóm Tắt & Hỏi Đáp RAG
- **ROUGE-1, ROUGE-2, ROUGE-L:** Đánh giá độ trùng khớp n-gram giữa bản tóm tắt tự động và bản tóm tắt mẫu.
- **Faithfulness Score:** Tỷ lệ phần trăm các luận điểm trong câu trả lời có bằng chứng trực tiếp từ ngữ cảnh trích dẫn.
