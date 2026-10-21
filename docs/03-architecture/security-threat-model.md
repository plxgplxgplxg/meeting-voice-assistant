# Mô Hình Rủi Ro & An Toàn Bảo Mật (Threat Model)

## 1. Nhận Diện Tài Sản Cần Bảo Vệ
- Tệp âm thanh ghi âm cuộc họp (dữ liệu nhạy cảm của tổ chức).
- Văn bản phiên âm và danh sách tóm tắt nội dung bảo mật.
- API Keys và thông tin đăng nhập các dịch vụ đám mây.

## 2. Phân Tích Mối Đe Dọa (STRIDE)
- **Spoofing:** Giả mạo danh tính để truy cập cuộc họp của nhóm khác -> Cô lập dữ liệu theo phân quyền phiên làm việc.
- **Tampering:** Sửa đổi trái phép nội dung transcript -> Lưu lịch sử phiên bản chỉnh sửa (versioning).
- **Information Disclosure:** Rò rỉ tệp ghi âm qua đường dẫn lưu trữ -> Sử dụng Presigned URL có thời hạn ngắn.
- **Denial of Service:** Tải file dung lượng quá lớn gây tắc nghẽn worker -> Giới hạn kích thước file upload (< 500MB) và rate-limiting.
