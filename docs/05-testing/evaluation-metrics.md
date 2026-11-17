# Định Nghĩa Chỉ Số Đánh Giá Đo Lường (Evaluation Metrics)

## 1. Đánh Giá Phiên Âm Tiếng Nói (ASR)
- **Word Error Rate (WER):**
  $$WER = \frac{S + D + I}{N}$$
  Trong đó: $S$ là số từ thay thế, $D$ là số từ bị xóa, $I$ là số từ chèn thêm, $N$ là tổng số từ tham chiếu.
- **Character Error Rate (CER):** Bổ sung cho tiếng Việt sau khi thống nhất quy tắc dấu câu/chữ hoa.
- **Timestamp Error:** Sai số tuyệt đối trung bình của mốc bắt đầu/kết thúc segment.

## 2. Đánh Giá Tách Người Nói (Diarization)
- **Diarization Error Rate (DER):** Tổng tỷ lệ lỗi gán nhãn người nói sai, bỏ sót tiếng nói và nhận diện nhầm tiếng ồn.
- **Jaccard Error Rate (JER):** Đo mức chồng lấp giữa speaker hypothesis và reference.

## 3. Đánh Giá Tóm Tắt & Hỏi Đáp RAG
- **ROUGE-1, ROUGE-2, ROUGE-L:** Đánh giá độ trùng khớp n-gram giữa bản tóm tắt tự động và bản tóm tắt mẫu.
- **Faithfulness Score:** Tỷ lệ phần trăm các luận điểm trong câu trả lời có bằng chứng trực tiếp từ ngữ cảnh trích dẫn.
- **Retrieval Recall@k / MRR:** Đo segment evidence có được xếp trong top-k hay không.
- **Citation Precision/Recall:** Citation có thực sự hỗ trợ claim và có bỏ sót evidence quan trọng hay không.

## 4. Đánh Giá Vận Hành

- Queue wait time, provider latency p50/p95/p99 và task failure rate.
- CPU/RAM/disk, cold-start embedding model và network egress.
- Chi phí Gladia/LLM/EC2 trên mỗi giờ audio.

Không sử dụng transcript/summary fallback demo để tính bất kỳ chỉ số AI nào.
