# Bản Đặc Tả Bộ Dữ Liệu Đánh Giá Thực Nghiệm

## 1. Yêu Cầu Kỹ Thuật Dữ Liệu Âm Thanh
- Ngôn ngữ: Tiếng Việt đa vùng miền, có tiếng đệm và code-switching.
- Định dạng: WAV/MP3/M4A/WebM; lưu sample rate/channel gốc trong metadata.
- Số lượng người nói: 2 đến 6; có mẫu nói chồng, tiếng ồn, vọng và microphone xa.
- Dữ liệu phải có consent và được ẩn danh trước khi đưa vào repo/báo cáo.

## 2. Cấu Trúc Ground-Truth
- Mỗi tệp âm thanh trong `data/sample_audio/` có một tệp JSON tương ứng trong `data/ground_truth/`:
  - Mốc thời gian từng câu phát biểu (`start`, `end`).
  - Nhãn người nói chính xác (`speaker`).
  - Nội dung chuẩn chính tả (`text`).
  - Bộ 5 câu hỏi QA kèm câu trả lời chuẩn và trích dẫn timestamp.

## 3. Phân tập và version

- Tách Dev để tinh chỉnh prompt/config và Test khóa trước đánh giá cuối.
- Mỗi sample có ID, checksum, duration, speaker count, noise tag và consent status.
- Mỗi lần chạy ghi provider/model/version, ngày chạy và cấu hình.
- Không trộn output fallback vào dataset đánh giá.
