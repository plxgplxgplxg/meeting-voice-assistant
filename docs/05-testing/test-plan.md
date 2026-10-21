# Kế Hoạch Kiểm Thử Phần Mềm (ISO/IEC/IEEE 29119)

## 1. Phạm Vi Kiểm Thử
- **Unit Testing:** Kiểm thử các hàm tính toán, chunking, validate schema, và chuyển đổi dữ liệu.
- **Integration Testing:** Kiểm thử kết nối CSDL PostgreSQL, hàng đợi Redis, và giao tiếp giữa Backend API và AI Service.
- **Performance / Latency Testing:** Đo độ trễ xử lý streaming qua WebSocket và thời gian suy luận của mô hình ASR.

## 2. Công Cụ Kiểm Thử
- **Backend:** `pytest`, `pytest-asyncio`, `httpx`.
- **Frontend:** `jest`, `@testing-library/react`.
