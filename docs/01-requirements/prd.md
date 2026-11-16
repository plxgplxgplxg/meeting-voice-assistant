# Product Requirements Document (PRD)

## 1. Tổng quan & Thông tin chung (Metadata)

- **Tên sản phẩm:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp (Meeting Transcription, Summarization, and Question Answering System)
- **Người phụ trách (Owner / PM):** Nguyễn Phương Linh (MSSV: 20224871)
- **Các bên liên quan (Stakeholders):**
  - Giảng viên hướng dẫn & Hội đồng đánh giá đồ án tốt nghiệp
  - Tech Lead / AI Engineer: Phụ trách pipeline ASR, Diarization, RAG và LLM
  - Fullstack Developer: Phụ trách Backend API (FastAPI) và Frontend Web (Next.js)
  - QA / Tester: Kiểm thử chất lượng phần mềm (ISO/IEC 25010) và độ chính xác mô hình AI
- **Trạng thái:** Đang xem xét (In Review)
- **Ngày cập nhật gần nhất:** 2026-10-22

---

## 2. Bối cảnh & Mục đích (Why)

### 2.1. Lý do xây dựng
Trong môi trường học thuật và doanh nghiệp, việc ghi chép biên bản cuộc họp thủ công tồn tại nhiều hạn chế:
- **Tốn thời gian:** Người tham gia mất trung bình 30 - 60 phút sau mỗi buổi họp để nghe lại băng ghi âm, hoàn thiện biên bản và tổng hợp danh sách công việc.
- **Dễ bỏ sót thông tin:** Thông tin quan trọng, quyết định then chốt và phân công trách nhiệm thường bị thất lạc hoặc ghi chép thiếu nhất quán.
- **Khó khăn trong tra cứu:** Khi số lượng cuộc họp tăng lên, việc tìm lại một nội dung hoặc phát biểu cụ thể đòi hỏi phải nghe lại toàn bộ bản ghi âm từ đầu đến cuối mà không có mốc thời gian (timestamp) trực quan.

### 2.2. Tầm nhìn chiến lược
Xây dựng hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp ứng dụng AI hiện đại (Speech-to-Text, Speaker Diarization, RAG), giúp tự động hóa chu trình ghi chép - trích xuất - tra cứu nội dung cuộc họp tiếng Việt, nâng cao hiệu suất làm việc nhóm và bảo đảm tính minh bạch, có bằng chứng xác thực (grounded citation) cho mọi thông tin truy xuất.

### 2.3. Phạm vi sản phẩm (In-Scope vs. Out-of-Scope)

#### In-Scope (Phiên bản hiện tại)
- Thu âm trực tiếp trên trình duyệt hoặc tải lên tệp âm thanh có sẵn (WAV, MP3, M4A).
- Phiên âm tiếng Việt tự động kèm mốc thời gian bắt đầu - kết thúc cho từng phân đoạn (segment).
- Phân đoạn và nhận diện người nói (Speaker Diarization), hỗ trợ đổi tên nhãn người nói.
- Trình biên tập Transcript Studio cho phép đồng bộ phát lại audio và chỉnh sửa trực tiếp nội dung văn bản.
- Tự động sinh biên bản tóm tắt đa cấp độ: Tổng quan, Các quyết định chính, Danh sách công việc cần làm (Action Items gồm việc, người phụ trách, hạn chót nếu có).
- Trợ lý hỏi đáp RAG (Retrieval-Augmented Generation) trên từng cuộc họp cụ thể, bắt buộc kèm trích dẫn nguồn (speaker, timestamp) chính xác.
- Chia sẻ cuộc họp qua liên kết (Shareable Link) với phân quyền linh hoạt theo từng cuộc họp: Chỉ xem (Viewer) hoặc Cho phép chỉnh sửa (Editor).
- Xuất biên bản cuộc họp ra các định dạng chuẩn: TXT, DOCX, JSON, SRT/VTT.

#### Out-of-Scope (Chưa thực hiện trong phiên bản này)
- Hệ thống thanh toán thương mại, quản lý subscription / billing.
- Tích hợp bot tự động tham gia cuộc họp video của bên thứ ba (Zoom Bot, Google Meet Bot, MS Teams Bot).
- Đăng nhập qua mạng xã hội doanh nghiệp hoặc tích hợp danh bạ Active Directory/LDAP.
- Huấn luyện lại từ đầu (pre-training) các mô hình nền tảng ASR hoặc LLM cỡ lớn.
- Thay thế hoàn toàn quyết định kiểm duyệt biên bản pháp lý của con người.

---

## 3. Đối tượng sử dụng & User Stories (Who)

### 3.1. Chân dung người dùng (User Personas)

1. **Chủ cuộc họp (Meeting Owner)**
   - *Đặc điểm:* Người trực tiếp ghi âm hoặc tải lên tệp âm thanh cuộc họp. Có toàn quyền quản lý, chỉnh sửa, xóa cuộc họp, sinh link chia sẻ và phân quyền (View/Edit) cho người khác.
   - *Điểm đau (Pain points):* Mệt mỏi vì phải nghe đi nghe lại băng ghi âm để gõ từng chữ, tốn thời gian chia sẻ biên bản cho từng người, khó kiểm soát ai được sửa ai chỉ được xem.

2. **Người chỉnh sửa (Collaborator - Editor)**
   - *Đặc điểm:* Đồng nghiệp hoặc thành viên được Chủ cuộc họp gửi link chia sẻ với quyền Edit để hỗ trợ hoàn thiện biên bản.
   - *Điểm đau (Pain points):* Cần rà soát đối soát âm thanh nhanh, sửa lỗi chính tả từ ngữ chuyên ngành, gán lại tên người nói thật và xuất biên bản nhanh chóng mà không cần qua nhiều bước trung gian.

3. **Người xem (Collaborator - Viewer)**
   - *Đặc điểm:* Người nhận link chia sẻ với quyền View (hoặc thành viên cần nắm thông tin nhưng không có thẩm quyền sửa đổi).
   - *Điểm đau (Pain points):* Cần nắm nhanh các quyết định đã chốt, ai chịu trách nhiệm việc gì, và muốn hỏi đáp tra cứu tức thì qua Trợ lý RAG mà không làm xáo trộn dữ liệu gốc.

### 3.2. Câu chuyện người dùng (User Stories)

| Mã ID | Câu chuyện người dùng (User Story) | Giá trị mang lại |
|---|---|---|
| **US-01** | Với tư cách là **Chủ cuộc họp**, tôi muốn tải tệp ghi âm lên hoặc thu âm trực tiếp, để hệ thống tự động bóc băng thành văn bản kèm nhãn từng người nói. | Giảm 80% công sức gõ văn bản thủ công. |
| **US-02** | Với tư cách là **Chủ cuộc họp hoặc Editor**, tôi muốn vừa nghe lại vừa sửa từ ngữ chuyên ngành và gán tên thật cho người nói trong Transcript Studio, để biên bản đạt độ chính xác cao nhất. | Kiểm soát chất lượng nội dung nhanh chóng và trực quan. |
| **US-03** | Với tư cách là **Chủ cuộc họp hoặc Editor**, tôi muốn hệ thống tự động trích xuất danh sách Action Items và Quyết định, để tôi bàn giao công việc ngay sau cuộc họp. | Rút ngắn thời gian ban hành biên bản và theo dõi tiến độ. |
| **US-04** | Với tư cách là **Người xem (Viewer) hoặc Editor**, tôi muốn đặt câu hỏi tự nhiên về nội dung cuộc họp và nhận câu trả lời có kèm timestamp, để tôi kiểm tra lại tính chính xác từ âm thanh gốc chỉ với một cú nhấp chuột. | Tra cứu tức thì, tránh hiểu nhầm nội dung cuộc thảo luận. |
| **US-05** | Với tư cách là **Chủ cuộc họp hoặc Editor**, tôi muốn xuất biên bản dưới dạng file DOCX hoặc TXT, để gửi cho các bên liên quan lưu trữ hoặc in ấn. | Dễ dàng chia sẻ qua email hoặc đưa vào hồ sơ lưu trữ dự án. |
| **US-06** | Với tư cách là **Chủ cuộc họp**, tôi muốn tạo liên kết chia sẻ (Shareable Link) với quyền "Chỉ xem" (Viewer) hoặc "Chỉnh sửa" (Editor), để đồng nghiệp truy cập nhanh mà vẫn bảo đảm phân quyền an toàn. | Chia sẻ linh hoạt theo từng cuộc họp tương tự Google Docs. |
| **US-07** | Với tư cách là **Chủ cuộc họp**, tôi muốn có thể thay đổi quyền hạn hoặc thu hồi (Revoke) link chia sẻ bất kỳ lúc nào, để kiểm soát chặt chẽ quyền riêng tư dữ liệu cuộc họp. | Ngăn chặn truy cập trái phép khi tài liệu đã kết thúc chu trình chia sẻ. |

---

## 4. Yêu cầu tính năng & Chức năng (What)

### 4.1. Luồng người dùng tổng thể (User Flow)

```
[Bắt đầu]
   ├──> Lựa chọn 1: Thu âm trực tiếp trên Web Browser
   └──> Lựa chọn 2: Tải lên tệp âm thanh có sẵn (WAV, MP3, M4A)
           │
           ▼
   [Hệ thống kiểm tra tệp / khởi tạo phiên]
           │
           ▼
   [Xử lý nền: VAD -> ASR -> Speaker Diarization]
           │
           ▼
   [Hiển thị kết quả tại Transcript Studio]
           │
           ├──> Chỉnh sửa văn bản / đổi tên Speaker / đồng bộ Audio Player
           ├──> Hệ thống tự động sinh Tóm tắt & Action Items (Background LLM Task)
           ├──> Hệ thống tạo Vector Embeddings & Index vào pgvector
           │
           ▼
   [Tương tác hậu cuộc họp]
           ├──> Đọc bản tóm tắt và danh sách việc cần làm
           ├──> Hỏi đáp RAG với Trợ lý AI (kèm nguồn trích dẫn)
           ├──> Chia sẻ cuộc họp qua liên kết (Share Link: View / Edit)
           └──> Xuất biên bản (TXT, DOCX, JSON, SRT)
```

### 4.2. Yêu cầu chức năng chi tiết (Functional Requirements)

#### FR-01: Thu âm trực tiếp (Real-time Recording)
- Giao diện có nút điều khiển Start Recording, Pause, Resume, Stop.
- Bắt buộc kiểm tra quyền Microphone của trình duyệt trước khi ghi.
- Hiển thị sóng âm thanh (Audio Visualizer) và bộ đếm thời gian thực.
- Gửi các audio chunks qua WebSocket/SSE lên backend để xử lý liên tục.

#### FR-02: Tải lên và Quản lý tệp âm thanh (Audio File Upload)
- Hỗ trợ kéo thả (drag & drop) tệp âm thanh với định dạng: `.mp3`, `.wav`, `.m4a`.
- Giới hạn dung lượng tệp: tối đa 200 MB; thời lượng tối đa 120 phút mỗi cuộc họp.
- Validate tệp trước khi đẩy vào Object Storage (MinIO/S3) và hàng đợi tác vụ Redis.
- Hiển thị thanh tiến trình xử lý (Progress bar: Uploading -> Transcribing -> Diarizing -> Indexing).

#### FR-03: Nhận diện giọng nói & Phân đoạn người nói (ASR & Diarization)
- Tự động tách lời nói thành các phân đoạn văn bản kèm `start_time` và `end_time`.
- Gán nhãn người nói tự động (`SPEAKER_00`, `SPEAKER_01`, ...).
- Cho phép người dùng chỉnh sửa nhãn người nói đồng loạt (Rename speaker) cho toàn bộ cuộc họp.

#### FR-04: Trình biên tập Transcript Studio
- Danh sách câu thoại hiển thị theo dạng dòng thời gian (timeline).
- Tích hợp trình phát âm thanh (Audio Player) đồng bộ với văn bản: khi bấm vào đoạn text nào, âm thanh tự động tua đến `start_time` tương ứng.
- Khi audio đang phát, đoạn text tương ứng được highlight theo thời gian thực.
- Cho phép chỉnh sửa trực tiếp nội dung văn bản nếu AI nhận diện nhầm từ chuyên ngành; hỗ trợ phím tắt lưu thay đổi.

#### FR-05: Tóm tắt thông minh & Trích xuất công việc (Meeting Summarization)
- Tự động phân tích toàn văn transcript để sinh ra:
  1. **Tóm tắt điều hành (Executive Summary):** 3 - 5 câu tóm gọn mục đích và kết quả buổi họp.
  2. **Các quyết định chính (Key Decisions):** Danh sách gạch đầu dòng các kết luận đã thống nhất.
  3. **Danh sách công việc (Action Items):** Bảng gồm Công việc, Người phụ trách (Assignee), Hạn chót (Deadline nếu có).
- Gắn phiên bản của bản tóm tắt với phiên bản transcript để tự động cập nhật khi transcript có chỉnh sửa lớn.

#### FR-06: Trợ lý hỏi đáp cuộc họp (Grounded RAG Chatbot)
- Cho phép người dùng nhập câu hỏi vào hộp thoại chat riêng của cuộc họp.
- Hệ thống truy hồi các chunk ngữ cảnh liên quan nhất qua pgvector (cosine similarity).
- Câu trả lời của LLM bắt buộc đi kèm thẻ trích dẫn nguồn: `[Speaker Name, mm:ss]`.
- Khi người dùng click vào thẻ trích dẫn, hệ thống tự động nhảy Audio Player đến mốc thời gian đó và cuộn màn hình đến đoạn transcript làm căn cứ.
- Nếu thông tin không có trong cuộc họp, AI phải từ chối rõ ràng ("Thông tin này không được đề cập trong cuộc họp"), tuyệt đối không bịa đặt (hallucination).

#### FR-07: Tìm kiếm và Xuất dữ liệu (Search & Export)
- Tìm kiếm từ khóa theo tiêu đề cuộc họp và nội dung transcript (Full-text search).
- Cho phép xuất dữ liệu ra các định dạng:
  - Text thuần (.txt)
  - Văn bản tài liệu (.docx) theo mẫu biên bản cuộc họp chuẩn
  - Dữ liệu cấu trúc (.json) phục vụ tích hợp hệ thống
  - Tệp phụ đề (.srt / .vtt) có timestamp

#### FR-08: Chia sẻ cuộc họp & Phân quyền qua Link (Shareable Link & Access Control)
- Cho phép Chủ cuộc họp (Owner) mở hộp thoại chia sẻ để tạo liên kết truy cập an toàn (UUID/cryptographic token).
- Tùy chọn quyền hạn gán cho liên kết:
  - `Viewer` (Chỉ xem): Cho phép nghe audio, xem transcript, đọc tóm tắt và thực hiện hỏi đáp RAG.
  - `Editor` (Chỉnh sửa): Toàn bộ quyền của Viewer cộng thêm quyền sửa đổi transcript, đổi tên người nói, yêu cầu sinh lại tóm tắt và xuất biên bản.
- Hỗ trợ đổi quyền hoặc thu hồi liên kết (Revoke link) ngay lập tức, vô hiệu hóa mọi truy cập tiếp theo qua link đó.
- Kiểm tra quyền truy cập ở cấp độ API middleware cho từng request tới tài nguyên cuộc họp.

### 4.3. Các trường hợp ngoại lệ (Edge Cases)

| Tình huống | Cách hệ thống xử lý |
|---|---|
| Mất kết nối mạng khi đang thu âm trực tiếp | Lưu trữ tạm thời các chunks âm thanh vào IndexedDB trên trình duyệt; tự động kết nối lại WebSocket và gửi bù dữ liệu khi mạng phục hồi. |
| Người dùng tải lên tệp hỏng hoặc không phải audio (đổi đuôi giả) | Backend kiểm tra MIME type và dùng FFmpeg probe kiểm tra giải mã; nếu lỗi lập tức trả về thông báo "Tệp âm thanh không hợp lệ hoặc bị hỏng" và dừng tác vụ. |
| Cuộc họp có nhiều đoạn im lặng kéo dài hoặc chỉ toàn tiếng ồn | Module VAD (Voice Activity Detection) tự động lọc bỏ các đoạn không có tiếng nói, giảm tải tài nguyên tính toán cho mô hình Whisper. |
| Nhiều người nói đè lên nhau (Overlapping speech) | Ghi nhận phân đoạn theo người nói có âm lượng/đặc trưng rõ hơn; gắn cờ cảnh báo (flag) để người dùng rà soát lại thủ công. |
| Câu hỏi RAG không tìm thấy thông tin tương đồng trong transcript | Trả lời: "Nội dung cuộc họp không đề cập đến vấn đề này. Vui lòng kiểm tra lại câu hỏi hoặc nghe lại bản ghi âm." Không tự ý suy diễn từ dữ liệu ngoài. |
| Truy cập cuộc họp bằng link đã bị thu hồi hoặc token không hợp lệ | Hệ thống lập tức từ chối với mã 403 Forbidden và hiển thị thông báo: "Liên kết chia sẻ không hợp lệ hoặc đã bị thu hồi bởi Chủ cuộc họp." |

### 4.4. Yêu cầu phi chức năng (Non-Functional Requirements)

- **Độ chính xác AI (AI Accuracy):**
  - Word Error Rate (WER) < 15% đối với âm thanh tiếng Việt chất lượng tốt, không lẫn tạp âm lớn.
  - Diarization Error Rate (DER) < 20% trên cuộc họp từ 2 đến 5 người tham gia.
  - Tỷ lệ trích dẫn RAG hợp lệ (Grounded Citation Accuracy) đạt trên 95%.
- **Hiệu năng & Thời gian phản hồi (Performance & Latency):**
  - Thời gian xử lý batch cho file audio 60 phút: dưới 8 phút (với hạ tầng có GPU tăng tốc).
  - Phản hồi câu hỏi RAG: Token đầu tiên xuất hiện dưới 2 giây qua Server-Sent Events (SSE).
  - Tải trang ban đầu (First Contentful Paint): dưới 1.5 giây.
- **Bảo mật & Quyền riêng tư (Security & Privacy):**
  - Toàn bộ dữ liệu âm thanh và transcript được phân lập theo từng phiên họp và kiểm soát chặt chẽ qua vai trò Owner và Share Token (Viewer/Editor).
  - Không ghi log chứa thông tin nội dung nhạy cảm hoặc khóa bí mật (API keys, secrets).
  - Hỗ trợ xóa hoàn toàn tệp âm thanh gốc và vector index khi người dùng yêu cầu xóa cuộc họp.
- **Khả năng mở rộng & Độ tin cậy (Scalability & Reliability):**
  - Tách biệt kiến trúc Backend API và AI Service để có thể scale độc lập phần xử lý AI.
  - Sử dụng hàng đợi Redis có cơ chế retry tối đa 3 lần cho các tác vụ phiên âm nền khi gặp lỗi tạm thời.

---

## 5. Thiết kế & Trải nghiệm (UI/UX)

### 5.1. Nguyên tắc thiết kế (Design Principles)
- **Clean & Minimalist:** Giao diện tối giản, tập trung vào nội dung văn bản và tiến trình cuộc họp, giảm thiểu thành phần gây xao nhãng.
- **Audio-Text Interactivity:** Sự gắn kết mật thiết giữa âm thanh và con chữ; mọi tương tác trên chữ đều có thể phản hồi về âm thanh và ngược lại.
- **Information Hierarchy:** Phân tách rõ ràng giữa 3 phân vùng chính: Transcript Studio (chiếm 55%), Smart Summary & Action Items (chiếm 25%), RAG Chat Assistant (chiếm 20%).

### 5.2. Các màn hình chính (Core Screens)
1. **Dashboard / Meeting List:** Danh sách các cuộc họp đã diễn ra, trạng thái xử lý (Ready, Processing, Failed), nút tạo cuộc họp mới và ô tìm kiếm nhanh.
2. **Audio Intake Modal:** Modal cho phép chọn giữa hai tab: "Ghi âm trực tiếp" (với visualizer âm thanh) hoặc "Tải lên tệp âm thanh" (kéo thả tệp kèm thanh tiến độ).
3. **Meeting Workspace (Màn hình làm việc chính):**
   - *Thanh trên cùng:* Tiêu đề cuộc họp, thời lượng, số người tham gia, nút Chia sẻ (Share) mở Modal phân quyền, nút Xuất dữ liệu (Export).
   - *Khung phát âm thanh (Audio Player Bar):* Cố định phía dưới hoặc trên, có thanh trượt timeline, nút tua 5s/10s, điều chỉnh tốc độ phát (0.75x, 1x, 1.25x, 1.5x).
   - *Cột trung tâm (Transcript Studio):* Dòng thời gian các lượt nói, nhãn speaker có màu phân biệt, nút đổi tên speaker, inline editor để sửa text (chỉ hiển thị khả năng edit với Owner và Editor; Viewer ở chế độ chỉ đọc).
   - *Cột bên phải (Tabbed Sidebar):* Chuyển đổi giữa 2 tab: "Tóm tắt & Công việc" và "Hỏi đáp AI".
4. **Share Modal:** Hộp thoại chia sẻ hiển thị link bí mật, dropdown chọn quyền (`Chỉ xem - Viewer` / `Chỉnh sửa - Editor`), nút Copy Link và nút Thu hồi link (Revoke).

### 5.3. Ghi chú hành vi trạng thái UI (UI States & Interactions)
- **Nút bấm (Buttons):**
  - *Default:* Màu nền primary thương hiệu, chữ rõ nét.
  - *Hover:* Đổi sắc độ nền sáng/tối hơn 8%, con trỏ chuyển dạng pointer.
  - *Loading:* Hiển thị spinner xoay nhẹ, disable tương tác nhấn chuột để tránh gửi request trùng lặp.
  - *Disabled:* Màu xám nhạt (opacity 40%), cursor not-allowed khi chưa thỏa mãn điều kiện nhập liệu.
- **Thẻ trích dẫn timestamp (Citation Badge):** Có hiệu ứng hover highlight, click vào sẽ scroll mượt mà (smooth scroll) đến dòng transcript tương ứng và phát đoạn audio đó.

---

## 6. Tiêu chí nghiệm thu (Acceptance Criteria - AC)

| Mã AC | Tính năng | Tiêu chí nghiệm thu cụ thể |
|---|---|---|
| **AC-01** | Tải lên tệp âm thanh | Hệ thống chỉ chấp nhận định dạng `.mp3`, `.wav`, `.m4a` dưới 200 MB. Nếu tệp không đúng định dạng, hiển thị thông báo lỗi rõ ràng trong vòng 1 giây và chặn upload. |
| **AC-02** | Xử lý nền & Trạng thái | Khi tệp được tải lên thành công, hệ thống chuyển sang trạng thái "Đang xử lý", hiển thị tiến độ % và cập nhật kết quả transcript ngay khi worker hoàn thành mà không cần người dùng tải lại trang. |
| **AC-03** | Đồng bộ Audio - Text | Khi người dùng click vào một từ hoặc đoạn hội thoại bất kỳ trong Transcript Studio, trình phát âm thanh phải nhảy chính xác đến thời điểm `start_time` của đoạn đó trong vòng dưới 200ms. |
| **AC-04** | Đổi tên người nói | Khi người dùng đổi tên "SPEAKER_00" thành "Nguyễn Văn A", toàn bộ các lượt nói của SPEAKER_00 trong toàn bộ cuộc họp phải được cập nhật tên mới tức thì trên giao diện và trong cơ sở dữ liệu. |
| **AC-05** | Tóm tắt & Action Items | Bản tóm tắt phải được tự động sinh sau khi phiên âm xong, gồm đầy đủ 3 phần: Tóm tắt điều hành, Quyết định và Danh sách công việc có phân định rõ Người phụ trách (nếu được nêu trong cuộc họp). |
| **AC-06** | Hỏi đáp RAG kèm trích dẫn | Mọi câu trả lời của Trợ lý AI đều phải chứa ít nhất một thẻ trích dẫn dạng `[Tên, mm:ss]`. Khi nhấn vào thẻ trích dẫn, audio phải phát đúng thời điểm đó. Nếu nội dung không có trong cuộc họp, AI phải từ chối rõ ràng. |
| **AC-07** | Xuất biên bản | Người dùng có thể tải về file `.docx` và `.txt` chứa đầy đủ tiêu đề cuộc họp, ngày giờ, danh sách người tham gia, tóm tắt, action items và toàn văn transcript có mốc thời gian. |
| **AC-08** | Chia sẻ cuộc họp qua Link | Chủ cuộc họp có thể tạo link chia sẻ với quyền View hoặc Edit trong 1 thao tác. Người dùng mở link View không hiển thị nút sửa/xóa; người dùng mở link Edit có thể chỉnh sửa biên bản. Khi Owner bấm Thu hồi link, truy cập tiếp theo bị chặn với mã 403 Forbidden. |

---

## 7. Chỉ số đo lường thành công (Metrics & KPIs)

### 7.1. Chỉ số cốt lõi (North Star Metric)
- **Thời gian hoàn tất biên bản cuộc họp (Time-to-Meeting-Minutes):** Giảm từ trung bình 45 phút xuống dưới **10 phút** cho một cuộc họp tiêu chuẩn kéo dài 60 phút (bao gồm cả thời gian AI xử lý và người dùng rà soát).

### 7.2. Các chỉ số định lượng kỹ thuật & AI (Technical KPIs)
- **Word Error Rate (WER):** Đạt mức $\le 15\%$ trên tập dữ liệu cuộc họp tiếng Việt đàm thoại tiêu chuẩn.
- **Diarization Error Rate (DER):** Đạt mức $\le 20\%$ đối với các cuộc họp từ 2 đến 5 người tham gia.
- **Grounded Citation Accuracy:** Đạt $\ge 95\%$ các câu trả lời của RAG chỉ ra đúng đoạn transcript chứa thông tin làm căn cứ.
- **AI Processing Ratio (RTF - Real Time Factor):** Đạt RTF $\le 0.15$ (tức 60 phút âm thanh xử lý xong trong vòng $\le 9$ phút trên server GPU).

### 7.3. Các chỉ số trải nghiệm & Hiệu quả sản phẩm (Product KPIs)
- **Tỷ lệ chỉnh sửa transcript (Edit Rate):** Số lượng câu thoại người dùng phải sửa lại thủ công chiếm dưới **10%** tổng số câu thoại của cuộc họp.
- **Tỷ lệ sử dụng tính năng tóm tắt & hỏi đáp:** Hơn **80%** các phiên cuộc họp được người dùng yêu cầu sinh bản tóm tắt và thực hiện ít nhất 1 câu hỏi tra cứu qua chatbot.

---

## 8. Phụ lục & Câu hỏi mở (Open Questions / TBD)

### 8.1. Danh sách vấn đề cần chốt (TBD)
1. **[TBD-01] Giải pháp phân đoạn người nói trong thời gian thực (Streaming Diarization):**
   - *Hiện trạng:* Mô hình Pyannote hiện tại hoạt động tối ưu nhất ở chế độ batch (sau khi đã có đủ tệp âm thanh).
   - *Câu hỏi mở:* Có nên tách việc hiển thị real-time thành transcript tạm thời chưa có tên speaker, sau đó khi kết thúc cuộc họp mới chạy pass thứ hai hoàn thiện diarization hay áp dụng chunk-based diarization liên tục?
2. **[TBD-02] Hạ tầng GPU phục vụ đánh giá đồ án:**
   - *Hiện trạng:* Chạy mô hình Whisper Large/Medium và Pyannote đòi hỏi VRAM tối thiểu 8GB - 12GB để đạt tốc độ xử lý khả thi.
   - *Câu hỏi mở:* Sẽ triển khai demo trên môi trường máy trạm cục bộ (Local GPU RTX), sử dụng Cloud GPU (Google Colab / RunPod), hay tích hợp API dịch vụ bên ngoài làm phương án dự phòng khi hội đồng chấm thi kiểm tra?
3. **[TBD-03] Chiến lược chunking cho hội thoại dài trong RAG:**
   - *Hiện trạng:* Các lượt nói trong cuộc họp có độ dài ngắn không đều nhau (có câu chỉ 1-2 từ, có đoạn phát biểu kéo dài vài phút).
   - *Câu hỏi mở:* Nên chunk theo từng lượt nói (turn-based chunking) kèm ngữ cảnh trượt (sliding window 3 segments) hay chunk theo độ dài token cố định?

### 8.2. Tài liệu tham chiếu liên quan
- **SRS:** [docs/01-requirements/srs.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/01-requirements/srs.md)
- **Use Cases:** [docs/01-requirements/use-cases.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/01-requirements/use-cases.md)
- **Ma trận truy vết:** [docs/01-requirements/traceability-matrix.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/01-requirements/traceability-matrix.md)
- **Đề xuất đề tài:** [de-xuat-de-tai-tro-ly-cuoc-hop-ai.md](file:///Users/plxg/workspace/meeting-voice-assistant/de-xuat-de-tai-tro-ly-cuoc-hop-ai.md)
