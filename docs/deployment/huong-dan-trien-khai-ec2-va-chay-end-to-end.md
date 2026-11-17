# RUNBOOK: BIẾN MÔI TRƯỜNG, FULL E2E VÀ AWS EC2

**Cập nhật:** 17/11/2026  
**Mục tiêu:** triển khai single-host bằng Docker Compose và biết chính xác phần nào chủ dự án phải tự cung cấp.

## 1. Checklist phần Rin-chan phải làm

### Tài khoản và dữ liệu ngoài repo

- [ ] Có tài khoản AWS và quyền tạo EC2, Elastic IP, Security Group, EBS.
- [ ] Có Gladia account và API key còn quota.
- [ ] Có Google AI Studio Gemini key; hoặc OpenAI key nếu đổi provider.
- [ ] Có tài khoản ngân hàng nhận tiền, mã ngân hàng VietQR và tên/số tài khoản.
- [ ] Có SePay account, kết nối đúng tài khoản ngân hàng và tạo webhook API key.
- [ ] Có một audio tiếng Việt thật mà bạn biết nội dung để phát hiện dữ liệu giả (engine `mock`).
- [ ] Nếu kiểm thử microphone `/live`: có domain trỏ về Elastic IP và email nhận thông báo Let’s Encrypt.
- [ ] Có quyền clone repo private trên EC2 nếu repository không public.

### Quyết định trước deploy

- [ ] Chọn `LLM_PROVIDER=gemini` hoặc `openai`.
- [ ] Chọn EC2 tối thiểu tham chiếu: 4 vCPU, 8 GB RAM, 40–80 GB gp3. Đây không phải benchmark; tăng cấu hình nếu build/image/model gây OOM.
- [ ] Xác định đây là demo hạn chế hay public production. Public production phải xử lý các P0 security gap ở mục 14.
- [ ] Chọn chiến lược backup và thời gian giữ backup.

AWS cảnh báo không nên mở SSH cho toàn Internet; Security Group nên giới hạn cổng 22 vào IP quản trị. Xem [EC2 launch parameters](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-launch-parameters.html) và [Security Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-security-group.html).

## 2. Biến môi trường cần điền

Sao chép `.env.example` thành `.env`. Không commit `.env`.

| Biến | Bắt buộc production | Nguồn/cách tạo | Ghi chú |
|---|---:|---|---|
| `POSTGRES_USER` | Có | Tự chọn | Có thể giữ `postgres` |
| `POSTGRES_PASSWORD` | Có | Password manager hoặc `openssl rand -base64 32` | Không chứa ký tự cần URL-encode nếu dùng trực tiếp trong URL Compose |
| `POSTGRES_DB` | Có | Tự chọn | Mặc định `meeting_intelligence` |
| `SECRET_KEY` | Có | `openssl rand -hex 32` | Ký JWT; đổi key làm token cũ mất hiệu lực. Production từ chối giá trị mặc định |
| `AI_SERVICE_TOKEN` | Có | `openssl rand -hex 32` | Dùng chung cho `X-Service-Token` giữa Backend và AI Service, tối thiểu 32 ký tự |
| `CORS_ORIGINS` | Có | Domain công khai | Danh sách phân tách dấu phẩy, không dùng `*` ở production |
| `MAX_UPLOAD_MB` | Không | Tự chọn | Mặc định 500; Nginx cũng giới hạn 500 MB |
| `AGENT_RECURSION_LIMIT` | Không | Tự chọn | Số bước tối đa của một lượt trợ lý, mặc định 8 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | Tự chọn | Mặc định 60 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Không | Tự chọn | Mặc định 30 |
| `GLADIA_API_KEY` | Có cho AI thật | Gladia dashboard | Thiếu key làm meeting chuyển `failed` (không sinh transcript giả) |
| `GLADIA_BASE_URL` | Không | Giữ mặc định | `https://api.gladia.io` |
| `AUDIO_PIPELINE_ENGINE` | Có | `gladia` | `mock` chỉ smoke test |
| `LLM_PROVIDER` | Có | `gemini` hoặc `openai` | Compose mặc định `gemini` |
| `GEMINI_API_KEY` | Có khi dùng Gemini | Google AI Studio | Production Compose hiện yêu cầu vì provider mặc định |
| `OPENAI_API_KEY` | Có khi dùng OpenAI | OpenAI dashboard | Để rỗng khi không dùng |
| `EMBEDDING_MODEL_NAME` | Không | Hugging Face model ID | Mặc định multilingual E5 small |
| `DEVICE` | Không | `cpu` | EC2 tham chiếu không GPU |
| `SEPAY_BANK_CODE` | Có cho payment | VietQR/SePay | Phải đúng mã ngân hàng hỗ trợ |
| `SEPAY_ACCOUNT_NUMBER` | Có cho payment | Tài khoản ngân hàng | Không dùng số demo |
| `SEPAY_ACCOUNT_NAME` | Có cho payment | Tên chủ tài khoản | Dùng đúng thông tin ngân hàng |
| `SEPAY_WEBHOOK_API_KEY` | Có | SePay webhook settings | Backend dùng để xác thực webhook |
| `NEXT_PUBLIC_BACKEND_API_URL` | Chỉ local dev | `http://localhost:8000` | Production để rỗng/same-origin; public env bị đóng tại Next build |

Production Compose tự đặt `BACKEND_API_URL` (AI Service gọi công cụ về Backend) và `AGENT_CHECKPOINT_DB_URL` (hội thoại của trợ lý lưu trong schema `langgraph` của cùng PostgreSQL, do thư viện tự tạo bảng). Không cần cấu hình thêm.

`ENVIRONMENT=production` và `APP_DEBUG=false` đã được production Compose đặt trực tiếp.

### Giá trị chưa được biến môi trường hóa

Model name đang gán cố định trong `ai-service/app/core/config.py` và `ai-service/app/rag/llm_client.py`: Gemini `gemini-2.0-flash`, OpenAI `gpt-4o-mini` (dùng cho cả tóm tắt, hỏi đáp và trợ lý). Trước deploy cần xác nhận model còn được account/provider hỗ trợ. Nếu không, phải bổ sung `GEMINI_MODEL`/`OPENAI_MODEL` vào settings và code.

## 3. Chuẩn bị `.env`

```bash
cp .env.example .env
openssl rand -hex 32
nano .env
```

Kiểm tra không còn placeholder:

```bash
grep -nE 'your_|replace_with|0987654321|development-only' .env
```

Lệnh phải không in ra dòng nào. Không gửi nội dung `.env` vào issue, báo cáo, ảnh chụp hoặc chat.

## 4. Chạy local để smoke test

```bash
docker compose up --build -d
docker compose ps
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8001/health
curl -fsS http://localhost:3000
docker compose logs --tail=200 backend-api ai-service celery-worker celery-beat
```

Backend chạy `alembic upgrade head` khi khởi động container; `celery-beat` phải đang chạy vì nó chuyển sự kiện outbox sang worker mỗi 2 giây (thiếu beat thì upload xong nhưng không xử lý).

Local development công khai các cổng 3000/8000/8001/5432/6379 để debug. Không dùng file Compose dev trên EC2 public.

## 5. Tạo EC2

1. Chọn Ubuntu Server 24.04 LTS hoặc 22.04 LTS.
2. Chọn instance tham chiếu 4 vCPU/8 GB RAM hoặc lớn hơn.
3. EBS gp3 40–80 GB; bật encryption.
4. Tạo key pair hoặc dùng AWS Systems Manager.
5. Security Group inbound:

| Port | Source | Mục đích |
|---|---|---|
| 22/TCP | IP quản trị `/32` | SSH |
| 80/TCP | `0.0.0.0/0`, `::/0` | HTTP + ACME challenge |
| 443/TCP | `0.0.0.0/0`, `::/0` | HTTPS |

Không mở 3000, 5432, 6379, 8000, 8001. Production Compose không publish các cổng này.

6. Gán Elastic IP để DNS/webhook không đổi sau stop/start.
7. Nếu dùng domain, tạo bản ghi A trỏ domain về Elastic IP và chờ DNS resolve.

## 6. Cài Docker trên Ubuntu

Dùng repository chính thức, không dùng convenience script cho production. Các bước dưới đây theo [Docker Engine for Ubuntu](https://docs.docker.com/engine/install/ubuntu/) và cài luôn Compose plugin.

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Đăng xuất SSH rồi đăng nhập lại, sau đó:

```bash
docker version
docker compose version
docker run --rm hello-world
```

## 7. Tạo swap và kiểm tra tài nguyên

Nếu instance chỉ có 8 GB RAM, tạo swap 4 GB để giảm rủi ro OOM khi build AI image/load model:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
df -h
```

## 8. Clone và deploy HTTP lần đầu

```bash
git clone <REPOSITORY_URL> meeting-voice-assistant
cd meeting-voice-assistant
cp .env.example .env
nano .env
```

Validate Compose bằng chính `.env`:

```bash
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
```

Build và start:

```bash
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs --tail=200
```

Smoke test:

```bash
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1/api/v1/plans
curl -fsS http://<ELASTIC_IP>/healthz
```

Image AI có PyTorch/sentence-transformers nên build/download lần đầu có thể lâu và tốn disk/RAM.

## 9. Bật HTTPS với Certbot webroot

Microphone `getUserMedia()` chỉ khả dụng trong secure context (HTTPS hoặc localhost), theo [MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia). Bước này bắt buộc để test `/live` qua domain.

### 9.1. Điều kiện

- Domain đã resolve về Elastic IP.
- Port 80 và 443 mở.
- Nginx HTTP đang healthy.

### 9.2. Lấy certificate

```bash
export DEPLOY_DOMAIN=meeting.example.com
export LETSENCRYPT_EMAIL=you@example.com

docker compose --env-file .env -f docker-compose.prod.yml --profile tls run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d "$DEPLOY_DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" \
  --agree-tos --no-eff-email
```

Certbot webroot ghi challenge vào thư mục mà Nginx đang phục vụ, không cần dừng web server; xem [Certbot webroot documentation](https://eff-certbot.readthedocs.io/en/stable/using.html#webroot).

### 9.3. Bật cấu hình TLS

```bash
cp nginx/nginx.conf nginx/nginx.http.conf.backup
sed "s/__DOMAIN__/${DEPLOY_DOMAIN}/g" nginx/nginx.https.conf.example > nginx/nginx.conf
docker compose --env-file .env -f docker-compose.prod.yml restart nginx
curl -fsS "https://${DEPLOY_DOMAIN}/healthz"
```

### 9.4. Renew

Chạy định kỳ bằng cron/systemd timer:

```bash
docker compose --env-file .env -f docker-compose.prod.yml --profile tls run --rm certbot \
  renew --webroot -w /var/www/certbot
docker compose --env-file .env -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 10. Cấu hình SePay

1. Kết nối đúng tài khoản ngân hàng trong SePay.
2. Tạo webhook tới `https://<DOMAIN>/api/v1/payments/sepay/webhook`.
3. Chọn event tiền vào/credit phù hợp.
4. Cấu hình API key/header đúng với `SEPAY_WEBHOOK_API_KEY` mà backend kiểm tra.
5. Chuyển khoản test với đúng amount và `order_code` trong nội dung.
6. Kiểm tra log và order status; gửi lại cùng webhook phải trả trạng thái duplicate/idempotent.

Không test payment thật bằng số tài khoản demo trong `.env.example`.

## 11. Kịch bản full E2E

### 11.1. Hạ tầng

```bash
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs --tail=100 celery-worker celery-beat ai-service backend-api
```

Tất cả service có healthcheck phải `healthy`; worker và beat phải đang `Up`. Kiểm tra `/internal/` không lộ ra ngoài:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<DOMAIN>/internal/agent/v1/meetings/00000000-0000-0000-0000-000000000000/overview
```

Kết quả phải là `404`.

### 11.2. Product flow

1. Mở domain/IP, đăng ký user mới và đăng nhập lại.
2. Tạo project.
3. Upload audio thật 1–3 phút, nhớ nội dung và số người nói.
4. Xác minh meeting đi qua `uploaded`, `transcribing`, `summarizing` và dừng ở `ready`; tóm tắt và chỉ mục (`summary_status`, `index_status`) đều `ready`.
5. Mở transcript:
   - nội dung phải liên quan audio thật;
   - không được giống các câu mẫu của engine `mock`, và meeting không được gắn nhãn dữ liệu mẫu;
   - speaker/timestamp hợp lý.
6. Sửa text, rename speaker, xóa một segment, reload và kiểm tra persistence; mở lịch sử chỉnh sửa và hoàn tác một thay đổi; tóm tắt phải chuyển `stale` rồi tạo lại được bằng nút Tạo lại.
7. Phát audio, click segment và kiểm tra seek.
8. Kiểm tra summary/action items phản ánh đúng transcript.
9. Hỏi một câu có đáp án rõ; citation phải trỏ tới segment hỗ trợ câu trả lời và click seek đúng.
10. Xuất DOCX, JSON, SRT; mở file và kiểm tra encoding/timestamp.
11. Tạo viewer share link, mở cửa sổ ẩn danh: xem được, không sửa được, chỉ hỏi đáp có trích dẫn.
12. Mở pricing, tạo VietQR, hoàn tất webhook và kiểm tra plan/quota cập nhật.
13. Qua HTTPS, mở `/live`, cấp mic, ghi ngắn, dừng và xác minh file WebM đi qua batch pipeline.
14. Với tài khoản Pro: hỏi trợ lý "đổi tên Speaker 1 thành An"; thẻ đề xuất phải hiển thị diff, chỉ khi bấm Áp dụng thì transcript đổi, và Hoàn tác đưa về nguyên trạng. Yêu cầu soạn biên bản DOCX và tải về.
15. Với tài khoản Free: trợ lý chỉ trả lời có trích dẫn, không đề xuất sửa.
16. Tắt Redis 30 giây trong lúc upload rồi bật lại: meeting vẫn được xử lý (outbox).

### 11.3. Persistence

```bash
docker compose --env-file .env -f docker-compose.prod.yml restart
docker compose --env-file .env -f docker-compose.prod.yml ps
```

Meeting, transcript, subscription và audio playback phải còn sau restart.

## 12. Backup và update

### Backup database

```bash
mkdir -p backups
docker compose --env-file .env -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres -d meeting_intelligence -Fc > backups/meeting_intelligence.dump
```

Điều chỉnh user/database nếu `.env` dùng tên khác.

### Backup audio volume

Xác định tên volume bằng `docker volume ls`, sau đó archive volume vào thư mục `backups`. Không xóa volume trong quy trình backup.

### Update release

```bash
git pull --ff-only
docker compose --env-file .env -f docker-compose.prod.yml config --quiet
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
docker compose --env-file .env -f docker-compose.prod.yml ps
```

Container Backend tự chạy `alembic upgrade head` khi khởi động nên mỗi bản release có thể thay đổi schema; backup PostgreSQL trước khi update là bắt buộc.

## 13. Troubleshooting

| Triệu chứng | Kiểm tra | Cách xử lý |
|---|---|---|
| Compose báo biến required | `.env`, placeholder grep, `config` | Điền password/key bắt buộc |
| Frontend gọi localhost trên EC2 | Browser Network, build cache | Rebuild frontend; production dùng same-origin |
| Meeting đứng `uploaded` | `celery-beat` có chạy không, bảng `outbox_events` còn dòng `dispatched_at IS NULL` | Bật beat; Redis phải sẵn sàng (sự kiện tự gửi lại) |
| Meeting đứng `transcribing`/`summarizing` | worker log, `processing_jobs.status`, `attempts`, AI log | Kiểm tra provider/quota/volume; job hết 3 lần thử sẽ thành `failed`, thử lại bằng `reprocess` |
| Meeting `failed` ngay sau upload | `failure_reason` | Thường do thiếu `GLADIA_API_KEY`, `ffprobe` không đọc được file hoặc vượt giới hạn thời lượng của gói |
| Hỏi đáp báo `INDEX_NOT_READY` | `index_status` | Đợi job `index`, hoặc gọi `POST /meetings/{id}/reindex` |
| Trợ lý báo không khả dụng | `/health` của AI Service, `LLM_PROVIDER`/key, `AGENT_CHECKPOINT_DB_URL` | Điền key, kiểm tra kết nối PostgreSQL |
| Trợ lý trả 402 | Gói của người dùng | Chỉ gói có `agent_tools` (Pro, Business) dùng công cụ |
| Summary chung chung/sai | LLM provider/key/model | Sửa key/model, kiểm tra provider response |
| AI container OOM | `docker stats`, kernel log | Tăng RAM/swap; worker concurrency 1 |
| Audio 404 | `meeting_storage` mount/path | Kiểm tra volume chung Backend/Worker/AI |
| `/live` không có microphone | URL HTTP, browser permission | Bật HTTPS, cấp permission |
| SePay không nâng gói | webhook URL/key/order code/amount | Xem backend log và SePay delivery log |
| Certbot fail | DNS/port 80/challenge path | Kiểm tra A record và `/.well-known/acme-challenge/` |

## 14. Phần code còn lại trước public production

### P0 — bắt buộc

- [x] Authorization meeting tập trung (`MeetingAccessPolicy`) cho transcript, summary, chat, audio, export, trợ lý.
- [x] Không có fallback demo ở production; provider failure đặt meeting `failed` và cho phép retry.
- [x] Alembic baseline/migrations và unique/index/check constraints.
- [ ] Chuyển access/refresh token khỏi `localStorage` sang HttpOnly Secure SameSite cookie hoặc triển khai threat model tương đương.
- [ ] Thêm rate limit cho auth/upload/chat/payment webhook (CORS theo domain đã có).
- [ ] Pin dependency/image version cho AI Service (Backend đã pin) và có quy trình cập nhật CVE.
- [ ] Tự động backup + thử restore PostgreSQL/audio volume.
- [ ] Chạy kịch bản E2E mục 11 với key thật, gồm lượt trợ lý, và lưu bằng chứng.

### P1 — để full product flow ổn định

- [x] Quota check tại upload boundary (và theo thời lượng đo bằng `ffprobe`).
- [x] Regenerate summary và dựng lại chỉ mục sau khi transcript thay đổi.
- [x] Refresh-token retry phía frontend (single-flight); [ ] route guard đầy đủ (hiện chỉ chuyển về `/login` khi phiên hết hạn).
- [ ] UI quản lý project members/share revoke/expiry (chưa có tính năng revoke/expiry ở backend).
- [x] Retry/backoff cho job nền; [ ] dead-letter và cảnh báo job kẹt.
- [x] Structured logging có request ID; [ ] metrics và alert queue/provider/disk.
- [ ] Browser E2E automation cho các kịch bản chính (gồm trợ lý, duyệt, hoàn tác).
- [ ] Đưa tên model LLM vào biến môi trường.

### P2 — mở rộng

- [x] Persistent hybrid search bằng pgvector/tsvector.
- [ ] Tìm kiếm xuyên meeting trong project (công cụ `search_project`).
- [ ] S3-compatible storage thay local volume.
- [ ] Live ASR thật (WebSocket mô phỏng đã được xóa).
- [ ] CI/CD, registry image và blue/green/rollback.

## 15. Kết luận trạng thái deploy

Repo đã có đường chạy single-host cho demo E2E thật khi bạn điền key/provider/bank và hoàn tất TLS. Phần authorization, không dữ liệu giả và migrations đã xong. Chưa nên công khai cho dữ liệu nhạy cảm hoặc nhiều người dùng cho đến khi hoàn thành các mục P0 còn lại (cookie HttpOnly, rate limit, backup/restore, pin dependency) và đã chạy E2E với provider thật, vì hành vi của trợ lý với mô hình thật chưa được kiểm chứng.
