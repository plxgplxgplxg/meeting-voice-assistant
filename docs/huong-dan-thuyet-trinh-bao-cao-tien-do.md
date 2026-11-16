# CẨM NANG HƯỚNG DẪN THUYẾT TRÌNH BÁO CÁO TIẾN ĐỘ ĐỒ ÁN (END-TO-END)
## HỆ THỐNG PHIÊN ÂM, TÓM TẮT VÀ HỎI ĐÁP NỘI DUNG CUỘC HỌP THÔNG MINH (MEETING VOICE ASSISTANT)

- **Người thực hiện:** Nguyễn Phương Linh — MSSV: 20224871 — Lớp: IT1-02
- **Giảng viên hướng dẫn:** TS. Cao Tuấn Dũng
- **Tài liệu slide đi kèm:** [docs/bao-cao-tien-do-20-slides.md](file:///Users/plxg/workspace/meeting-voice-assistant/docs/bao-cao-tien-do-20-slides.md)
- **Thời lượng ước tính:** 15 – 20 phút (trung bình 1 – 1.5 phút/slide)

---

## 1. NGUYÊN TẮC THUYẾT TRÌNH VỚI GIẢNG VIÊN HƯỚNG DẪN

1. **Trực diện, đi thẳng vào bản chất kỹ thuật:** Không nói dài dòng về cảm xúc hay mở đầu vòng vo. Tập trung vào: *Bài toán là gì? Đã giải quyết bằng giải pháp/kiến trúc nào? Tại sao lại chọn công nghệ đó thay vì công nghệ khác? Dữ liệu thực nghiệm chứng minh ra sao?*
2. **Quy tắc dẫn dắt biểu đồ (Diagram Walkthrough):**
   - **Bước 1 (Định hướng):** Nói rõ biểu đồ này thuộc chuẩn nào, giải quyết bài toán gì (ví dụ: *"Đây là sơ đồ kiến trúc mức Container C4 Level 2..."* hoặc *"Đây là sơ đồ tuần tự mức phân tích Analysis Level..."*).
   - **Bước 2 (Đi theo luồng dữ liệu):** Luôn dẫn dắt theo chiều tương tác nghiệp vụ: từ Trái sang Phải, từ Trên xuống Dưới, hoặc từ Actor khởi phát qua các tầng xử lý.
   - **Bước 3 (Nhấn mạnh điểm kỹ thuật cốt lõi - Key Insight):** Nhấn mạnh lý do thiết kế (Trade-off, tối ưu phần cứng, đảm bảo ACID).
3. **Phong thái học thuật:** Dùng thuật ngữ kỹ thuật chuẩn ngành (Two-Pass, ASR, Diarization, Word Alignment, Hybrid Search, Reciprocal Rank Fusion, HNSW, ACID Transaction).

---

## 2. KỊCH BẢN CHI TIẾT THEO TỪNG SLIDE & HƯỚNG DẪN GIẢI THÍCH BIỂU ĐỒ

---

### SLIDE 01: GIỚI THIỆU ĐỀ TÀI
- **Mục tiêu slide:** Khẳng định tên đề tài, tính pháp lý, cấu trúc báo cáo và phạm vi đã hoàn thành.
- **Lời thoại gợi ý:**
  > *"Kính thưa Thầy, em xin phép báo cáo tiến độ đồ án tốt nghiệp với đề tài: 'Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp thông minh'. Trong giai đoạn 1 vừa qua, em đã hoàn thành toàn diện 3 nội dung nền tảng gồm: Đặc tả yêu cầu phần mềm (Folder 01), Khảo sát thực nghiệm công nghệ AI (Folder 02) và Thiết kế kiến trúc hệ thống cùng cơ sở dữ liệu (Folder 03). Hôm nay em xin báo cáo tổng thể các kết quả kỹ thuật cốt lõi đã đạt được."*

---

### SLIDE 02: KHÁI QUÁT PRD: BÀI TOÁN & PHẠM VI DỰ ÁN
- **Mục tiêu slide:** Làm rõ bài toán nghiệp vụ thực tiễn, đầu vào và cấu trúc đầu ra.
- **Lời thoại gợi ý:**
  > *"Về bài toán thực tế: Hiện nay việc lập biên bản cuộc họp thủ công tốn từ 45 đến 60 phút cho một cuộc họp kéo dài 1 giờ, đồng thời rất dễ bỏ sót các quyết định quan trọng và danh sách công việc được giao. Khi cần tra cứu lại, thành viên phải nghe lại toàn bộ file ghi âm rất mất thời gian.*  
  > *Hệ thống của em giải quyết trọn vẹn bài toán này với: Đầu vào là âm thanh thu trực tiếp qua trình duyệt hoặc tệp ghi âm tải lên, có đặc thù tiếng Việt hội thoại đa người nói. Đầu ra là một hệ thống dữ liệu có cấu trúc hoàn chỉnh gồm: Toàn văn bóc băng có gắn nhãn người nói và mốc thời gian từng từ; Biên bản tóm tắt tự động trích xuất quyết định và Action Items; cùng một Chatbot RAG cho phép hỏi đáp nội dung cuộc họp kèm trích dẫn mốc thời gian kiểm chứng."*

---

### SLIDE 03: MỤC TIÊU HỆ THỐNG & CHỈ SỐ KỸ THUẬT
- **Mục tiêu slide:** Đưa ra các chỉ số đo lường định lượng (chỉ số North Star và SLA kỹ thuật).
- **Lời thoại gợi ý:**
  > *"Để hệ thống có giá trị thực tiễn cao, em xác lập 4 chỉ số chất lượng cốt lõi:*  
  > *Thứ nhất, chỉ số North Star: Giảm thời gian hoàn thành biên bản cuộc họp 60 phút từ 45 phút xuống dưới 10 phút.*  
  > *Thứ hai, độ trễ hiển thị trực tiếp khi đang họp phải dưới 1.5 giây để người dùng thấy chữ chạy mượt mà.*  
  > *Thứ ba, tốc độ xử lý bóc băng chính thức (Batch RTF) trên GPU đạt dưới 0.15, thực tế với mô hình em chọn đạt khoảng 0.03x, tức 10 phút ghi âm chỉ mất khoảng 20 giây xử lý.*  
  > *Thứ tư, 100% câu trả lời từ RAG phải có trích dẫn mốc giây để người dùng bấm nghe lại âm thanh gốc, và dữ liệu phải đảm bảo tính toàn vẹn giao dịch ACID tuyệt đối."*

---

### SLIDE 04: MÔ HÌNH USE CASE & PHÂN QUYỀN ACTOR
- **Mục tiêu slide:** Giải thích ranh giới chức năng và phân quyền hệ thống.

#### Hướng dẫn thuyết trình Biểu đồ Use Case (PlantUML Use Case):
- **Cách chỉ vào hình:**
  1. *Chỉ vào các Actor bên trái:* Gồm 3 nhóm người dùng có phân quyền giảm dần: **Chủ cuộc họp (Owner)** nắm toàn quyền tạo, sửa, xóa và chia sẻ; **Người sửa (Editor)** có quyền chỉnh sửa nội dung văn bản và đổi tên người nói; **Người xem (Viewer)** chỉ có quyền đọc biên bản, nghe audio và tra cứu Chatbot.
  2. *Chỉ vào các Actor bên phải:* Hai hệ thống phụ trợ là **AIService** (chịu trách nhiệm xử lý âm thanh thời gian thực và ngoại tuyến) và **LLMService** (chịu trách nhiệm tóm tắt và suy luận câu trả lời RAG).
  3. *Chỉ vào khối chức năng ở giữa:* Có 7 Use Cases nghiệp vụ (UC-01 đến UC-07). Tất cả các tương tác đều được bao hàm bởi ca sử dụng `Xác thực & phân quyền người dùng` (`<<include>>`).
- **Lời thoại gợi ý:**
  > *"Thưa Thầy, đây là sơ đồ Use Case tổng thể của hệ thống. Về mặt phân quyền, em thiết kế dựa trên mô hình kiểm soát truy cập theo tài nguyên (Resource-based Access Control via Share Link). Chủ cuộc họp có toàn quyền quản lý, trong khi người nhận link chia sẻ chỉ có quyền chỉnh sửa (Editor) hoặc chỉ xem (Viewer). Phía bên phải là hai tác nhân hệ thống chịu trách nhiệm cho các tác vụ tính toán nặng: phân hệ AI xử lý âm thanh và dịch vụ LLM sinh văn bản.*  
  > *Em xin lưu ý là các bước tính toán vector hay thuật toán nội bộ không vẽ thành bong bóng Use Case riêng vì đây là nghiệp vụ ngầm của hệ thống, giúp sơ đồ tập trung chuẩn xác vào tương tác của người dùng."*

---

### SLIDE 05: DANH MỤC CHỨC NĂNG NGHIỆP VỤ (7 USE CASES)
- **Mục tiêu slide:** Lướt nhanh qua 7 Use Cases để khẳng định tính đầy đủ của bộ tài liệu đặc tả.
- **Lời thoại gợi ý:**
  > *"Em đã hoàn thành đặc tả chi tiết cho 7 Use Cases cốt lõi: UC-01 thu âm trực tiếp; UC-02 xử lý file ghi sẵn; UC-03 chỉnh sửa biên bản trong Transcript Studio; UC-04 tự động trích xuất tóm tắt và việc cần làm; UC-05 hỏi đáp RAG kèm trích dẫn; UC-06 xuất biên bản ra DOCX/SRT và UC-07 chia sẻ cuộc họp an toàn qua liên kết. Các use case này tạo thành một chu trình khép kín từ lúc bắt đầu họp đến khi bàn giao biên bản."*

---

### SLIDE 06: KIẾN TRÚC HỆ THỐNG TỔNG THỂ
- **Mục tiêu slide:** Trình bày kiến trúc phần mềm, nguyên lý phân tầng và giao thức kết nối.

#### Hướng dẫn thuyết trình Biểu đồ Kiến trúc (PlantUML Component Phân Tầng):
- **Cách chỉ vào hình:** Đi từ Trên xuống Dưới qua 5 phân tầng kiến trúc:
  1. *Client:* Next.js Web App giao tiếp qua HTTPS và `AudioWorklet` thu âm PCM 16kHz truyền qua WebSocket (WSS).
  2. *Cổng Gateway & Web Layer:* `Nginx` làm Reverse Proxy tiếp nhận toàn bộ lưu lượng, định tuyến REST API và sự kiện SSE về `Backend API (FastAPI)`, định tuyến luồng micro trực tiếp về `Live ASR`.
  3. *GPU Layer (ai-service):* Tách riêng hoàn toàn để chạy trên máy chủ GPU CUDA, gồm `Live ASR` phục vụ thời gian thực và `Celery Worker` phục vụ bóc băng theo lô.
  4. *Data Layer:* Cơ sở dữ liệu duy nhất **PostgreSQL 17 + extension `pgvector`** (lưu cả dữ liệu quan hệ lẫn vector 384 chiều), `Redis 7` làm message broker và `Audio Storage` lưu file âm thanh.
  5. *Cloud LLM:* Ủy thác toàn bộ tác vụ tóm tắt và RAG cho `OpenAI GPT-4o-mini` qua kết nối HTTPS bảo mật.
- **Điểm nhấn kỹ thuật cần chốt với Thầy:**
  > *"Kiến trúc này tuân thủ nguyên tắc phân tách độc lập (Decoupling): Tầng Web nghiệp vụ chạy rất nhẹ và có thể mở rộng độc lập; tầng tính toán AI nặng được đóng gói chạy trực tiếp trên GPU CUDA; và đặc biệt hệ thống sử dụng duy nhất một CSDL PostgreSQL tích hợp pgvector, loại bỏ hoàn toàn sự cố phân mảnh dữ liệu giữa DB quan hệ và DB vector rời."*

---

### SLIDE 07: KIẾN TRÚC XỬ LÝ HAI LƯỢT (TWO-PASS ARCHITECTURE)
- **Mục tiêu slide:** Giải thích bài toán đánh đổi giữa độ trễ và độ chính xác, cùng giải pháp Two-Pass.

#### Hướng dẫn thuyết trình Biểu đồ Two-Pass:
- **Cách chỉ vào hình:** So sánh 2 nhánh xử lý:
  1. *Nhánh trên (Pass 1 - Trực tiếp):* Đi từ Microphone $\to$ Silero VAD lọc khung 32ms $\to$ Zipformer-vi INT8 giải mã nhanh $\to$ Đẩy sự kiện SSE chữ chạy Karaoke về màn hình. Độ trễ cực thấp $\le 1.5$s. Song song đó âm thanh được ghi tạm vào ổ đĩa.
  2. *Nhánh dưới (Pass 2 - Ngoại tuyến):* Khi kết thúc cuộc họp, tệp âm thanh hoàn chỉnh được đưa vào pipeline xử lý chuẩn: FFmpeg $\to$ PhoWhisper-medium bóc băng chính xác $\to$ Pyannote tách người nói $\to$ Căn chỉnh mốc từ $\to$ Lưu vào CSDL.
  3. *Mũi tên nối:* Bản Pass 2 ghi đè hoàn toàn bản nháp Pass 1 và là nguồn dữ liệu duy nhất cho RAG.
- **Lời thoại gợi ý:**
  > *"Thưa Thầy, trong các hệ thống voice meeting, luôn có mâu thuẫn giữa nhu cầu 'muốn thấy chữ ngay khi đang nói' và 'muốn văn bản chuẩn xác có phân tách người nói'. Để giải quyết triệt để, em thiết kế kiến trúc hai lượt:*  
  > *Pass 1 chỉ đóng vai trò hiển thị bản nháp thời gian thực để người dự họp theo dõi mạch phát biểu. Còn Pass 2 chạy nền sau khi họp xong hoặc khi tải file lên, sử dụng mô hình mạnh hơn để tạo ra bản ghi lưu trữ chính thức có nhãn người nói và mốc thời gian chi tiết."*

---

### SLIDE 08: LUẬN GIẢI LỰA CHỌN MÔ HÌNH AI (TẠI SAO CHỌN MODEL ĐÓ?)
- **Mục tiêu slide:** Chứng minh tính khoa học và căn cứ thực nghiệm trong việc chọn từng mô hình.
- **Lời thoại gợi ý (Dựa vào bảng số liệu thực nghiệm):**
  > *"Khi lựa chọn mô hình AI, em đã khảo sát thực nghiệm kỹ lưỡng dựa trên tập dữ liệu tiếng Việt chuẩn VIVOS và tập đối thoại khó VLSP Task-2:*  
  > *1. **Tại sao chọn PhoWhisper-medium cho Pass 2?**  
  > Trên tập hội thoại khó VLSP, khi nâng từ bản `small` lên `medium`, tỷ lệ lỗi từ (WER) giảm rất mạnh tới **6.11%** (từ 32.96% xuống còn 26.85%). Nhưng nếu nâng tiếp từ `medium` lên `large`, WER chỉ cải thiện thêm được **0.17%** trong khi số tham số và dung lượng tăng gấp đôi. Do đó, bản `medium` chính là điểm cân bằng tối ưu (Sweet Spot). Đồng thời, khi chạy qua CTranslate2 FP16 trên GPU CUDA, mô hình chỉ tốn khoảng 2GB VRAM và đạt tốc độ RTF 0.03x, tức xử lý 10 phút audio chỉ mất khoảng 20 giây.*  
  > *2. **Tại sao Pass 1 chọn Zipformer-vi thay vì Whisper?**  
  > Zipformer-vi chạy kiến trúc RNN-T rất nhẹ (~75MB), trễ $\le 1.5$s và quan trọng nhất là không bao giờ bị hiện tượng lặp ảo giác (hallucination loop) khi gặp khoảng lặng hoặc nhạc nền như Whisper.*  
  > *3. **Pyannote Diarization:** Chạy trên GPU, em thiết lập ràng buộc cứng `min_speakers = 2` để ngăn lỗi gom toàn bộ cuộc họp về một người nói, và có xây dựng sẵn thuật toán Standalone K-means dự phòng khi mất token.*  
  > *4. **multilingual-e5-small:** Sinh vector 384 chiều khớp chính xác chỉ mục `vector(384)` của PostgreSQL, tốc độ tính toán cực nhanh dưới 5ms một đoạn.*  
  > *5. **Ủy thác LLM cho Cloud API:** Giúp giải phóng hoàn toàn 10–18 GB VRAM trên máy chủ cho các tác vụ âm thanh, đồng thời tận dụng tính năng Structured Outputs của GPT-4o-mini để ép cấu trúc JSON chuẩn 100%."*

---

### SLIDE 09: SƠ ĐỒ TUẦN TỰ PHÂN TÍCH: GHI ÂM TRỰC TIẾP (UC-01)
- **Mục tiêu slide:** Trình bày luồng tương tác thời gian thực theo chuẩn UML Analysis Level (mô hình BCE).

#### Hướng dẫn thuyết trình Biểu đồ Tuần tự UC-01:
- **Cách chỉ vào hình:**
  1. *Chỉ vào các đối tượng tham gia:* Người dùng (`actor`), Giao diện AudioWorklet (`boundary`), Live Gateway WebSocket (`control`), Kho lưu trữ tạm (`entity`) và Cổng SSE (`control`).
  2. *Giai đoạn khởi tạo (Bước 1-3):* Trình duyệt mở kết nối WebSocket `/ws/live`, server phản hồi xác nhận 101 Switching Protocols.
  3. *Vòng lặp truyền & xử lý âm thanh (Bước 4-11):*
     - Mỗi 100ms gửi một khối audio PCM 16kHz lên Live Gateway.
     - Live Gateway vừa ghi nối tiếp vào Storage tạm, vừa thực thi hàm nội bộ `processLiveAudio(chunk)` (lọc Silero VAD 32ms và giải mã nhanh bộ đệm qua Zipformer-vi INT8).
     - Kết quả giải mã tạm thời được đẩy qua SSE (`pushDraftPartial`) để giao diện hiển thị chữ chạy Karaoke.
     - Khi phát hiện khoảng lặng $\ge 500$ms hoặc câu đạt trần 6.5s, Live Gateway gọi hàm `finalizeDraftSentence()` để chuẩn hóa đầu câu, ánh xạ từ điển viết tắt (hotwords) và phát sự kiện `pushDraftFinal` chốt câu trên timeline.
  4. *Kết thúc phiên (Bước 12-15):* Đóng file âm thanh hoàn chỉnh để sẵn sàng đưa vào Pass 2.
- **Lời thoại gợi ý:**
  > *"Thưa Thầy, đây là sơ đồ tuần tự mức phân tích cho tính năng ghi âm trực tiếp. Luồng xử lý thể hiện rõ cơ chế hai chiều bất đồng bộ: âm thanh nhị phân gửi lên qua WebSocket, Live Gateway thực thi hàm `processLiveAudio` để lọc VAD và giải mã nhanh bằng Zipformer-vi, sau đó đẩy ngược văn bản nháp về giao diện qua Server-Sent Events (SSE). Khi người nói dừng câu, hàm `finalizeDraftSentence` sẽ chốt câu hoàn chỉnh. Việc phân tách này giúp giao diện không bị giật lag và âm thanh luôn được ghi nhận an toàn."*

---

### SLIDE 10: SƠ ĐỒ TUẦN TỰ PHÂN TÍCH: XỬ LÝ TỆP ÂM THANH (UC-02)
- **Mục tiêu slide:** Trình bày luồng xử lý tệp ghi sẵn mức phân tích toàn hệ thống.

#### Hướng dẫn thuyết trình Biểu đồ Tuần tự UC-02:
- **Cách chỉ vào hình:**
  1. *Khởi tạo tác vụ (Bước 1-7):* Người dùng tải file $\to$ Backend lưu file vào Storage, tạo bản ghi `Meeting` ở trạng thái QUEUED, đẩy task vào Celery Queue và phản hồi ngay `202 Accepted` kèm ID. Giao diện mở kết nối SSE để chờ tiến độ.
  2. *Thực thi bất đồng bộ (Bước 8-11):* AI Worker nhận task từ hàng đợi, đọc file âm thanh và kích hoạt pipeline xử lý âm thanh. Quá trình xử lý liên tục phát tiến độ từ 15% đến 100% qua SSE về màn hình.
  3. *Lưu trữ và Tóm tắt (Bước 12-17):* Worker ghi các phân đoạn lời nói và vector ngữ nghĩa vào PostgreSQL, gửi nội dung sang Cloud LLM lấy tóm tắt và việc cần làm, cập nhật trạng thái cuộc họp thành COMPLETED.
  4. *Hiển thị kết quả (Bước 18-24):* Backend phát tín hiệu `transcript.ready`, giao diện tự động kéo dữ liệu về và hiển thị đầy đủ trên Transcript Studio.
- **Lời thoại gợi ý:**
  > *"Ở ca sử dụng UC-02, hệ thống áp dụng hoàn toàn mô hình xử lý bất đồng bộ (Asynchronous Task Processing). Người dùng không phải chờ đợi trên màn hình mà nhận phản hồi 202 ngay lập tức, sau đó theo dõi thanh tiến trình chạy theo thời gian thực qua SSE. Toàn bộ logic bóc băng phức tạp được AI Worker thực thi ngầm trên GPU."*

---

### SLIDE 11: LUỒNG CHI TIẾT: PIPELINE XỬ LÝ ÂM THANH AI (PASS 2)
- **Mục tiêu slide:** Làm rõ quy trình biến đổi tín hiệu âm thanh thành dữ liệu có cấu trúc bên trong AI Worker.

#### Hướng dẫn thuyết trình Biểu đồ Pipeline Pass 2:
- **Cách chỉ vào hình:** Đi theo luồng tuần tự từ trên xuống:
  1. *Chuẩn hóa âm thanh (Bước 1):* FFmpeg đưa về WAV Mono 16 kHz PCM và chuẩn hóa năng lượng `loudnorm`.
  2. *Rẽ nhánh song song (Fork - Bước 2, 3, 4):* 
     - Nhánh trái: Silero VAD Gatekeeper lọc khung tiếng nói $\to$ PhoWhisper-medium bóc băng ra chữ và ước lượng mốc thời gian từng từ (`word_timestamps`).
     - Nhánh phải: Pyannote Diarization chạy song song trên GPU để phân tách các lượt phát biểu (`speaker turns`).
  3. *Hội tụ và Căn chỉnh (Join - Bước 5, 6, 7):* Thuật toán **Turn-taking Word Alignment** lấy giao cắt thời gian giữa từ và turn người nói để gán đúng người phát biểu; bộ lọc **Sanitizer** cắt bỏ các ảo giác lặp từ của Whisper $\to$ Ghi vào bảng `transcript_segments`.
  4. *Tạo chỉ mục và Tóm tắt (Bước 8-13):* Thuật toán **Speaker-Turn Chunking** gom câu $\to$ `e5-small` tính vector 384 chiều $\to$ Lưu `transcript_embeddings` $\to$ Gửi Cloud LLM tạo tóm tắt biên bản.
- **Lời thoại gợi ý:**
  > *"Đây là luồng xử lý chi tiết bên trong GPU Worker: Điểm mấu chốt của thiết kế này là cơ chế xử lý song song giữa bóc băng ASR và phân tách người nói Diarization. Sau đó, thuật toán Word Alignment sẽ dùng mốc thời gian chi tiết của từng từ để ghép nối chính xác với lượt nói của từng người, giải quyết trọn vẹn hiện tượng ngắt lời và nói chen ngang."*

---

### SLIDE 12: LUỒNG CHI TIẾT: NGHIỆP VỤ RAG & TRÍCH DẪN MỐC GIÂY
- **Mục tiêu slide:** Giải thích cơ chế tìm kiếm thông minh và cách thức tạo trích dẫn kiểm chứng.

#### Hướng dẫn thuyết trình Biểu đồ RAG:
- **Cách chỉ vào hình:**
  1. *Xử lý câu hỏi (Bước 1-2):* `Query Condensation` viết lại câu hỏi dựa trên lịch sử chat để tạo câu hỏi độc lập ngữ cảnh; `e5-small` sinh vector câu hỏi với tiền tố `query: `.
  2. *Truy hồi lai song song (Bước 3a, 3b, 4):* Thực hiện song song trong PostgreSQL: Tìm kiếm vector ngữ nghĩa (Dense Cosine HNSW) và Tìm kiếm từ khóa chính xác (Lexical BM25). Sau đó dùng công thức **Reciprocal Rank Fusion (RRF với $k=60$)** để hợp nhất thứ hạng, lấy ra Top 5–7 đoạn phù hợp nhất.
  3. *Mở rộng cửa sổ (Window Retrieval $\pm 1$ - Bước 6):* Tự động lấy thêm đoạn phát biểu liền trước và liền sau từ CSDL để khôi phục đại từ nhân xưng ("anh ấy", "cái này") bị tỉnh lược trong hội thoại.
  4. *Sinh câu trả lời và Trích dẫn (Bước 7-10):* Đóng gói ngữ cảnh gửi LLM; LLM stream từng từ kèm mã thẻ `[S0412]`. Backend đối chiếu CSDL lấy chính xác mốc giây và đẩy về giao diện; người dùng nhấp vào trích dẫn là trình phát audio tự tua đến đúng đoạn đó.
- **Lời thoại gợi ý:**
  > *"RAG trên hội thoại cuộc họp khó hơn nhiều so với RAG tài liệu thông thường vì câu nói ngắn và nhiều đại từ thay thế. Em giải quyết bằng 3 kỹ thuật: Truy hồi lai RRF $k=60$ để không bỏ sót từ chuyên môn; Mở rộng cửa sổ $\pm 1$ chunk để giữ trọn ngữ cảnh đối thoại; và cơ chế Citation Binding giúp người dùng kiểm chứng câu trả lời bằng âm thanh thực tế chỉ với một cú nhấp chuột."*

---

### SLIDE 13: THIẾT KẾ CƠ SỞ DỮ LIỆU (ERD) & CƠ CHẾ AN TOÀN ACID
- **Mục tiêu slide:** Trình bày cấu trúc bảng dữ liệu và chứng minh giải pháp bảo toàn tính toàn vẹn dữ liệu.

#### Hướng dẫn thuyết trình Sơ đồ ERD & Cơ chế ACID:
- **Cách chỉ vào hình:**
  1. *Sơ đồ ERD:* Chỉ rõ 6 bảng cốt lõi: `MEETINGS` (thông tin cuộc họp) $\to$ `TRANSCRIPT_SEGMENTS` (các câu phát biểu, quan hệ 1:N) $\to$ `TRANSCRIPT_EMBEDDINGS` (chứa cột `embedding vector(384)` có chỉ mục HNSW) $\to$ `SUMMARIES` và `ACTION_ITEMS`. Bảng `TRANSCRIPT_SEGMENT_VERSIONS` dùng để lưu vết lịch sử chỉnh sửa.
  2. *Cơ chế Compute-then-Commit:* Giải thích cách thức xử lý khi người dùng sửa câu chữ:
     - *Pha 1 (Compute):* Tính trước vector embedding mới ở bên ngoài transaction.
     - *Pha 2 (Commit):* Mở duy nhất một `PostgreSQL Transaction`: ghi bản cũ vào bảng version, cập nhật text mới, đánh dấu vector cũ `is_active = false`, chèn vector mới, đánh dấu summary `is_stale = true` và COMMIT.
- **Lời thoại gợi ý:**
  > *"Thưa Thầy, để tránh hiện tượng 'văn bản hiển thị một đằng nhưng Chatbot tìm kiếm theo vector một nẻo' khi người dùng sửa biên bản, em áp dụng mẫu thiết kế Compute-then-Commit trong một PostgreSQL Transaction duy nhất. Nếu quá trình tính vector hoặc cập nhật xảy ra lỗi, toàn bộ transaction sẽ rollback, đảm bảo dữ liệu văn bản và vector ngữ nghĩa luôn đồng bộ tuyệt đối."*

---

### SLIDE 14: KIẾN TRÚC TRIỂN KHAI HẠ TẦNG & PHÂN BỔ VRAM
- **Mục tiêu slide:** Chứng minh tính khả thi về mặt tài nguyên phần cứng và an toàn an ninh thông tin.
- **Lời thoại gợi ý (Dựa vào bảng VRAM):**
  > *"Về mặt tài nguyên phần cứng: Khi vận hành đồng thời toàn bộ pipeline AI trên máy chủ GPU 24GB VRAM (như RTX 3090 hay RTX 4090), tổng mức tiêu thụ VRAM đỉnh điểm chỉ khoảng **5.5 đến 6.8 GB**, chiếm chưa tới **30%** tổng dung lượng card. Hệ thống còn dư hơn 70% VRAM dự phòng, hoàn toàn đủ khả năng mở rộng chạy song song 2 đến 3 luồng xử lý cùng lúc. Cấu hình này cũng tương thích an toàn trên môi trường kiểm thử Kaggle GPU T4 15GB.*  
  > *Về an toàn thông tin, hệ thống thiết lập 4 ranh giới tin cậy (STRIDE) và đặc biệt áp dụng thẻ phân tách XML `<excerpts>` khi gửi dữ liệu sang LLM để triệt tiêu hoàn toàn rủi ro tấn công Prompt Injection từ nội dung phát biểu trong cuộc họp."*

---

### SLIDE 15: TỔNG KẾT GIAI ĐOẠN 1 & KẾ HOẠCH TIẾP THEO
- **Mục tiêu slide:** Khẳng định kết quả nghiệm thu giai đoạn 1 và cam kết lộ trình thực hiện giai đoạn 2.
- **Lời thoại gợi ý:**
  > *"Tóm lại, trong giai đoạn 1 vừa qua, em đã hoàn thành toàn diện việc nghiên cứu, đặc tả và thiết kế kiến trúc cho hệ thống Meeting Voice Assistant. Các thiết kế đều có cơ sở khoa học, số liệu thực nghiệm và tuân thủ các chuẩn kỹ thuật phần mềm quốc tế.*  
  > *Kế hoạch trong giai đoạn tiếp theo:*  
  > *Pha 04: Hoàn thiện thiết kế chi tiết DDL cơ sở dữ liệu vật lý, hợp đồng API OpenAPI 3.0 và wireframe giao diện.*  
  > *Pha 05: Tập trung lập trình cài đặt toàn bộ hệ thống bằng Docker Compose, hoàn thiện Worker GPU và đánh giá định lượng độ chính xác bằng các chỉ số WER, DER và RAG Triad.*  
  > *Em xin chân thành cảm ơn Thầy đã lắng nghe và rất mong nhận được những góp ý, chỉ dẫn của Thầy để đồ án đạt kết quả tốt nhất!"*

---

## 3. BẢNG DỰ ĐOÁN CÂU HỎI CỦA GIẢNG VIÊN VÀ CÁCH TRẢ LỜI NGẮN GỌN

| Câu hỏi của Thầy | Trọng tâm trả lời ngắn gọn & thuyết phục |
|---|---|
| **Tại sao không dùng luôn Whisper bản Large cho chính xác nhất?** | *"Dạ thưa Thầy, theo dữ liệu thực nghiệm của VinAI trên tập hội thoại khó VLSP-2, bản Large chỉ giảm thêm 0.17% WER so với bản Medium (26.68% so với 26.85%) nhưng kích thước mô hình tăng gấp đôi (từ 769M lên 1550M) và làm tăng đáng kể độ trễ suy luận. Do đó bản Medium là điểm cân bằng tối ưu giữa độ chính xác và tài nguyên."* |
| **Nếu mạng chập chờn hoặc hết Token Hugging Face thì phần tách người nói có chết không?** | *"Dạ hệ thống có thiết kế cơ chế chịu lỗi nhiều tầng (Graceful Fallback). Nếu không kết nối được Pyannote, hệ thống tự động kích hoạt Engine 2 là bộ phân cụm Standalone Acoustic K-means thuần PyTorch không cần token để tiếp tục phân tách, hoặc gán nhãn `SPEAKER_UNKNOWN` chứ tuyệt đối không làm dừng đột ngột hệ thống."* |
| **Tại sao không dùng DB vector chuyên dụng như Milvus hay Pinecone mà lại dùng pgvector?** | *"Dạ thưa Thầy, trong hệ thống này, khi người dùng sửa văn bản thì vector tương ứng bắt buộc phải cập nhật ngay. Nếu dùng 2 CSDL riêng biệt sẽ rất khó đảm bảo giao dịch ACID, dễ bị tình trạng 'văn bản đã đổi nhưng vector trong Milvus chưa cập nhật'. Sử dụng pgvector trong PostgreSQL cho phép thực thi toàn bộ việc sửa text và cập nhật vector trong một Transaction nguyên tử duy nhất."* |
| **Pass 1 dùng Zipformer-vi không có dấu câu thì người dùng đọc có khó chịu không?** | *"Dạ thưa Thầy, Pass 1 chỉ đóng vai trò bản nháp chạy tức thời theo giọng nói để người dự họp biết hệ thống đang bắt đúng tiếng nói. Khi người nói dứt câu, hệ thống tự động viết hoa chữ cái đầu và ánh xạ từ khóa. Ngay khi cuộc họp kết thúc, bản Pass 2 của PhoWhisper có đầy đủ dấu chấm phẩy chuẩn xác sẽ thay thế hoàn toàn."* |
