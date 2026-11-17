# Chương 5: Thực Nghiệm, Đánh Giá & Kết Luận

## 5.1. Thiết Lập Thực Nghiệm
Mô tả dataset tiếng Việt đa người nói có transcript/speaker/timestamp ground truth, provider/model/version, cấu hình EC2 và ngày chạy. Output fallback bị loại khỏi tập đánh giá.

## 5.2. Kết Quả & Đánh Giá
- Kết quả chỉ số WER đối với nhận dạng giọng nói.
- Kết quả chỉ số DER đối với tách người nói.
- Đánh giá summary/action-item, Retrieval Recall@k/MRR, citation precision/recall và faithfulness.
- Báo cáo latency percentile, failure rate và chi phí trên mỗi giờ audio.

## 5.3. Kết Luận & Hướng Phát Triển
Chỉ kết luận bằng số đo thực tế. Hướng phát triển ưu tiên: authorization/fallback/migration, persistent pgvector, S3 storage, live ASR thật, observability và CI/CD.
