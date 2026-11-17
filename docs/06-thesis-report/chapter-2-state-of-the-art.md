# Chương 2: Tổng Quan Các Công Nghệ Liên Quan (State-of-the-Art)

## 2.1. Nhận Dạng Tiếng Nói Tự Động (ASR)
Tổng quan kiến trúc Transformer/Whisper và so sánh self-host với Cloud ASR. Implementation hiện chọn Gladia API v2 để đồng thời nhận transcript, diarization và timestamp mà không cần GPU EC2; PhoWhisper/Pyannote được giữ là phương án nghiên cứu đối chứng.

## 2.2. Kỹ Thuật Tách Người Nói (Speaker Diarization)
Phương pháp phân đoạn âm thanh, trích xuất đặc trưng âm học (x-vectors) và thuật toán phân cụm người nói.

## 2.3. Hệ Thống Tạo Sinh Tăng Cường Truy Xuất (RAG)
Nguyên lý RAG, multilingual E5, lexical retrieval, hybrid ranking và citation timestamp. Bản hiện thực dùng retrieval trong memory trên transcript của một meeting; pgvector persistent index là hướng phát triển, không phải kết quả hiện tại.
