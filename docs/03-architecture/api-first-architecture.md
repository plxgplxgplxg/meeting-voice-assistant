# Kiến Trúc Tối Giản API-First Cho Meeting Voice Assistant

**Đề tài:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp  
**Tài liệu:** `docs/03-architecture/api-first-architecture.md`  
**Ngày lập:** 01/11/2026  

---

## 1. Bảng Phân Bổ Nhiệm Vụ: CPU vs Cloud API

Để tối ưu tốc độ triển khai, loại bỏ hoàn toàn yêu cầu thuê máy chủ GPU đắt đỏ và giữ chi phí ở mức thấp nhất, hệ thống phân chia ranh giới xử lý như sau:

| Thành phần | Nơi thực thi | Mô hình / Dịch vụ chọn | Chi phí ước tính | Lý do kỹ thuật |
|---|---|---|---|---|
| **VAD (Lọc tiếng nói)** | **CPU (Local)** | `Silero VAD v6` (ONNX) | **0 VNĐ** | Nhẹ (~10MB), chạy < 1ms/frame, không có API nào hợp lý cho gói 32ms. |
| **Pass 1 ASR (Draft live)** | **CPU (Local)** | `sherpa-onnx Zipformer-vi` | **0 VNĐ** | Nhẹ (~75MB), chạy RAM CPU, hiển thị tức thì không phụ thuộc mạng quốc tế. |
| **Pass 2 (ASR + Diarization)** | **Cloud API** | **Gladia API (Solaria-1)** | **~5.000 VNĐ / giờ họp** *(Có 50€ free)* | Đóng gói trọn gói ASR + Diarization + Word timestamps; rẻ nhất và chuẩn nhất. |
| **RAG Embedding** | **CPU (Local)** | `multilingual-e5-small` | **0 VNĐ** | 118M params, nhúng 300 câu chỉ mất ~1.5s trên CPU thường, giữ nguyên schema 384-dim. |
| *(Dự phòng Embedding)* | *Cloud API* | *OpenAI text-embedding-3-small* | *~10 VNĐ / cuộc họp* | Phương án nếu muốn chuyển hẳn sang API hoàn toàn. |
| **LLM (Tóm tắt & Hỏi đáp)** | **Cloud API** | **Gemini 2.0 Flash** *(hoặc GPT-4o-mini)* | **~50 – 100 VNĐ / cuộc họp** | Rẻ nhất thị trường, đọc hiểu tiếng Việt rất tốt, trích xuất cấu trúc chuẩn. |

---

## 2. Chi Tiết Lựa Chọn Từng Tầng API Rẻ Nhất & Đủ Dùng Cho Tiếng Việt

### 2.1. Tầng Xử Lý Âm Thanh Cuộc Họp (ASR + Diarization + Word Timestamps)

#### Lựa chọn chính thức: **Gladia API (Solaria-1)**
- **Vì sao chọn:**
  1. **Giá rẻ nhất trọn gói:** **0.16€ – 0.22€ / giờ audio** (~**5.000 – 6.000 VNĐ / giờ họp**). Các bên khác như Deepgram thu thêm phí Diarization riêng ($0.26 + $0.12 = $0.38/h), Google thu $0.96/h. Gladia đã gom toàn bộ vào giá gốc.
  2. **Đủ dùng và tối ưu cho cuộc họp tiếng Việt:** Xử lý rất tốt hiện tượng **Code-switching** (chèn thuật ngữ tiếng Anh: *sprint, deploy, backlog, task, deadline*), tỷ lệ WER tiếng Việt thực tế ~18% – 22%.
  3. **Đầy đủ dữ liệu cho Frontend:** Trả về cấu trúc JSON gồm:
     - Nhãn người nói (`speaker_0`, `speaker_1`...).
     - Phân đoạn từng câu (`start`, `end`, `text`).
     - Từng từ có mốc mili-giây chi tiết (`words[i]: {word, start, end, confidence}`) phục vụ tính năng Karaoke trên `wavesurfer.js`.
  4. **Tặng sẵn 50€ Credit:** Đăng ký tài khoản là có sẵn 50€, đủ để chạy thử và bảo vệ đồ án cho khoảng **200 giờ họp hoàn toàn miễn phí**.

---

### 2.2. Tầng Vector Embedding Cho RAG (Hỏi Đáp Nội Dung)

#### Khuyến nghị số 1: **Giữ `multilingual-e5-small` chạy trên CPU cục bộ (0 VNĐ)**
- File model chỉ nặng **120MB INT8 / 470MB FP32**.
- Khi người dùng hoàn thành cuộc họp 1 tiếng (~300 câu / chunks):
  - Chạy hàm `model.encode(texts)` trên CPU 4-core mất đúng **1.5 đến 2 giây**.
  - Không tốn một đồng chi phí API.
  - Không phải đổi cấu hình kiểu dữ liệu `vector(384)` đã thiết kế sẵn trong bảng `transcript_embeddings` của PostgreSQL.

#### Khuyến nghị số 2 (Nếu muốn 100% gọi API): **OpenAI `text-embedding-3-small`**
- Giá: **$0.02 / 1.000.000 tokens**.
- Một cuộc họp 1 tiếng có khoảng 15.000 từ (~20.000 tokens).
- Chi phí nhúng toàn bộ cuộc họp: **0.0004 USD (~10 VNĐ / cuộc họp)**.
- Tham số chiều có thể ép về `dimensions = 512` hoặc `384` qua cơ chế Matryoshka.

---

### 2.3. Tầng Tóm Tắt & Hỏi Đáp RAG (LLM)

#### Lựa chọn chính thức: **Google Gemini 2.0 Flash** *(hoặc OpenAI GPT-4o-mini)*
- **Gemini 2.0 Flash:**
  - Giá input: **$0.10 / 1M tokens**.
  - Giá output: **$0.40 / 1M tokens**.
  - Quota miễn phí: Có sẵn Free Tier thử nghiệm (15 RPM).
  - Khả năng tiếng Việt: Rất tự nhiên, khả năng đọc hiểu ngữ cảnh dài lên đến 1M tokens (chứa được cả transcript cuộc họp kéo dài 10 tiếng).
- **OpenAI GPT-4o-mini (Phương án dự phòng):**
  - Giá input: **$0.15 / 1M tokens**, output: **$0.60 / 1M tokens**.
  - Ép kiểu JSON Schema bằng tính năng Structured Outputs chuẩn xác 100% khi sinh danh sách Action Items.
- **Chi phí thực tế:** Một lần tóm tắt cuộc họp + 10 câu hỏi chat RAG chỉ tiêu tốn khoảng **0.002 – 0.004 USD (~50 – 100 VNĐ)**.

---

## 3. Tổng Chi Phí Thực Tế Cho Một Cuộc Họp 1 Tiếng

| Hạng mục xử lý | Đơn vị thực thi | Chi phí mỗi cuộc họp (VNĐ) |
|---|---|---|
| Lọc VAD & Pass 1 Draft | CPU (Local) | **0 VNĐ** |
| Nhận dạng ASR + Tách người nói (Gladia) | Cloud API | **~5.500 VNĐ** *(hoặc 0đ với gói 50€ free)* |
| Vector Embedding RAG (`e5-small` CPU) | CPU (Local) | **0 VNĐ** |
| LLM Tóm tắt + 5 câu hỏi chat RAG (Gemini) | Cloud API | **~60 VNĐ** |
| **Tổng cộng mỗi cuộc họp 1 giờ** | | **~5.560 VNĐ** |

---

## 4. Tác Động Đến Hạ Tầng Máy Chủ (DevOps)

Khi chuyển Pass 2 sang Cloud API:
1. **Bỏ hoàn toàn yêu cầu GPU:** Không cần NVIDIA GPU, không cần cấu hình NVIDIA Container Toolkit phức tạp trong Docker.
2. **Cấu hình máy chủ triển khai siêu nhẹ:**
   - Chỉ cần 1 VPS CPU tiêu chuẩn: **2 đến 4 vCPU, 4GB – 8GB RAM**.
   - Giá thuê VPS: khoảng **150.000 – 300.000 VNĐ / tháng** (so với 6 – 10 triệu VNĐ/tháng nếu thuê VPS GPU).
   - Tốc độ xử lý: File audio 1 giờ gửi lên Gladia chỉ mất **30 – 45 giây** là trả về toàn bộ kết quả phân đoạn người nói và mốc từ.
