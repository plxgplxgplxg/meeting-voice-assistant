# Báo Cáo Hoàn Thành: Chuyển Đổi Use Cases Từ TECHTACK-VOICE Sang Meeting-Voice-Assistant

Tài liệu này tổng hợp chi tiết toàn bộ các use cases đã được chuyển đổi, tái cấu trúc kiến trúc (từ NestJS/Prisma sang FastAPI/SQLAlchemy Async) và triển khai lại giao diện người dùng theo phong cách thiết kế tối giản (**Clean Minimalist** với bảng màu **Slate + Emerald**).

---

## 1. Danh Mục Các Use Case Đã Chuyển Đổi

### A. Quản Trị Xác Thực & Người Dùng (Auth & User Profile)
- **Đăng ký tài khoản (`/api/v1/auth/register`)**: Mã hóa mật khẩu bảo mật chuẩn `bcrypt`, tự động liên kết gói **Free** mặc định với thời lượng 60 phút.
- **Đăng nhập (`/api/v1/auth/login`)**: Cấp phát cặp JWT Access Token (hạn 60 phút) và Refresh Token (hạn 7 ngày).
- **Làm mới Token (`/api/v1/auth/refresh`)**: Xoay vòng Access Token mà không cần đăng nhập lại.
- **Quản lý Hồ sơ (`/api/v1/auth/me`, `/api/v1/users/me`)**: Cập nhật thông tin họ tên, tra cứu vai trò và định danh.
- **Đổi mật khẩu (`/api/v1/users/me/password`)**: Xác thực mật khẩu cũ trước khi cập nhật mật khẩu mới.

### B. Không Gian Làm Việc & Dự Án (Workspaces & Projects)
- **Quản lý Dự án (`/api/v1/projects`)**: CRUD dự án không gian làm việc nhóm.
- **Quản lý Thành viên (`/api/v1/projects/{id}/members`)**: Phân quyền chi tiết theo ma trận: `owner`, `editor`, `viewer`.
- **Gán Cuộc Họp Vào Dự Án (`/api/v1/projects/{id}/meetings/{meeting_id}`)**: Liên kết nhiều cuộc họp vào một dự án làm việc chung.

### C. Cuộc Họp & Phiên Âm Chi Tiết (Meetings & Transcripts)
- **Quản lý Cuộc Họp (`/api/v1/meetings`)**: Tìm kiếm theo tiêu đề, lọc theo trạng thái (`created`, `processing`, `completed`), xóa mềm (`soft delete`).
- **Chia sẻ Cuộc họp (`/api/v1/meetings/{id}/share`)**: Sinh token liên kết chia sẻ cho người ngoài xem biên bản không cần tài khoản.
- **Biên tập Phiên âm (`/api/v1/transcripts`)**:
  - Chỉnh sửa nội dung từng câu nói inline trực tiếp trên giao diện (`PATCH /transcripts/{id}`).
  - Đổi tên người nói đồng loạt (`POST /transcripts/meetings/{id}/rename-speaker`), ví dụ đổi `Speaker 1` thành `Giám Đốc An`.
  - Xóa đoạn hội thoại thừa (`DELETE /transcripts/{id}`).

### D. Bộ Máy Xuất Biên Bản Đa Định Dạng (Export Service)
Porting toàn bộ bộ máy xuất biên bản của TECHTACK sang Python với chuẩn hóa typography và màu sắc:
- **Microsoft Word (.docx)**: Tạo file Word chứa tiêu đề chuẩn, bảng tóm tắt điều hành, danh sách việc cần làm (Action Items) và bảng phiên âm phân vai kèm mốc thời gian.
- **Văn bản thuần (.txt)**: Biên bản họp tinh gọn UTF-8.
- **Phụ đề SubRip (.srt)**: Chuẩn định dạng `00:00:00,000 --> 00:00:10,000` kèm nhãn người nói.
- **Phụ đề WebVTT (.vtt)**: Chuẩn phụ đề Web `WEBVTT` hỗ trợ thẻ `<v Speaker>`.
- **Dữ liệu JSON (.json)**: Toàn bộ cấu trúc metadata, tóm tắt và mảng transcript segments.

### E. Gói Dịch Vụ, Hạn Mức & Thanh Toán VietQR (Billing & SePay)
- **Hệ thống Gói & Hạn mức (`/api/v1/plans`)**:
  - `Free`: 60 phút/tháng, 0 VNĐ.
  - `Pro`: 600 phút/tháng, 99.000 VNĐ.
  - `Unlimited`: Vô hạn thời lượng, 299.000 VNĐ.
- **Cổng Thanh toán VietQR (`/api/v1/payments`)**:
  - Sinh mã đơn hàng chuẩn format `MVA######`.
  - Sinh URL ảnh VietQR động liên kết ngân hàng MBBank qua SePay.
  - Webhook nhận thông báo chuyển khoản tự động, quét mã đơn hàng trong nội dung, kích hoạt gói dịch vụ tức thì và đảm bảo tính bất biến (idempotent).

### F. Giao Diện Người Dùng Studio (Frontend Redesign)
Tuân thủ tiêu chuẩn thiết kế **Clean Minimalist Frontend** (`/Users/plxg/.agents/skills/clean-minimalist-frontend`):
- **Bảng màu**: Slate 900 (`#0f172a`) + Emerald 600 (`#059669`).
- **Quy tắc không biểu tượng cảm xúc**: 100% sử dụng icon vector Lucide SVG (`w-3.5 h-3.5` hoặc `w-4 h-4`), tuyệt đối không dùng emoji.
- **Scrubber Audio & Speaker Timeline**:
  - Đồng bộ âm thanh playback với thanh trượt tiến trình.
  - Tách làn người nói với dải màu sắc trực quan (Emerald, Indigo, Teal, Violet, Amber).
  - Điều chỉnh tốc độ phát (0.75x, 1x, 1.25x, 1.5x, 2x) và thanh trượt phóng to thu nhỏ (Zoom Slider 1x - 4x).
  - Bấm vào bất kỳ khối hội thoại hoặc mốc thời gian để tua âm thanh ngay lập tức.
- **Transcript Feed Tương Tác**:
  - Highlight đoạn thoại đang phát đồng bộ theo audio player.
  - Chế độ cuộn tự động (Auto-scroll toggle).
  - Tìm kiếm nội dung hoặc tên người nói theo thời gian thực.
  - Hộp thoại đổi tên người nói hàng loạt.
- **Trợ Lý AI Hỏi Đáp (RAG Assistant)**:
  - Khung chat tương tác trả lời câu hỏi dựa trên nội dung cuộc họp.
  - Trích dẫn trực quan (`CitationPills`): bấm vào `[Speaker 1 • 01:25]` sẽ tự động tua Audio Scrubber đến đúng giây 85.
- **Mission Control Banner**: Card theo dõi trạng thái phân tích trong nền với nút 1-click xem tiến trình (Rule 4).

---

## 2. Kết Quả Kiểm Thử Tự Động (Verification Results)

### A. Backend Pytest
Toàn bộ 4 test suites của backend-api đã vượt qua kiểm thử thành công:
```bash
pytest backend-api/tests
============================= test session starts ==============================
platform darwin -- Python 3.13.10, pytest-9.1.1
backend-api/tests/test_auth.py .                                         [ 25%]
backend-api/tests/test_exports.py .                                      [ 50%]
backend-api/tests/test_health.py .                                       [ 75%]
backend-api/tests/test_payments.py .                                     [100%]
======================== 4 passed in 1.29s ========================
```

### B. Frontend Next.js Production Build
Biên dịch thành công toàn bộ các routes của ứng dụng Next.js:
```bash
$ next build
   Creating an optimized production build ...
 ✓ Compiled successfully
 ✓ Linting and checking validity of types 
 ✓ Collecting page data 
 ✓ Generating static pages (8/8)
 ✓ Finalizing page optimization 

Route (app)                              Size     First Load JS
┌ ○ /                                    5.9 kB          101 kB
├ ○ /_not-found                          871 B            88 kB
├ ○ /live                                4.46 kB        91.6 kB
├ ○ /login                               2.84 kB        98.2 kB
├ ƒ /meetings/[id]                       10.9 kB         106 kB
├ ○ /register                            2.99 kB        98.3 kB
└ ○ /settings/profile                    4.37 kB        91.5 kB
```

---

## 3. Hướng Dẫn Vận Hành

### Chạy Backend API
```bash
cd backend-api
source venv/bin/activate # nếu có
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Chạy Frontend
```bash
cd frontend
pnpm dev
```
Truy cập giao diện tại: `http://localhost:3000`
