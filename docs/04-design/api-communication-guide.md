# Hướng Dẫn Giao Tiếp API & Quy Chuẩn (API Guidelines)

## 1. Chuẩn Hóa Mã Trả Về (HTTP Status Codes)
- `200 OK`: Truy vấn hoặc xử lý thành công.
- `201 Created`: Tạo mới tài nguyên thành công.
- `202 Accepted`: Tiếp nhận tác vụ xử lý nền (Async processing).
- `400 Bad Request`: Dữ liệu đầu vào không hợp lệ.
- `404 Not Found`: Không tìm thấy tài nguyên.
- `500 Internal Server Error`: Lỗi hệ thống nội bộ.

## 2. Cấu Trúc Báo Lỗi Tiêu Chuẩn (RFC 7807)
```json
{
  "error": {
    "code": "MEETING_NOT_FOUND",
    "message": "Không tìm thấy cuộc họp với mã định danh cung cấp.",
    "path": "/api/v1/meetings/550e8400-e29b-41d4-a716-446655440000"
  }
}
```
