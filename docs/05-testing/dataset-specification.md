# Bản Đặc Tả Bộ Dữ Liệu Đánh Giá Thực Nghiệm

## 1. Yêu Cầu Kỹ Thuật Dữ Liệu Âm Thanh
- Ngôn ngữ: Tiếng Việt (chất giọng chuẩn, có thể pha lẫn tiếng đệm hội thoại).
- Định dạng: WAV / MP3, tần số lấy mẫu tối thiểu 16kHz, đơn kênh (Mono).
- Số lượng người nói: 2 đến 4 người tham gia trao đổi.

## 2. Cấu Trúc Ground-Truth
- Mỗi tệp âm thanh trong `data/sample_audio/` có một tệp JSON tương ứng trong `data/ground_truth/`:
  - Mốc thời gian từng câu phát biểu (`start`, `end`).
  - Nhãn người nói chính xác (`speaker`).
  - Nội dung chuẩn chính tả (`text`).
  - Bộ 5 câu hỏi QA kèm câu trả lời chuẩn và trích dẫn timestamp.
