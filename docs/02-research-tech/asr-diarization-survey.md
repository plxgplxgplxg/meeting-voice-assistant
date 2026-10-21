# Khảo Sát Công Nghệ ASR, VAD & Speaker Diarization

## 1. Nhận Dạng Tiếng Nói (ASR)
- **OpenAI Whisper / Faster-Whisper:**
  - Mô hình Transformer Sequence-to-Sequence mã nguồn mở hàng đầu.
  - Faster-Whisper tối ưu hóa bằng CTranslate2 cho tốc độ suy luận nhanh gấp 4 lần so với openai-whisper gốc trên GPU/CPU.
- **Thách thức với tiếng Việt:**
  - Hiện tượng lặp từ khi gặp khoảng lặng hoặc âm thanh rè.
  - Cần tích hợp Voice Activity Detection để cắt bỏ đoạn tĩnh trước khi đưa vào ASR.

## 2. Phát Hiện Tiếng Nói (Voice Activity Detection - VAD)
- **Silero VAD:** Mô hình mạng nơ-ron nhỏ gọn (< 2MB), độ chính xác cao vượt trội so với WebRTC VAD truyền thống, độ trễ cực thấp.

## 3. Tách Người Nói (Speaker Diarization)
- **Pyannote.audio 3.1:** Kiến trúc SOTA hiện nay cho bài toán diarization, tính toán embeddings của người nói và clustering theo thời gian thực hoặc offline.
