# KẾ HOẠCH KIỂM THỬ

## 1. Phạm vi

Kiểm thử auth, project, audio pipeline, transcript, summary, RAG, export, share, billing, frontend contracts và production Compose.

## 2. Tầng kiểm thử

| Tầng | Mục tiêu | Công cụ |
|---|---|---|
| Unit | Parser Gladia, VAD, chunking, retriever, generators | pytest |
| API integration | Auth/chat/export/payment với DB SQLite test | pytest + httpx ASGITransport |
| Contract | Frontend path/payload khớp OpenAPI | TypeScript build + contract regression |
| Container | Image build, health, volume/network | Docker Compose |
| E2E thật | Browser → queue → providers → DB → export/payment | Checklist thủ công có bằng chứng |
| AI evaluation | WER/DER/citation/faithfulness | Dataset có ground truth |

## 3. Lệnh kiểm thử

```bash
cd backend-api
python -m pytest -q

cd ../ai-service
python -m pytest -q

cd ../frontend
pnpm run build

cd ..
docker compose config --quiet
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
```

## 4. Test case E2E bắt buộc

| ID | Kịch bản | Kết quả |
|---|---|---|
| E2E-01 | Register/login/profile/password | Phiên và dữ liệu đúng |
| E2E-02 | Tạo project, upload audio thật | Meeting liên kết project và chuyển completed |
| E2E-03 | Transcript edit/rename/delete/reload | Dữ liệu giữ sau reload |
| E2E-04 | Summary/action item | Nội dung xuất phát từ audio thật |
| E2E-05 | RAG + citation seek | Trả lời grounded, seek đúng đoạn |
| E2E-06 | Export DOCX/JSON/SRT | File tải và mở được |
| E2E-07 | Share viewer incognito | Metadata/view flow hoạt động; ghi nhận giới hạn auth con |
| E2E-08 | VietQR + SePay webhook | Order completed, subscription đổi, webhook trùng idempotent |
| E2E-09 | Restart Compose | DB/audio còn, container healthy |
| E2E-10 | `/live` qua HTTPS | Browser cấp mic, WebM upload và xử lý batch |

## 5. Phân biệt smoke và E2E AI

- `AUDIO_PIPELINE_ENGINE=mock` hoặc key rỗng: chỉ smoke infrastructure.
- Full E2E: key thật, audio fixture biết trước nội dung, transcript không chứa câu fallback trong code.
- LLM fallback cũng không được tính là pass summary/RAG quality.

## 6. Gap test hiện tại

- Chưa có project/transcript/share/quota integration test đầy đủ.
- Chưa có frontend test runner và browser automation.
- Chưa có test container/volume recovery tự động.
- Chưa có test production “fallback disabled”.
- Chưa có load/cost benchmark.

Các gap phải được ưu tiên theo [traceability matrix](../01-requirements/traceability-matrix.md).
