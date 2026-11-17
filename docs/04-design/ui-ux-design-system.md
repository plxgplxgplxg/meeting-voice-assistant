# UI/UX DESIGN SYSTEM HIỆN HÀNH

## 1. Nguyên tắc

- Navigation phẳng: meeting/project, thu microphone, hồ sơ/quota.
- Tác vụ audio chạy nền; UI không khóa toàn màn hình.
- Transcript, timeline, summary và chat nằm trong một workspace.
- Dùng Lucide SVG, không dùng emoji trong UI/log.
- Text chính tối thiểu 14 px; badge tối thiểu 12 px.
- Lỗi phải nói được hành động tiếp theo.

## 2. Route

| Route | Mục đích |
|---|---|
| `/` | Dashboard, project selector, upload, search/filter |
| `/live` | Thu microphone và upload WebM để xử lý batch |
| `/meetings/{id}` | Timeline, transcript, summary, action items, RAG, export/share |
| `/login`, `/register` | Xác thực |
| `/settings/profile` | Hồ sơ và mật khẩu |

## 3. Trạng thái meeting

- `created`: vừa tạo, chưa có file.
- `processing`: đã nhận file/đang ở queue hoặc provider.
- `completed`: transcript/summary đã lưu.
- `failed`: mục tiêu cần hiển thị rõ; worker hiện chưa đặt trạng thái này nhất quán.

Trang chi tiết polling khi `processing`. Dashboard hiển thị card/banner task đang chạy nhưng chưa có phần trăm tiến độ thật.

## 4. Component map

| Component | Trách nhiệm |
|---|---|
| `ProjectSelector` | Chọn/tạo project |
| `SpeakerTimeline` | Audio player, lane speaker, seek |
| `TranscriptFeed` | Search/edit/rename/delete segment |
| `AssistantChatPane` | Chat history, ask, citation seek |
| `ExportDropdown` | Download format |
| `QuotaBadge` | Subscription usage và mở pricing |
| `PricingModal`/`VietQRModal` | Checkout và polling payment |

## 5. Accessibility và responsive

- Mọi icon-only button cần `title` hoặc `aria-label`.
- Modal cần bổ sung focus trap/Escape và phục hồi focus; code hiện chưa hoàn chỉnh.
- Desktop dùng split pane; mobile xếp dọc.
- Không dùng màu như tín hiệu duy nhất; status cần label text.
- Microphone cần HTTPS trên domain production và thông báo rõ khi quyền bị từ chối.

## 6. Khoảng trống UI còn lại

- Route guard thống nhất cho trang cần đăng nhập.
- Error boundary/toast thay cho `alert`/`confirm`.
- Trạng thái `failed` và nút retry processing.
- Edit action item trong UI dù backend đã có PATCH.
- Quản lý member/project chi tiết ngoài selector.
- Share permission/expiry/revoke.
- Loại bỏ toàn bộ `text-[10px]`/`text-[11px]` còn sót để đạt chuẩn đọc.
