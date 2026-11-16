# Nghiên Cứu Chuyển Đổi Các Mô Hình AI Self-Host Sang Cloud API

**Đề tài:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp  
**Sinh viên thực hiện:** Nguyễn Phương Linh — MSSV 20224871 — Lớp IT1-02  
**GVHD:** Thầy Cao Tuấn Dũng — Trường CNTT&TT, ĐHBK Hà Nội  
**Tài liệu:** `docs/02-research-tech/cloud-api-models-evaluation.md`  
**Ngày lập:** 01/11/2026  

---

## 1. Tổng Quan Bài Toán và Hiện Trạng Hệ Thống

Theo khảo sát kiến trúc trong `docs/02-research-tech/` và mã nguồn `ai-service`, hệ thống hiện tại đang thiết kế các mô hình AI theo phân tầng sau:

| Thành phần | Mô hình self-host hiện tại | Phần cứng dự kiến | Mục đích kỹ thuật |
|---|---|---|---|
| **VAD (Phát hiện tiếng nói)** | `Silero VAD v6` (ONNX) | CPU / GPU (~0.1 GB VRAM) | Lọc khung âm thanh 32ms, loại bỏ khoảng lặng/tạp âm |
| **Pass 1 ASR (Draft realtime)** | `sherpa-onnx Zipformer-vi INT8` (~75MB) | CPU / GPU (~0.2 GB VRAM) | Hiển thị chữ nháp trực tiếp trên WebSocket, trễ ≤ 1.5s |
| **Pass 2 ASR (Batch offline)** | `PhoWhisper-medium-ct2` (CUDA FP16) | GPU (~2.0 GB VRAM) | Nhận dạng chính thức, trích xuất word-level timestamps |
| **Speaker Diarization** | `pyannote community-1` / `3.1` (PyTorch) | GPU (~2.5 GB VRAM) | Tách người nói (SPEAKER_00, SPEAKER_01...), gán turn |
| **Căn chỉnh Word-to-Speaker** | Thuật toán cục bộ (Python) | CPU | Giao cắt timestamps của Whisper và Pyannote turns |
| **Text Embedding (RAG)** | `multilingual-e5-small` (384 dims) | GPU / CPU (~0.4 GB VRAM) | Tạo vector cho transcript chunk lưu vào pgvector |
| **LLM (Tóm tắt & RAG)** | Đã dùng Cloud API (`GPT-4o-mini`) | Cloud API ngoài | Tóm tắt, trích xuất Action Items, trả lời hỏi đáp |

### Vấn đề đặt ra khi Self-Host toàn bộ:
1. **Chi phí hạ tầng GPU:** Để chạy trơn tru Pass 2 ASR + Diarization + Embedding, tài liệu thiết kế yêu cầu máy chủ có GPU chuyên dụng **16GB – 24GB VRAM** (RTX 3090, RTX 4090, A10G). Chi phí thuê Cloud VPS GPU 24/7 dao động từ **$220 – $720/tháng** (~5.500.000 – 18.000.000 VNĐ/tháng), vượt quá ngân sách thử nghiệm sinh viên/dự án nhỏ.
2. **Độ phức tạp vận hành:** Quản lý CUDA drivers, container GPU passthrough, rủi ro tràn bộ nhớ (CUDA OOM), và yêu cầu Hugging Face Token cho Pyannote gated repo.

---

## 2. Ma Trận Đánh Giá Khả Năng Thay Thế Từng Thành Phần

```
┌────────────────────────────────────────────────────────────────────────┐
│               MA TRẬN QUYẾT ĐỊNH: SELF-HOST VS CLOUD API               │
├──────────────────────┬─────────────┬──────────────┬────────────────────┤
│ Thành phần           │ Khả năng    │ Phương án    │ Khuyến nghị        │
│                      │ chuyển API  │ Cloud API    │ triển khai         │
├──────────────────────┼─────────────┼──────────────┼────────────────────┤
│ 1. Silero VAD        │ KHÔNG       │ Không có     │ GIỮ NGUYÊN LOCAL   │
│ 2. Pass 1 Zipformer  │ KHÔNG NÊN   │ Deepgram WS  │ GIỮ NGUYÊN LOCAL   │
│ 3. Pass 2 PhoWhisper │ RẤT TỐT     │ Deepgram /   │ ĐỔI SANG API HOẶC  │
│ 4. Pyannote Diarize  │ RẤT TỐT     │ Gladia /     │ DÙNG ALL-IN-ONE    │
│                      │             │ Google Chirp2│ API AUDIO          │
│ 5. e5-small Embed    │ RẤT TỐT     │ OpenAI 3-s / │ ĐỔI SANG API HOẶC  │
│                      │             │ Gemini Embed │ GIỮ LOCAL TRÊN CPU │
└──────────────────────┴─────────────┴──────────────┴────────────────────┘
```

---

## 3. Nghiên Cứu Chi Tiết Từng Thành Phần

### 3.1. Voice Activity Detection (VAD) & Pass 1 ASR (Streaming Draft)

#### Quyết định: **BẮT BUỘC GIỮ LOCAL TRÊN CPU**
- **Lý do kỹ thuật VAD:** `Silero VAD v6` là mô hình ONNX siêu nhẹ (~10MB), xử lý từng khung âm thanh 32ms trong vòng **dưới 1ms trên CPU**. Không một dịch vụ Cloud nào cung cấp API chỉ để bắt VAD cho từng gói micro; gọi HTTP/WebSocket lên cloud cho tác vụ này sẽ gây trễ mạng 100–300ms, phản tác dụng hoàn toàn.
- **Lý do kỹ thuật Pass 1:** `sherpa-onnx Zipformer-vi INT8` dung lượng chỉ **75MB**, chạy trực tiếp trên CPU của container Backend/AI Service với RTF ~0.01 (xử lý 1 giây âm thanh chỉ mất 10 mili-giây).
  - Chi phí tự host trên CPU: **0 VNĐ**.
  - Không cần GPU.
  - Nếu chuyển sang API streaming ngoài (như Deepgram Streaming), chi phí là **$0.46 – $0.55/giờ**, kèm độ trễ mạng quốc tế từ Việt Nam sang máy chủ US/EU.

---

### 3.2. Pass 2 Batch ASR + Speaker Diarization (Thành phần tốn GPU nhất)

Đây là nút thắt chính yêu cầu GPU 24GB. Trong pipeline hiện tại:
- `PhoWhisper-medium` tốn ~2.0 GB VRAM.
- `pyannote community-1` tốn ~2.5 GB VRAM.
- Cần thuật toán căn chỉnh phức tạp `Word-to-Speaker Alignment` để gộp mốc từ của Whisper vào mốc turn của Pyannote.

#### Các ứng viên Cloud API hàng đầu cho Tiếng Việt:

#### Ứng viên 1: **Gladia API (Solaria-1)** — *Khuyến nghị số 1 cho Meeting*
- **Đặc điểm:** Thiết kế chuyên biệt cho Audio Intelligence và cuộc họp doanh nghiệp. Đóng gói sẵn **ASR + Speaker Diarization + Word-level Timestamps + Code-switching** trong 1 lần gọi API duy nhất.
- **Hỗ trợ tiếng Việt:** Tốt, nhận dạng đa ngữ chuẩn xác, tự động nhận diện từ chèn tiếng Anh (code-switching: deploy, sprint, backlog).
- **Benchmark & Chất lượng:**
  - Lõi dựa trên kiến trúc Whisper tối ưu hóa kết hợp mô hình phân tách người nói nơ-ron độc quyền.
  - Tỷ lệ WER trên tiếng Việt hội thoại: ~**18% – 24%** (tương đương hoặc vượt trội PhoWhisper-medium trên âm thanh có nhiễu).
  - Trích xuất mốc từ chính xác theo mili-giây (`start`, `end`, `confidence` từng từ), đáp ứng 100% tính năng Karaoke của `wavesurfer.js`.
- **Giá thành:**
  - Xử lý Batch: **0.16€ – 0.27€ / giờ âm thanh** (tương đương **$0.18 – $0.29 / giờ audio**, tức khoảng **4.500 – 7.200 VNĐ / giờ họp**).
  - Diarization: **Đã bao gồm trong giá gốc** (không phụ thu thêm).
  - Tặng miễn phí: **50€ credit khi đăng ký** (xử lý được gần 200 giờ họp miễn phí).

#### Ứng viên 2: **Deepgram (Nova-3)** — *Khuyến nghị số 2 về Tốc độ và Chi phí*
- **Đặc điểm:** Mô hình Nova-3 thế hệ mới nhất của Deepgram, tối ưu hóa riêng cho các ngôn ngữ có thanh điệu (Tonal contours) như tiếng Việt.
- **Hỗ trợ tiếng Việt:** Hỗ trợ chính thức mã ngôn ngữ `language=vi`, nhận dạng cả tiếng Bắc, Trung, Nam.
- **Benchmark & Chất lượng:**
  - WER trên tiếng Việt: **~16% – 22%**, tốc độ xử lý nhanh nhất thị trường (xử lý 1 giờ audio trong dưới 15 giây).
  - Diarization: Hỗ trợ nhận diện số người nói thông qua tham số `diarize=true`.
  - Word timestamps: Cung cấp đầy đủ mốc thời gian từng từ.
- **Giá thành (Pay-As-You-Go):**
  - Base Pre-recorded ASR: **$0.0043 / phút** ($0.258 / giờ audio).
  - Speaker Diarization: **+$0.0020 / phút** ($0.120 / giờ audio).
  - **Tổng cộng ASR + Diarization: $0.378 / giờ audio** (khoảng **9.500 VNĐ / giờ họp**).
  - Tặng miễn phí: **$200 credit dùng thử** (xử lý được hơn 500 giờ họp).

#### Ứng viên 3: **Google Cloud Speech-to-Text v2 (Chirp 2)**
- **Đặc điểm:** Kiến trúc USM (Universal Speech Model) 2 tỷ tham số của Google, đặt datacenter tại Singapore (`asia-southeast1`) cho độ trễ cực thấp về Việt Nam.
- **Hỗ trợ tiếng Việt:** `vi-VN` là một trong những ngôn ngữ mạnh nhất của Google nhờ lượng dữ liệu YouTube khổng lồ.
- **Benchmark & Chất lượng:**
  - WER: Thuộc nhóm thấp nhất thị trường (**~14% – 18%** trên tiếng Việt đàm thoại).
  - Hỗ trợ Diarization qua cấu hình `BatchRecognize`.
- **Giá thành:**
  - Standard Batch: **$0.016 / phút** ($0.96 / giờ audio, khoảng **24.000 VNĐ / giờ họp**).
  - Dynamic Batch (chấp nhận kết quả sau vài giờ): **$0.003 / phút** ($0.18 / giờ audio).
  - Miễn phí: **60 phút đầu tiên mỗi tháng**.

#### Ứng viên 4: **OpenAI Whisper API (`whisper-1`)**
- **Đặc điểm:** Mô hình Whisper Large chạy trên cụm máy chủ OpenAI.
- **Giá thành:** **$0.006 / phút** ($0.36 / giờ audio).
- **HẠN CHẾ CHÍ MẠNG:** OpenAI Whisper API **HOÀN TOÀN KHÔNG CÓ TÍNH NĂNG SPEAKER DIARIZATION**. Nếu dùng OpenAI Whisper API, bạn vẫn phải tự chạy Pyannote hoặc gọi một dịch vụ khác để tách người nói, do đó không giải quyết được bài toán bỏ GPU server.

#### Ứng viên 5: **Google Gemini 2.0 Flash (Multimodal Audio Direct)**
- **Đặc điểm:** Đưa trực tiếp toàn bộ tệp âm thanh (lên đến 2 giờ) vào Gemini 2.0 Flash trong một prompt duy nhất.
- **Cơ chế:** Gemini tự "nghe" audio, tự phân biệt giọng người nói, tự sinh transcript kèm timestamp và tự tóm tắt trong 1 lần suy luận.
- **Giá thành:**
  - Audio input token: ~$0.70 / 1 triệu tokens (khoảng **$0.06 – $0.08 / giờ audio**, tức chỉ **1.500 – 2.000 VNĐ / giờ họp**!). Rẻ nhất trong tất cả các giải pháp.
- **Hạn chế kỹ thuật:** Gemini trả về timestamp theo câu/lượt nói (coarse timestamps dạng `[01:25]`), **không trả về mốc thời gian từng từ (word-level timestamps)** để làm hiệu ứng Karaoke đổi màu chữ trên trình phát audio.

---

### 3.3. Text Embedding Cho RAG (Truy Hồi Hội Thoại)

Hiện tại hệ thống dùng `multilingual-e5-small` (118M tham số, 384 dimensions).

| Mô hình | Hình thức | Số chiều (dims) | Điểm MTEB Retrieval | Chi phí trên 1 giờ họp (~20.000 tokens) | Đánh giá |
|---|---|---|---|---|---|
| **multilingual-e5-small** | Self-host (CPU/GPU) | 384 | 60.2 | 0 VNĐ (chạy cục bộ) | Nhẹ, chạy tốt trên CPU (~50ms/chunk) |
| **OpenAI `text-embedding-3-small`** | Cloud API | 512 / 1536 | 62.3 | **$0.0004** (~10 VNĐ / cuộc họp) | Siêu rẻ, chất lượng truy hồi xuất sắc, hỗ trợ cắt chiều về 384/512 |
| **Google `text-embedding-004`** | Cloud API | 768 | 63.5 | **Miễn phí** (1500 req/ngày), sau đó $0.00002/1k chars | Rất tốt cho tiếng Việt, quota miễn phí thoải mái cho đồ án |
| **Cohere `embed-multilingual-v3.0`** | Cloud API | 1024 | 64.1 | $0.002 (~50 VNĐ / cuộc họp) | Chuyên sâu cho ngữ cảnh đa ngữ phức tạp |

> [!TIP]
> **Nhận định về Embedding:** Mô hình `multilingual-e5-small` thực chất **rất nhẹ và hoàn toàn có thể chạy trên CPU** thông thường trong môi trường Docker mà không cần GPU (chỉ mất ~1.5 giây để nhúng 300 chunks của 1 cuộc họp). Nếu muốn chuyển sang API, **OpenAI `text-embedding-3-small`** hoặc **Google `text-embedding-004`** là giải pháp tối ưu với chi phí gần như bằng 0.

---

## 4. Bảng So Sánh Tổng Thể Benchmark & Chi Phí Thực Tế

### 4.1. So sánh Benchmark Kỹ Thuật

| Tiêu chí kỹ thuật | Self-Host (PhoWhisper + Pyannote) | Gladia API (Solaria-1) | Deepgram API (Nova-3) | Google Cloud Speech (Chirp 2) |
|---|---|---|---|---|
| **WER Tiếng Việt Hội thoại** | 26.85% (VLSP-2) | ~18% – 24% | ~16% – 22% | ~14% – 18% |
| **Diarization Error Rate (DER)** | ~12% – 18% (Pyannote 3.1) | ~12% – 17% | ~14% – 20% | ~15% – 22% |
| **Word-Level Timestamps** | Có (Whisper DTW) | Có (Chính xác cao) | Có (Chính xác cao) | Có |
| **Hỗ trợ Code-switching Anh-Việt** | Trung bình (cần hotwords) | Rất tốt (natively) | Tốt | Rất tốt |
| **Xử lý chồng lấn (Overlap)** | Có (Pyannote exclusive) | Có | Có | Hạn chế |
| **Thời gian xử lý file 1 giờ** | ~2 – 3 phút (GPU) / ~30 phút (CPU) | ~30 – 50 giây | ~15 – 25 giây | ~40 – 60 giây |
| **Yêu cầu GPU Server** | **Bắt buộc có GPU 16-24GB** | **Không cần GPU** | **Không cần GPU** | **Không cần GPU** |

### 4.2. Bảng Tính Chi Phí Vận Hành Cho 100 Giờ Họp / Tháng

Giả sử hệ thống xử lý trung bình **100 cuộc họp (mỗi cuộc họp 1 giờ)** trong một tháng:

| Phương án kiến trúc | Chi phí ASR + Diarization | Chi phí RAG Embedding | Chi phí Hạ tầng Máy chủ | Tổng chi phí / tháng |
|---|---|---|---|---|
| **Phương án 1: Self-Host Toàn Bộ (Theo Docs hiện tại)** | $0 (Chạy mã nguồn mở) | $0 | **$250 – $400 / tháng** (Thuê VPS GPU RTX 3090 / A10G 24GB) | **~6.250.000 – 10.000.000 VNĐ** |
| **Phương án 2: Gladia API** | 100h × $0.22 = **$22** | 100h × $0.0004 = **$0.04** | **$10 – $20 / tháng** (VPS CPU thường 4 vCPU, 8GB RAM) | **~800.000 – 1.050.000 VNĐ** *(Tiết kiệm ~85-90%)* |
| **Phương án 3: Deepgram Nova-3 API** | 100h × $0.38 = **$38** | $0.04 | **$10 – $20 / tháng** (VPS CPU thường) | **~1.200.000 – 1.450.000 VNĐ** *(Tiết kiệm ~80%)* |
| **Phương án 4: Serverless GPU (RunPod/Modal)** | 100h × 3m = 300m GPU = **$3.00** | $0 (Local CPU) | **$10 – $20 / tháng** (VPS CPU điều phối) | **~350.000 – 600.000 VNĐ** *(Rẻ nhất nếu vẫn muốn self-host)* |

---

## 5. Góc Nhìn Đồ Án Tốt Nghiệp: Nên Chọn Phương Án Nào?

Vì đây là **Đồ án Tốt nghiệp Cử nhân CNTT tại ĐHBK Hà Nội (GVHD: Thầy Cao Tuấn Dũng)**, việc lựa chọn công nghệ cần cân đối giữa **tính thực tiễn/chi phí** và **giá trị học thuật khi bảo vệ trước Hội đồng chấm thi**:

> [!WARNING]
> **Rủi ro khi chuyển 100% sang API thương mại trong Đồ án Tốt nghiệp:**
> Nếu sinh viên thay thế toàn bộ ASR và Diarization bằng Gladia hay Deepgram, Hội đồng bảo vệ có thể đặt câu hỏi:  
> *"Đóng góp kỹ thuật và hàm lượng AI của đề tài nằm ở đâu nếu toàn bộ phần lõi chỉ là gọi API bên thứ ba?"*

### Đề xuất Kiến Trúc Tối Ưu: "Kiến Trúc Kép" (Dual-Engine / Strategy Pattern)

Thiết kế hệ thống theo mô hình **Provider / Strategy Pattern**, cho phép chuyển đổi linh hoạt qua biến môi trường `.env`:

```
                                [AUDIO WORKER PIPELINE]
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       【CHẾ ĐỘ 1: LOCAL EXPERIMENT】                 【CHẾ ĐỘ 2: CLOUD API ENGINE】
       - Pass 2: PhoWhisper-medium                   - Engine: Gladia API hoặc Deepgram Nova-3
       - Diarization: Pyannote 3.1                   - Đóng gói: ASR + Diarization + Timestamps
       - Môi trường: Kaggle Notebook (GPU T4)        - Môi trường: Triển khai Web thực tế (VPS CPU)
       - Mục đích: Đo đạc số liệu khoa học           - Mục đích: Demo mượt mà, không tốn tiền GPU,
         (WER, CER, DER) cho Chương 5 đồ án.           chi phí chỉ vài nghìn đồng mỗi cuộc họp.
```

### Các bước cụ thể:
1. **Trong Báo cáo Đồ án (Chương 2, 4, 5):**
   - Vẫn trình bày đầy đủ cơ sở lý thuyết của `PhoWhisper`, cơ chế `CTranslate2`, mạng nơ-ron `Pyannote 3.1`, giải thuật `Word-to-Speaker Alignment` và đánh giá chỉ số thực nghiệm WER/DER trên môi trường Kaggle GPU miễn phí. Điều này đảm bảo trọn vẹn điểm số học thuật và khối lượng nghiên cứu.
2. **Trong Triển khai Ứng dụng Thực tế (Demo Web):**
   - Viết thêm adapter `GladiaAudioPipeline` hoặc `DeepgramAudioPipeline`.
   - Máy chủ web chỉ cần thuê một VPS CPU thông thường giá rẻ (~150.000 – 300.000 VNĐ/tháng).
   - Khi người dùng tải file lên, hệ thống gọi Gladia/Deepgram API, nhận về kết quả cấu trúc JSON gồm phân đoạn người nói và mốc từ trong 30 giây, đẩy thẳng vào PostgreSQL và kích hoạt RAG.
   - Chi phí demo gần như bằng 0 nhờ các gói dùng thử miễn phí ($50 của Gladia hoặc $200 của Deepgram).
