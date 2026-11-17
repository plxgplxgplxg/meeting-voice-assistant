# PRODUCT REQUIREMENTS DOCUMENT

**Sản phẩm:** Meeting Voice Assistant  
**Phiên bản:** 2.0  
**Cập nhật theo code:** 16/11/2026

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
5. Worker gọi Gemini/OpenAI để tóm tắt và trích xuất action item.
6. Người dùng biên tập transcript, phát/tua audio.
7. Người dùng hỏi đáp, nhấn citation để nghe lại.
8. Xuất TXT/SRT/VTT/JSON/DOCX.

### 3.2. Luồng hỗ trợ

- Quản lý thành viên project với owner/editor/viewer.
- Tìm kiếm/lọc meeting.
- Link chia sẻ token.
- Gói Free/Pro/Business, usage theo phút.
- VietQR checkout và SePay webhook.
- Cập nhật hồ sơ và đổi mật khẩu.

### 3.3. Không thuộc release hiện tại

- Live ASR thật trong lúc đang nói.
- Offline-first/IndexedDB và reconnect audio chunks.
- S3/MinIO, Kubernetes hoặc multi-node worker.
- Vector database bền vững.
- Regenerate summary sau biên tập.
- Link chia sẻ có mật khẩu/expiry/revoke.
- Mobile app native.

## 4. Yêu cầu sản phẩm ưu tiên

| Ưu tiên | Yêu cầu | Chỉ số nghiệm thu |
|---|---|---|
| P0 | Upload và xử lý audio thật | Transcript phản ánh đúng file, meeting chuyển `processing` → `completed` |
| P0 | Transcript Studio | Sửa text, rename speaker, delete segment giữ sau reload |
| P0 | Summary/action items | Kết quả sinh từ transcript thật |
| P0 | RAG citation | Mỗi citation có segment và timestamp seek được |
| P0 | Export | DOCX/JSON/SRT tải và mở được |
| P1 | Project | Meeting upload trong project xuất hiện đúng project |
| P1 | Auth/profile | Register/login/update/password hoạt động |
| P1 | Deploy một EC2 | Service healthy và dữ liệu tồn tại sau restart |
| P2 | Share | Viewer link dùng được; cần hardening trước public production |
| P2 | Billing | Checkout/webhook/idempotency hoạt động với SePay |

## 5. Trải nghiệm người dùng

### 5.1. Màn hình

- `/`: project selector, meeting dashboard, upload modal, trạng thái processing.
- `/live`: thu microphone và gửi bản ghi để xử lý batch.
- `/meetings/{id}`: timeline, transcript, summary/action items, chat, export, share.
- `/login`, `/register`: xác thực.
- `/settings/profile`: hồ sơ và mật khẩu.

### 5.2. Trạng thái bắt buộc

- Loading rõ ràng, không chặn toàn ứng dụng khi task chạy lâu.
- Meeting processing có đường quay lại một click.
- Error upload/provider phải có thông báo hành động được.
- Không gọi dữ liệu fallback là kết quả xử lý thật.

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
| Thiếu/sai API key | Hệ thống trả fallback demo | Startup checklist và E2E xác minh nội dung audio |
| EC2 thiếu RAM | AI Service/worker OOM | Tối thiểu 8 GB RAM + swap; worker concurrency 1 nếu cần |
| HTTP không có TLS | Microphone bị trình duyệt chặn | Domain + HTTPS trước kiểm thử `/live` |
| Share authorization chưa đồng nhất | Rò rỉ tài nguyên theo UUID | Không public rộng; hoàn thiện access dependency trước production |
| Không có migration | Khó nâng schema | Bổ sung Alembic trước dữ liệu production dài hạn |
| Lưu file local volume | Mất dữ liệu khi xóa volume/instance | Backup định kỳ, sau đó chuyển S3 nếu cần |

## 8. Điều kiện release

- Toàn bộ automated test/build vượt qua.
- Compose production resolve được với `.env` thật và service healthy.
- Hoàn thành checklist E2E thật trong SRS/runbook.
- Đã bật HTTPS nếu nghiệm thu microphone.
- Có backup thủ công đầu tiên và thử restore.
- Nếu public Internet: phải đóng các gap authorization/token đã nêu trong SRS.

## 9. Tài liệu chuẩn

- [SRS](srs.md)
- [Use cases](use-cases.md)
- [Kiến trúc hệ thống](../03-architecture/system-architecture.md)
- [Runbook triển khai](../deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md)
