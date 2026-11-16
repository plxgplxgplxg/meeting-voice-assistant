# Hướng Dẫn Thực Nghiệm Kiểm Thử ASR & Diarization Trên Kaggle / Colab

**Đề tài:** Hệ thống phiên âm, tóm tắt và hỏi đáp nội dung cuộc họp  
**Sinh viên:** Nguyễn Phương Linh — MSSV 20224871 — Lớp IT1-02 · **GVHD:** Thầy Cao Tuấn Dũng  
**Tài liệu:** `docs/02-research-tech/kaggle-colab-test-guide.md`  
**Ngày lập:** 22/10/2026 · **Mục đích:** Hướng dẫn chạy thực nghiệm 2 tệp Notebook kiểm chứng kỹ thuật  

---

## 1. Giới Thiệu 2 Tệp Notebook Thực Nghiệm

Để kiểm chứng tính khả thi thực tế của kiến trúc kỹ thuật đề xuất trong tài liệu [**`asr-diarization-survey.md`**](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/asr-diarization-survey.md), toàn bộ các mô hình AI được kiểm thử độc lập trên môi trường **Kaggle GPU** (môi trường kiểm thử thực nghiệm cho từng module nhỏ trước khi đóng gói triển khai toàn luồng lên máy chủ GPU ~24GB VRAM):

1. [**`01_test_pass2_batch_asr_diarization.ipynb`**](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/01_test_pass2_batch_asr_diarization.ipynb):
   - **Mục tiêu:** Kiểm thử quy trình hoàn chỉnh **Lượt 2 (Pass 2 - Batch Processing)**.
   - **Các bước:** FFmpeg chuẩn hóa âm thanh (Bandpass 100-7500Hz + Loudnorm EBU R128) $\to$ Silero VAD Gatekeeper (`threshold=0.65`) lọc sạch solo nhạc nền BGM/Jingle $\to$ `PhoWhisper-medium` (`nunu-willump/PhoWhisper-medium-ct2` FP16) nhận dạng giọng nói trích xuất mốc từ (`word_timestamps`) $\to$ **Dual-Engine Diarization** (Engine 1: Pyannote với `min_speakers=2`; Engine 2: Standalone Acoustic Diarizer thuần PyTorch 100% Zero-Token) $\to$ Giải thuật căn chỉnh `Word-to-Speaker Alignment` $\to$ Hậu xử lý văn bản (loại bỏ token `unk`, lọc lặp từ, từ điển Hotwords) $\to$ Xuất file `transcript_segments_output.json` chuẩn 100% theo thiết kế.
2. [**`02_test_pass1_live_streaming_zipformer.ipynb`**](file:///Users/plxg/workspace/meeting-voice-assistant/docs/02-research-tech/02_test_pass1_live_streaming_zipformer.ipynb):
   - **Mục tiêu:** Kiểm thử quy trình **Lượt 1 (Pass 1 - Live Streaming)**.
   - **Các bước:** Tải mô hình `sherpa-onnx Zipformer-vi INT8` (`sherpa-onnx-zipformer-vi-30M-int8-2026-02-09`, ~75MB) $\to$ Silero VAD v6 Gatekeeper (`threshold=0.55`) cắt khung tiếng người $\to$ Chia nhỏ âm thanh thành từng khung 100ms mô phỏng WebSocket từ trình duyệt $\to$ Nhận dạng trực tiếp 2 tầng (Interim Preview mỗi 450ms, Finalize khi khoảng lặng $\ge 500$ms) $\to$ Đo đạc hệ số thời gian thực (RTF $\approx 0.01$) $\to$ Xuất danh sách `live_draft_segments_output.json` (`source="draft"`).

---

## 2. Hướng Dẫn Lựa Chọn Phần Cứng & Môi Trường

### 2.1. Cấu hình trên Kaggle (Khuyến nghị số 1 — Miễn phí 30h/tuần)

> [!IMPORTANT]
> **LỰA CHỌN ACCELERATOR (GPU) TRÊN KAGGLE:**
> - Tại thanh cài đặt bên phải màn hình Notebook của Kaggle (Notebook Options):
>   - Chọn mục **Accelerator**: Chọn **`GPU T4 x2`** (2x NVIDIA Tesla T4 15GB VRAM) hoặc **`GPU P100`** (16GB VRAM).
>   - **Internet**: Bật **`ON`** (bắt buộc để tải mô hình và cài đặt thư viện).
>   - **Persistence**: Chọn `Variables and Files` để lưu lại kết quả.

- **Vì sao chọn GPU T4 x2 trên Kaggle?**
  - Cả hai mô hình `PhoWhisper-medium` (FP16) và `Pyannote Diarization` khi chạy cùng lúc chỉ chiếm khoảng **4.5 – 5.0 GB VRAM**, nằm hoàn toàn an toàn trong 15 GB VRAM của card T4.
  - Tốc độ xử lý (RTF) trên T4 đạt **~0.03x**, tức một đoạn âm thanh cuộc họp 10 phút chỉ mất khoảng **18–25 giây** để vừa nhận dạng vừa tách xong người nói! Môi trường này là bước đệm kiểm thử hoàn hảo trước khi đưa pipeline lên máy chủ thuê GPU ~24GB VRAM phục vụ toàn luồng.

### 2.2. Cấu hình trên Google Colab
- Menu: **Runtime** $\to$ **Change runtime type**.
- Chọn **T4 GPU** (Hardware accelerator: T4 GPU, GPU type: Standard).
- Nhấn **Save**.

---

## 3. Các Bước Chuẩn Bị Cần Thiết Trước Khi Chạy

### 3.1. Đăng ký nhận quyền sử dụng mô hình Pyannote (Bắt buộc cho Notebook 01)
Mô hình Diarization của Pyannote là mô hình cộng đồng yêu cầu chấp thuận điều khoản nghiên cứu trên Hugging Face:
1. Đăng nhập tài khoản trên [Hugging Face](https://huggingface.co).
2. Truy cập 2 liên kết sau và bấm **"Agree and access repository"**:
   - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
   - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
3. Lấy mã truy cập cá nhân: Vào **Settings** $\to$ **Access Tokens** $\to$ Tạo token mới với quyền **`Read`**.
4. Khi chạy Cell Bước 2 trong Notebook 01, dán mã Token này vào khi được hỏi.

### 3.2. Chuẩn bị tệp âm thanh cuộc họp tiếng Việt
- Cả 2 notebook đều có sẵn cơ chế tự động tải file tiếng Việt mẫu từ kho Common Voice / PhoWhisper nếu bạn chưa có file sẵn.
- **Nếu muốn thử tệp ghi âm thật của bạn:**
  - Nhấp vào biểu tượng thư mục (Files) ở góc trái màn hình Colab/Kaggle.
  - Bấm nút **Upload** và tải tệp `.wav`, `.mp3` hoặc `.m4a` của bạn lên.
  - Đổi tên tệp thành `meeting_sample.wav` hoặc sửa biến `INPUT_AUDIO_PATH` trong notebook trỏ tới tên file của bạn.

---

## 4. Quy Trình Chạy Thực Nghiệm và Kiểm Tra Kết Quả

### 4.1. Thực nghiệm Pass 2 (`01_test_pass2_batch_asr_diarization.ipynb`)
1. Mở notebook và chọn **Run All** (hoặc chạy tuần tự từng ô từ trên xuống dưới).
2. Nhập `HF_TOKEN` khi được yêu cầu.
3. Quan sát các bước:
   - **Bước 4:** FFmpeg tự động chuẩn hóa file về 16.000 Hz, 1 kênh Mono PCM.
   - **Bước 5:** PhoWhisper nhận dạng từng từ, in ra mốc thời gian chi tiết:
     ```json
     {"w": "chúng", "s": 1200, "e": 1450, "p": 0.98}
     ```
   - **Bước 6:** Pyannote phân đoạn các khoảng người nói: `SPEAKER_00`, `SPEAKER_01`.
   - **Bước 7:** Thuật toán căn chỉnh gán nhãn người nói cho từng từ và gom lại thành các đoạn hội thoại hoàn chỉnh.
   - **Bước 8:** In bảng kết quả trực quan và xuất file `transcript_segments_output.json`.

### 4.2. Đối chiếu kết quả JSON với thiết kế
Sau khi chạy xong Notebook 01, mở file `transcript_segments_output.json` và kiểm tra cấu trúc đầu ra:

```json
[
  {
    "segment_id": "seg_a1b2c3d4",
    "start_ms": 1200,
    "end_ms": 6800,
    "speaker": "SPEAKER_00",
    "text": "chúng ta cần chốt ngân sách quý bốn trước thứ sáu",
    "words": [
      {"w": "chúng", "s": 1200, "e": 1450, "p": 0.98},
      {"w": "ta", "s": 1450, "e": 1650, "p": 0.99},
      {"w": "cần", "s": 1650, "e": 1900, "p": 0.97}
    ],
    "overlap": false,
    "confidence": 0.98,
    "source": "final"
  }
]
```
Kết quả này **khớp 100% với đặc tả kỹ thuật** được mô tả tại Mục 1.2 của tài liệu `asr-diarization-survey.md`.

---

### 4.3. Thực nghiệm Pass 1 (`02_test_pass1_live_streaming_zipformer.ipynb`)
1. Mở notebook và chạy tuần tự.
2. Mô hình `sherpa-onnx Zipformer-vi` (~75MB) sẽ được tải tự động từ GitHub Release của nhóm k2-fsa.
3. Quan sát màn hình in luồng chữ streaming:
   - Cứ mỗi 100ms âm thanh nạp vào, mô hình tiến hành giải mã và in kết quả tạm thời ngay lập tức:
     ```
     [  1.5s] (Xử lý trong 12.3ms) >> xin chào
     [  2.5s] (Xử lý trong 14.1ms) >> xin chào các bạn hôm nay chúng ta họp
     ```
4. Quan sát chỉ số hiệu năng cuối cùng:
   - **Hệ số thời gian thực (RTF):** Đạt khoảng `0.01 – 0.03` trên GPU và `0.04 – 0.06` trên CPU.
   - Khẳng định tốc độ xử lý nhanh hơn thời gian thực tế gấp **30 đến 100 lần**, chứng minh giải pháp hoàn toàn đáp ứng độ trễ hiển thị trực tiếp $\le 1.5$ giây khi họp online.

---

## 5. Xử Lý Các Lỗi Thường Gặp (Troubleshooting)

| Lỗi | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `HTTPError: 403 Client Error: Forbidden for url` | Chưa chấp nhận điều khoản mô hình pyannote trên Hugging Face. | Truy cập trang model card [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) và bấm **Agree**. |
| `CUDA out of memory` | Dùng tệp âm thanh quá dài (> 2 tiếng) với batch_size lớn. | Trong cell Whisper ASR, giảm tham số `batch_size=8` xuống `batch_size=4` hoặc `batch_size=2`. |
| `FileNotFoundError: ffmpeg` | Môi trường thiếu ffmpeg. | Chạy lệnh `!apt-get update && apt-get install -y ffmpeg` ở đầu notebook. (Mặc định Kaggle/Colab đã có sẵn). |
| `StdinNotImplementedError` | PyTorch Hub hỏi xác nhận trust repo trên môi trường không có terminal tương tác. | Đã khắc phục tự động trong notebook bằng tham số `trust_repo=True` và fallback thư viện `silero-vad`. |
| `ImportError: cannot import name '_slice' from 'numpy._core.umath'` | Xung đột bộ nhớ RAM khi pip cập nhật NumPy trong khi tiến trình kernel đã nạp binary NumPy cũ (do `import torch` trước pip). | Đã sửa notebook: chạy `pip` đầu tiên và tự động đồng bộ. Khắc phục ngay trên Kaggle: chọn menu **`Session -> Restart Session`** rồi chạy lại. |
| `pip's dependency resolver does not currently take into account...` | Pip in cảnh báo về các gói hệ thống dựng sẵn của Kaggle (bigframes, moviepy, dopamine-rl). | Đây là cảnh báo thông tin của môi trường Kaggle, không ảnh hưởng đến pipeline. Đã thêm `--no-warn-conflicts` và ghim `numpy<2.3.0` để ẩn hoàn toàn. |
| Chữ nhận dạng bị thiếu dấu hoặc dính từ | Âm thanh mẫu có chất lượng micro quá kém hoặc âm lượng quá nhỏ. | Đảm bảo âm thanh đầu vào không bị rè quá mức; kiểm tra file đã qua bước chuẩn hóa FFmpeg. |
