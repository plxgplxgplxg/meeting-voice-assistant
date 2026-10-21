# Đặc Tả 5 Use Cases Cốt Lõi

## UC-01: Ghi Âm & Phiên Âm Trực Tiếp Cuộc Họp
- **Actor:** Người tham dự / Thư ký.
- **Pre-conditions:** Trình duyệt cấp quyền Microphone, kết nối mạng ổn định.
- **Main Flow:**
  1. Người dùng bấm nút "Bắt đầu cuộc họp mới".
  2. Hệ thống khởi tạo WebSocket streaming và nhận audio chunks.
  3. AI Service lọc giọng nói (VAD) và gửi transcript về UI theo thời gian thực.
  4. Người dùng bấm "Kết thúc cuộc họp", hệ thống lưu toàn bộ dữ liệu.

## UC-02: Tải Lên Tệp Âm Thanh & Tách Người Nói
- **Actor:** Người dùng có sẵn file ghi âm cuộc họp.
- **Main Flow:**
  1. Người dùng kéo thả tệp âm thanh vào hệ thống.
  2. Hệ thống tải tệp vào Object Storage và đẩy task vào hàng đợi.
  3. Worker chạy tách người nói (Pyannote) và phiên âm (Whisper).
  4. Hệ thống thông báo khi quá trình xử lý hoàn tất.

## UC-03: Biên Tập & Chuẩn Hóa Bản Ghi Âm
- **Actor:** Thư ký cuộc họp.
- **Main Flow:**
  1. Mở giao diện Transcript Studio.
  2. Nghe lại đoạn âm thanh tương ứng với từng câu phát biểu.
  3. Chỉnh sửa chữ sai chính tả hoặc đổi nhãn "Speaker 1" thành tên cụ thể.
  4. Lưu thay đổi; hệ thống tự động cập nhật lại vector embeddings.

## UC-04: Tự Động Sinh Tóm Tắt & Danh Sách Công Việc
- **Actor:** Người quản lý / Người tham dự.
- **Main Flow:**
  1. Yêu cầu hệ thống tổng hợp cuộc họp.
  2. LLM đọc toàn bộ transcript và trích xuất: Nội dung chính, Quyết định, Action Items.
  3. Hiển thị danh sách công việc có người phụ trách và hạn chót.

## UC-05: Hỏi Đáp Nội Dung Kèm Trích Dẫn Nguồn
- **Actor:** Mọi thành viên trong nhóm.
- **Main Flow:**
  1. Người dùng nhập câu hỏi vào ô chat của cuộc họp.
  2. Hệ thống tìm kiếm đoạn hội thoại phù hợp qua vector similarity search (pgvector).
  3. LLM sinh câu trả lời kèm thẻ trích dẫn [Speaker, timestamp].
  4. Người dùng bấm vào trích dẫn để nhảy trực tiếp đến đoạn audio liên quan.
