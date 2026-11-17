# PRODUCT REQUIREMENTS DOCUMENT

**Sản phẩm:** Meeting Voice Assistant  
**Phiên bản:** 3.0  
**Cập nhật theo code:** 17/11/2026

## 1. Tuyên bố sản phẩm

Meeting Voice Assistant giúp nhóm làm việc biến file ghi âm hoặc bản thu microphone thành transcript phân tách người nói, bản tóm tắt, action items và nguồn hỏi đáp có thể kiểm chứng bằng timestamp.

Giá trị cốt lõi không phải “AI trả lời hay”, mà là giảm thời gian lập biên bản trong khi vẫn cho người dùng quay lại đoạn audio làm bằng chứng.

## 2. Người dùng mục tiêu

| Persona | Nhu cầu |
|---|---|
| Sinh viên/nhóm đồ án | Ghi lại buổi hướng dẫn, theo dõi đầu việc |
| Nhóm sản phẩm/kỹ thuật | Tóm tắt quyết định và người phụ trách |
| Người quản lý dự án | Tổ chức meeting theo project, chia sẻ và xuất biên bản |
| Người xem | Đọc nội dung được chia sẻ và nghe lại đoạn trích dẫn |

## 3. Phạm vi release hiện tại

### 3.1. Luồng cốt lõi

1. Đăng ký/đăng nhập.
2. Tạo project.
3. Upload audio hoặc thu microphone rồi upload WebM.
4. Worker gọi Gladia để ASR + diarization.
5. Worker gọi Gemini/OpenAI để tóm tắt và trích xuất action item, đồng thời dựng chỉ mục tìm kiếm.
6. Người dùng biên tập transcript (có lịch sử và hoàn tác), phát/tua audio.
7. Người dùng hỏi đáp, nhấn citation để nghe lại.
8. Trợ lý cuộc họp đề xuất chỉnh sửa và sinh tài liệu; người dùng duyệt trước khi áp dụng.
9. Xuất TXT/SRT/VTT/JSON/DOCX.

### 3.2. Luồng hỗ trợ

- Quản lý thành viên project với owner/editor/viewer.
- Tìm kiếm/lọc meeting.
- Link chia sẻ token.
- Gói Free/Pro/Business (`free`, `pro`, `business`), usage theo phút, chu kỳ Free lăn 30 ngày; Free chỉ hỏi đáp có giới hạn số câu hỏi mỗi tháng, Pro/Business có thêm công cụ chỉnh sửa và tài liệu của trợ lý.
- VietQR checkout và SePay webhook.
- Cập nhật hồ sơ và đổi mật khẩu.

### 3.3. Không thuộc release hiện tại

- Live ASR thật trong lúc đang nói.
- Offline-first/IndexedDB và reconnect audio chunks.
- S3/MinIO, Kubernetes hoặc multi-node worker.
- Tìm kiếm xuyên nhiều cuộc họp trong một project (hạ tầng pgvector đã sẵn sàng).
- Link chia sẻ có mật khẩu/expiry/revoke.
- Mobile app native.

## 4. Yêu cầu sản phẩm ưu tiên

| Ưu tiên | Yêu cầu | Chỉ số nghiệm thu |
|---|---|---|
| P0 | Upload và xử lý audio thật | Transcript phản ánh đúng file, meeting chuyển `uploaded` → `ready`; lỗi hiển thị `failed` kèm lý do, không có dữ liệu giả |
| P0 | Transcript Studio | Sửa text, rename speaker, delete segment giữ sau reload |
| P0 | Summary/action items | Kết quả sinh từ transcript thật |
| P0 | RAG citation | Mỗi citation có segment và timestamp seek được |
| P0 | Export | DOCX/JSON/SRT tải và mở được |
| P1 | Meeting Assistant | Trợ lý trả lời có trích dẫn; mọi thay đổi chỉ là đề xuất, áp dụng sau khi duyệt, xem được trong lịch sử và hoàn tác về đúng văn bản cũ |
| P1 | Phiên bản transcript | Mỗi lần sửa tạo change set; xung đột revision trả 409; hoàn tác an toàn |
| P1 | Project | Meeting upload trong project xuất hiện đúng project |
| P1 | Auth/profile | Register/login/update/password hoạt động |
| P1 | Deploy một EC2 | Service healthy và dữ liệu tồn tại sau restart |
| P2 | Share | Viewer link dùng được; cần hardening trước public production |
| P2 | Billing | Checkout/webhook/idempotency hoạt động với SePay |

## 5. Trải nghiệm người dùng

### 5.1. Màn hình

- `/`: project selector, meeting dashboard, upload modal, trạng thái processing.
- `/live`: thu microphone và gửi bản ghi để xử lý batch.
- `/meetings/{id}`: timeline, transcript, summary/action items, trợ lý, tài liệu, lịch sử thay đổi, export, share.
- `/login`, `/register`: xác thực.
- `/settings/profile`: hồ sơ và mật khẩu.

### 5.2. Trạng thái bắt buộc

- Loading rõ ràng, không chặn toàn ứng dụng khi task chạy lâu.
- Meeting processing có đường quay lại một click.
- Error upload/provider phải có thông báo hành động được.
- Không gọi dữ liệu fallback là kết quả xử lý thật: engine `mock` chỉ có ở development và được gắn nhãn "Dữ liệu mẫu".
- Trợ lý không bao giờ tự sửa dữ liệu: đề xuất hiển thị diff với Duyệt / Sửa / Từ chối, và sau khi duyệt có thông báo Hoàn tác.

## 6. Chỉ số sản phẩm và kỹ thuật

| Nhóm | Chỉ số |
|---|---|
| Hoàn thành luồng | Tỷ lệ upload → completed |
| Chất lượng ASR | WER trên bộ audio tiếng Việt có ground truth |
| Chất lượng diarization | DER/JER trên bộ audio có nhãn speaker |
| Grounding | Citation precision/recall và faithfulness |
| Vận hành | Task failure rate, provider latency, queue wait time |
| Trải nghiệm | Thời gian tạo biên bản so với thao tác thủ công |

Không đặt mục tiêu latency tuyệt đối cho provider cloud trong tài liệu yêu cầu; phải đo và báo percentile từ dữ liệu thực nghiệm.

## 7. Rủi ro

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Thiếu/sai API key | Meeting `failed` với lý do rõ; `/health` báo `degraded` | Startup checklist và E2E xác minh nội dung audio |
| EC2 thiếu RAM | AI Service/worker OOM | Tối thiểu 8 GB RAM + swap; worker concurrency 1 nếu cần |
| HTTP không có TLS | Microphone bị trình duyệt chặn | Domain + HTTPS trước kiểm thử `/live` |
| Share link không có hạn/thu hồi | Link bị lộ vẫn dùng được | Quyền token đã thống nhất qua `MeetingAccessPolicy`; bổ sung expiry/revoke trước khi chia sẻ rộng |
| Agent thực hiện thay đổi ngoài ý muốn | Mất hoặc sai nội dung biên bản | Luồng đề xuất → duyệt, `expected_revision`, lịch sử + hoàn tác, token ủy quyền phạm vi một meeting, backend kiểm tra lại mọi đề xuất, giới hạn 200 thao tác |
| Prompt injection qua transcript | Agent bị dẫn dắt làm việc không được yêu cầu | Transcript luôn nằm trong thẻ dữ liệu không tin cậy; công cụ ghi chỉ tạo đề xuất; người dùng duyệt |
| Lưu file local volume | Mất dữ liệu khi xóa volume/instance | Backup định kỳ, sau đó chuyển S3 nếu cần |

## 8. Điều kiện release

- Toàn bộ automated test/build vượt qua.
- Compose production resolve được với `.env` thật và service healthy.
- Hoàn thành checklist E2E thật trong SRS/runbook.
- Đã bật HTTPS nếu nghiệm thu microphone.
- Có backup thủ công đầu tiên và thử restore.
- Nếu public Internet: chuyển token sang cookie HttpOnly và bổ sung expiry/revoke cho share link.

## 9. Tài liệu chuẩn

- [SRS](srs.md)
- [Use cases](use-cases.md)
- [Kiến trúc hệ thống](../03-architecture/system-architecture.md)
- [Runbook triển khai](../deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md)
