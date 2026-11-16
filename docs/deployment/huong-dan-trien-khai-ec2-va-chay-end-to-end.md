# HƯỚNG DẪN TOÀN TẬP: CẤU HÌNH BIẾN MÔI TRƯỜNG, CHẠY FULL END-TO-END VÀ TRIỂN KHAI LÊN AWS EC2

**Dự án:** Hệ thống Trợ lý Giọng nói, Phiên âm, Tóm tắt và Hỏi đáp Cuộc họp Thông minh (Meeting Voice Assistant)  
**Phiên bản:** 2.1  
**Ngày cập nhật:** 2026-11-16  
**Mục tiêu:** Hướng dẫn chi tiết từng bước cho người dùng về những phần cần tự làm (lấy API Key, điền biến môi trường, thiết lập máy ảo AWS EC2) để đưa toàn bộ hệ thống lên Internet và kiểm thử thông suốt quy trình thực tế từ A đến Z.

---

## 1. Tổng quan các phần bạn cần làm (Checklist hành động)

Hệ thống mã nguồn của dự án đã được hoàn thiện 100% về mặt lập trình:
- [x] Khởi tạo CSDL tự động (tạo bảng, kích hoạt `vector`, seed sẵn 3 gói cước Free, Pro, Unlimited).
- [x] Khớp nối các API Endpoint giữa Frontend và Backend.
- [x] Cấu hình Docker Compose đa container (`postgres`, `redis`, `backend-api`, `celery-worker`, `ai-service`, `frontend`, `nginx`).
- [x] Cấu hình Nginx Reverse Proxy tiếp nhận cổng 80/443, hỗ trợ WebSocket và tua âm thanh HTTP Range.

👉 **Những việc duy nhất bạn cần làm bao gồm:**
1. **Lấy các API Key** (Gladia API Key, Google Gemini API Key, SePay Webhook) từ các trang web cung cấp dịch vụ (hoàn toàn miễn phí).
2. **Tạo tệp `.env`** và điền các giá trị vào.
3. **Khởi tạo 1 máy ảo AWS EC2** (Ubuntu 22.04 LTS), cài đặt Docker và Docker Compose.
4. **Đưa mã nguồn lên EC2** và chạy 1 lệnh duy nhất: `docker compose -f docker-compose.prod.yml up -d --build`.
5. **Cấu hình Webhook SePay** trỏ về địa chỉ IP hoặc tên miền EC2.
6. **Thực hiện kiểm thử Full Flow End-to-End** trên trình duyệt.

---

## 2. Bảng chi tiết các Biến môi trường cần tìm và điền

Dưới đây là bảng toàn bộ các biến môi trường cấu hình trong tệp `.env` của hệ thống:

| Tên biến môi trường | Bắt buộc / Tùy chọn | Giá trị mặc định / Khuyến nghị | Mô tả chi tiết & Nơi tìm / Lấy giá trị |
|---|:---:|---|---|
| `ENVIRONMENT` | Bắt buộc | `production` | Môi trường chạy hệ thống (`production` hoặc `development`). |
| `DEBUG` | Bắt buộc | `false` | Bật/tắt chế độ debug (trên EC2 nên để `false`). |
| `STORAGE_ROOT` | Bắt buộc | `/tmp/meeting_storage` | Thư mục lưu trữ tệp ghi âm dùng chung giữa các container. |
| `SECRET_KEY` | **Bắt buộc** | Chuỗi hex 64 ký tự | Khóa bí mật ký mã JWT đăng nhập. Tạo bằng lệnh: `openssl rand -hex 32`. |
| `POSTGRES_USER` | Bắt buộc | `postgres` | Tên đăng nhập CSDL PostgreSQL. |
| `POSTGRES_PASSWORD` | **Bắt buộc** | *Tự đặt mật khẩu an toàn* | Mật khẩu truy cập PostgreSQL (ví dụ: `MeetingP@ssw0rd2026`). |
| `POSTGRES_DB` | Bắt buộc | `meeting_intelligence` | Tên cơ sở dữ liệu chính. |
| `DATABASE_URL` | Bắt buộc | `postgresql+asyncpg://postgres:<PASSWORD>@postgres:5432/meeting_intelligence` | Chuỗi kết nối CSDL asyncpg cho Backend và Worker. |
| `REDIS_URL` | Bắt buộc | `redis://redis:6379/0` | Địa chỉ hàng đợi Celery và bộ nhớ đệm Redis. |
| `AUDIO_PIPELINE_ENGINE` | Bắt buộc | `gladia` | Engine xử lý âm thanh (`gladia` hoặc `mock`). |
| `GLADIA_API_KEY` | **Bắt buộc** | *Lấy từ app.gladia.io* | Khóa API bóc tách âm thanh ASR và Diarization tiếng Việt. |
| `LLM_PROVIDER` | Bắt buộc | `gemini` | Nhà cung cấp mô hình ngôn ngữ (`gemini` hoặc `openai`). |
| `GEMINI_API_KEY` | **Bắt buộc** | *Lấy từ Google AI Studio* | Khóa API tóm tắt biên bản và hỏi đáp RAG qua Gemini 2.0 Flash. |
| `OPENAI_API_KEY` | Tùy chọn | Để trống nếu dùng Gemini | Khóa OpenAI API (chỉ cần nếu chọn `LLM_PROVIDER=openai`). |
| `SEPAY_BANK_CODE` | Bắt buộc | `MBBank` | Mã ngân hàng nhận tiền chuyển khoản (MBBank, VCB, TCB...). |
| `SEPAY_ACCOUNT_NUMBER` | Bắt buộc | Số tài khoản của bạn | Số tài khoản ngân hàng nhận tiền hiển thị trên mã VietQR. |
| `SEPAY_ACCOUNT_NAME` | Bắt buộc | Tên chủ tài khoản viết hoa | Ví dụ: `NGUYEN PHUONG LINH`. |
| `SEPAY_WEBHOOK_API_KEY` | **Bắt buộc** | *Lấy từ my.sepay.vn* | Khóa xác thực an toàn cho Webhook bắn về từ cổng SePay. |
| `NEXT_PUBLIC_BACKEND_API_URL` | **Bắt buộc** | `""` hoặc `http://<EC2_IP>` | Địa chỉ gọi API từ trình duyệt người dùng. |

---

## 3. Hướng dẫn chi tiết cách lấy từng API Key

### 3.1. Cách lấy Gladia API Key (Xử lý âm thanh & Tách người nói)
Gladia cung cấp gói dùng thử miễn phí **10 giờ âm thanh/tháng** mà không yêu cầu thẻ tín dụng:
1. Truy cập trang chủ Gladia: **[https://app.gladia.io/](https://app.gladia.io/)**
2. Nhấn **Sign Up** và đăng nhập bằng tài khoản Google hoặc Email của bạn.
3. Sau khi vào màn hình Dashboard, nhìn vào thanh menu bên trái, chọn mục **API Keys**.
4. Nhấn nút **Create New API Key**, đặt tên gợi nhớ (ví dụ: `meeting-assistant-key`).
5. Sao chép chuỗi mã API Key (dạng `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
6. Dán mã này vào biến `GLADIA_API_KEY` trong tệp `.env`.

### 3.2. Cách lấy Google Gemini API Key (Tóm tắt & Trợ lý RAG)
Google cung cấp miễn phí mô hình **Gemini 2.0 Flash** với tốc độ cực nhanh:
1. Truy cập Google AI Studio: **[https://aistudio.google.com/](https://aistudio.google.com/)**
2. Đăng nhập bằng tài khoản Gmail của bạn.
3. Ở góc trên bên trái, nhấn nút **Get API key**.
4. Nhấn **Create API key** -> Chọn **Create API key in new project** (hoặc chọn project Google Cloud sẵn có).
5. Sao chép chuỗi API Key (bắt đầu bằng `AIzaSy...`).
6. Dán mã này vào biến `GEMINI_API_KEY` trong tệp `.env`.

### 3.3. Cách lấy SePay Webhook API Key & Cấu hình VietQR
SePay là cổng trung gian kết nối tài khoản ngân hàng Việt Nam tự động qua Webhook:
1. Truy cập trang chủ SePay: **[https://my.sepay.vn/](https://my.sepay.vn/)**
2. Đăng ký một tài khoản miễn phí bằng số điện thoại hoặc email.
3. **Liên kết tài khoản ngân hàng:**
   - Vào mục **Tài khoản ngân hàng** -> Bấm **Thêm tài khoản**.
   - Chọn ngân hàng của bạn (ví dụ: Quân Đội - MBBank, Vietcombank, ACB...).
   - Nhập Số tài khoản ngân hàng và Tên chủ tài khoản.
4. **Lấy API Key Webhook:**
   - Vào mục **Cài đặt** -> **Khóa API (API Key)**.
   - Bấm **Tạo API Key mới**.
   - Sao chép chuỗi ký tự API Key này và dán vào biến `SEPAY_WEBHOOK_API_KEY` trong tệp `.env`.
   - Cập nhật các biến:
     - `SEPAY_BANK_CODE`: Mã ngân hàng của bạn (ví dụ `MBBank`, `Vietcombank`, `Techcombank`).
     - `SEPAY_ACCOUNT_NUMBER`: Số tài khoản của bạn (ví dụ `0987654321`).
     - `SEPAY_ACCOUNT_NAME`: Tên của bạn không dấu viết hoa (ví dụ `NGUYEN PHUONG LINH`).

---

## 4. Hướng dẫn Khởi tạo Máy ảo AWS EC2 từ A đến Z

### Bước 1: Đăng nhập AWS Console và Khởi tạo EC2 Instance
1. Đăng nhập vào trang quản trị AWS: **[https://aws.amazon.com/console/](https://aws.amazon.com/console/)**
2. Ở thanh tìm kiếm trên cùng, gõ **EC2** và chọn dịch vụ **EC2**.
3. Chọn khu vực (Region) ở góc trên bên phải là **Singapore (`ap-southeast-1`)** để đảm bảo đường truyền về Việt Nam có độ trễ thấp nhất.
4. Nhấn nút màu cam **Launch Instance**.

### Bước 2: Cấu hình thông số máy chủ
- **Name and tags:** Đặt tên máy ảo, ví dụ: `Meeting-Voice-Assistant-Server`.
- **Application and OS Images (Amazon Machine Image):**
  - Chọn **Ubuntu**.
  - Phiên bản: **Ubuntu Server 22.04 LTS (HVM), SSD Volume Type** (Architecture: 64-bit (x86)).
- **Instance type (Cấu hình phần cứng):**
  - Khuyến nghị chọn **`t3.large`** (2 vCPU, 8 GB RAM) hoặc **`t3.xlarge`** (4 vCPU, 16 GB RAM).
  - *Lưu ý:* Hệ thống sử dụng mô hình nhúng vector `multilingual-e5-small` trên CPU, nên dung lượng RAM tối thiểu 8 GB là lý tưởng nhất để các container chạy ổn định và mượt mà.
- **Key pair (login):**
  - Bấm **Create new key pair**.
  - Đặt tên key (ví dụ: `ec2-meeting-key`), chọn loại `RSA`, định dạng `.pem`.
  - Nhấn **Create key pair** và lưu tệp `.pem` tải về vào máy tính của bạn (rất quan trọng, không được làm mất).

### Bước 3: Cấu hình Tường lửa mạng (Network Settings - Security Group)
Chọn **Create security group** và cấu hình mở các cổng sau:
1. **SSH (Cổng 22):** Source type chọn `My IP` (để chỉ có máy tính của bạn mới kết nối SSH được vào máy chủ).
2. **HTTP (Cổng 80):** Source type chọn `Anywhere-IPv4` (`0.0.0.0/0`) - phục vụ người dùng truy cập web.
3. **HTTPS (Cổng 443):** Source type chọn `Anywhere-IPv4` (`0.0.0.0/0`) - phục vụ bảo mật SSL.
4. *(Tùy chọn)* Nếu không dùng Nginx mà muốn truy cập trực tiếp các cổng nội bộ:
   - Custom TCP Cổng **3000** (Frontend): `0.0.0.0/0`.
   - Custom TCP Cổng **8000** (Backend): `0.0.0.0/0`.

### Bước 4: Cấu hình Ổ cứng lưu trữ (Configure Storage)
- Dung lượng: Đặt **`30 GiB`** hoặc **`50 GiB`** loại **gp3** (General Purpose SSD).
- Nhấn **Launch Instance** ở góc dưới bên phải để bắt đầu tạo máy chủ. Chờ khoảng 1-2 phút trạng thái máy sẽ chuyển thành `Running`.

### Bước 5: Gán Elastic IP (Địa chỉ IP tĩnh - Khuyến nghị)
Để IP máy chủ không bị thay đổi mỗi lần khởi động lại:
1. Tại menu bên trái của EC2, chọn **Network & Security** -> **Elastic IPs**.
2. Nhấn **Allocate Elastic IP address** -> Bấm **Allocate**.
3. Chọn IP vừa tạo, bấm **Actions** -> **Associate Elastic IP address**.
4. Chọn Instance `Meeting-Voice-Assistant-Server` vừa tạo và bấm **Associate**.
5. Ghi lại địa chỉ IP công khai này (ví dụ: `13.250.80.123`).

---

## 5. Cài đặt Môi trường trên Máy chủ EC2

### Bước 1: Kết nối SSH vào EC2
Mở Terminal trên máy tính của bạn (macOS / Linux) hoặc PowerShell (Windows):
```bash
# Phân quyền tệp key SSH (chỉ người dùng mới đọc được)
chmod 400 /path/to/ec2-meeting-key.pem

# Kết nối SSH vào máy ảo Ubuntu
ssh -i /path/to/ec2-meeting-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### Bước 2: Cập nhật hệ thống và Tạo bộ nhớ ảo Swap 4GB
Bộ nhớ ảo Swap giúp máy chủ không bao giờ bị tràn RAM khi Docker tải các thư viện AI nặng:
```bash
# Cập nhật danh mục gói phần mềm
sudo apt update && sudo apt upgrade -y

# Tạo file swap 4GB
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Thiết lập swap tự động kích hoạt khi reboot
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Kiểm tra bộ nhớ
free -h
```

### Bước 3: Cài đặt Docker Engine và Docker Compose plugin
Chạy đoạn lệnh cài đặt Docker chính thức từ kho lưu trữ của Docker:
```bash
# Cài đặt các gói phụ trợ
sudo apt install -y ca-certificates curl gnupg lsb-release git

# Thêm khóa GPG của Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Thêm repository Docker vào APT
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cài đặt Docker và Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Cấp quyền cho user ubuntu chạy docker không cần gõ sudo
sudo usermod -aG docker ubuntu

# Thoát ra và đăng nhập lại SSH để nhận quyền docker
exit
```
Đăng nhập lại SSH:
```bash
ssh -i /path/to/ec2-meeting-key.pem ubuntu@<EC2_PUBLIC_IP>
docker --version
docker compose version
```

---

## 6. Đưa Mã Nguồn lên EC2 và Khởi động Hệ thống

### Bước 1: Tải mã nguồn dự án về EC2
Bạn có thể clone từ kho Git của bạn:
```bash
cd ~
git clone <URL_REPO_CUA_BAN> meeting-voice-assistant
cd meeting-voice-assistant
```
*(Hoặc dùng `scp`/`rsync` để copy toàn bộ thư mục từ máy tính cá nhân lên EC2 nếu chưa đẩy lên git).*

### Bước 2: Tạo tệp `.env` và điền thông tin
Tạo tệp `.env` từ file mẫu:
```bash
cp .env.example .env
nano .env
```
Điền đầy đủ các thông tin:
```ini
ENVIRONMENT=production
DEBUG=false
STORAGE_ROOT=/tmp/meeting_storage

# Sinh một chuỗi ngẫu nhiên bằng openssl rand -hex 32
SECRET_KEY=9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b

POSTGRES_USER=postgres
POSTGRES_PASSWORD=MatKhauDatabaseBaoMat2026!
POSTGRES_DB=meeting_intelligence
DATABASE_URL=postgresql+asyncpg://postgres:MatKhauDatabaseBaoMat2026!@postgres:5432/meeting_intelligence

REDIS_URL=redis://redis:6379/0

AUDIO_PIPELINE_ENGINE=gladia
GLADIA_API_KEY=dien_gladia_api_key_cua_ban_vao_day
GLADIA_BASE_URL=https://api.gladia.io

LLM_PROVIDER=gemini
GEMINI_API_KEY=dien_gemini_api_key_cua_ban_vao_day

SEPAY_BANK_CODE=MBBank
SEPAY_ACCOUNT_NUMBER=0987654321
SEPAY_ACCOUNT_NAME=NGUYEN PHUONG LINH
SEPAY_WEBHOOK_API_KEY=dien_sepay_api_key_cua_ban_vao_day

BACKEND_API_URL=http://backend-api:8000
AI_SERVICE_URL=http://ai-service:8001

# Nếu dùng cấu hình Nginx cổng 80 của EC2, bạn có thể để trống ("") 
# hoặc điền IP công khai: http://<EC2_PUBLIC_IP>
NEXT_PUBLIC_BACKEND_API_URL=http://<EC2_PUBLIC_IP>
```
Lưu tệp bằng cách nhấn `Ctrl + O` -> `Enter`, sau đó thoát bằng `Ctrl + X`.

### Bước 3: Khởi động hệ thống trọn gói bằng Docker Compose
Chạy tệp cấu hình sản xuất (có tích hợp sẵn Nginx Reverse Proxy tiếp nhận cổng 80):
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Hệ thống sẽ tự động tải các image, build Frontend, Backend, AI Service và Worker.

Kiểm tra trạng thái các container:
```bash
docker compose -f docker-compose.prod.yml ps
```
Bạn sẽ thấy 7 container đều ở trạng thái `Up` hoặc `Up (healthy)`:
- `meeting_nginx`: Cổng 80, 443
- `meeting_frontend`: Cổng 3000 nội bộ
- `meeting_backend_api`: Cổng 8000 nội bộ
- `meeting_celery_worker`: Chạy nền
- `meeting_ai_service`: Cổng 8001 nội bộ
- `meeting_postgres`: Cổng 5432 nội bộ (kèm pgvector)
- `meeting_redis`: Cổng 6379 nội bộ

Xem nhật ký khởi động của Backend:
```bash
docker compose -f docker-compose.prod.yml logs backend-api
```
Bạn sẽ thấy thông điệp xác nhận CSDL tự động khởi tạo thành công:
```
database_initialization_success
Uvicorn running on http://0.0.0.0:8000
```

---

## 7. Cấu hình Webhook SePay trỏ về EC2

Để tính năng thanh toán tự động kích hoạt khi có người chuyển khoản:
1. Đăng nhập vào trang quản trị SePay: **[https://my.sepay.vn/](https://my.sepay.vn/)**
2. Vào menu bên trái chọn **Tích hợp Webhook** -> Bấm **Thêm Webhook**.
3. **Cấu hình Webhook:**
   - **Tên Webhook:** `Meeting Voice Assistant EC2`
   - **URL Webhook:** 
     - Nếu có tên miền: `https://your-domain.com/api/v1/payments/webhook`
     - Nếu dùng IP EC2 trực tiếp: `http://<EC2_PUBLIC_IP>/api/v1/payments/webhook`
   - **Xác thực:** Chọn phương thức **API Key** và dán đúng chuỗi giá trị bạn đã điền trong biến `SEPAY_WEBHOOK_API_KEY`.
   - **Sự kiện gửi:** Chọn **Giao dịch tạo mới (Tiền vào)**.
4. Bấm **Lưu webhook**.
5. Bấm nút **Gửi thử nghiệm (Test Webhook)** trên dashboard SePay để kiểm tra. Bạn sẽ thấy Backend EC2 ghi log phản hồi HTTP 200 OK!

---

## 8. Kịch bản Kiểm thử Full Flow End-to-End thực tế

Sau khi máy chủ đã chạy, bạn hãy mở trình duyệt trên máy tính và thực hiện quy trình kiểm thử 10 bước hoàn chỉnh sau:

### Bước 1: Truy cập Trang chủ & Đăng ký tài khoản
- Mở trình duyệt truy cập: `http://<EC2_PUBLIC_IP>` (hoặc tên miền của bạn).
- Bấm vào nút **Đăng ký** ở góc trên bên phải.
- Nhập thông tin:
  - Họ và tên: `Nguyễn Phương Linh`
  - Email: `linh.test@gmail.com`
  - Mật khẩu: `Admin@123456`
- Bấm **Tạo tài khoản**. Hệ thống đăng ký thành công và tự động đăng nhập, hiển thị tên của bạn cùng huy hiệu hạn mức **QuotaBadge: 0 / 60 phút (Gói Miễn Phí)**.

### Bước 2: Tạo Không gian làm việc / Dự án
- Trên thanh chọn dự án **ProjectSelector**, bấm **Tạo dự án mới**.
- Nhập tên: `Dự án Đồ án Tốt nghiệp 2026`.
- Bấm **Tạo dự án**. Dự án mới xuất hiện trên danh mục quản lý.

### Bước 3: Tải lên tệp ghi âm cuộc họp
- Bấm vào nút **Tải lên bản ghi**.
- Chọn 1 tệp âm thanh đàm thoại ngắn (WAV hoặc MP3 từ 1 đến 5 phút để xử lý nhanh).
- Nhập tiêu đề cuộc họp: `Họp Báo Cáo Tiến Độ Tuần 1`.
- Bấm **Bắt đầu xử lý**.
- Hệ thống tải tệp lên server và tự động chuyển bạn đến trang Transcript Studio (`/meetings/<UUID>`).

### Bước 4: Quan sát xử lý tự động
- Trạng thái cuộc họp hiển thị badge màu vàng: `Đang xử lý (processing)`.
- Backend đẩy tác vụ vào `celery-worker`. Worker gọi `ai-service`, Gladia API bóc tách tiếng Việt và phân tách các người nói (`SPEAKER_00`, `SPEAKER_01`).
- Sau khoảng 30 - 60 giây, trang tự động cập nhật trạng thái sang `Hoàn thành (completed)` mà không cần bạn phải tải lại trang.

### Bước 5: Kiểm tra Transcript Studio & Tua âm thanh đồng bộ
- Bạn sẽ nhìn thấy danh sách các câu thoại đã được gỡ băng rõ ràng kèm mốc thời gian và tên người nói.
- Bấm nút **Play** trên thanh phát âm thanh:
  - Âm thanh phát mượt mà nhờ cơ chế HTTP Range stream.
  - Câu thoại đang phát sáng màu viền xanh đồng bộ.
  - Bấm vào bất kỳ câu thoại nào ở giữa danh sách, thanh phát âm thanh lập tức nhảy tua đến mốc giây tương ứng.
- **Thử sửa câu chữ:** Bấm đúp vào một câu, sửa một vài từ ngữ và bấm Lưu.
- **Thử đổi tên người nói:** Nhấp vào nhãn `SPEAKER_00`, nhập `Thầy Hướng Dẫn`, chọn *"Đổi tên cho toàn bộ cuộc họp"*. Tất cả các câu nói của người đó lập tức được đổi tên đồng loạt.

### Bước 6: Kiểm tra Tóm tắt điều hành & Action Items
- Nhấp sang tab **Tóm tắt (Summary)**:
  - Đọc phần **Tóm tắt điều hành (Executive Summary)** do Gemini 2.0 Flash sinh ra.
  - Đọc danh sách các **Luận điểm chính (Key Points)**.
  - Kiểm tra danh sách **Công việc cần làm (Action Items)**: mỗi việc có người phụ trách và nút checkbox đánh dấu hoàn thành. Thử tích chọn 1 công việc để chuyển trạng thái thành `completed`.

### Bước 7: Trải nghiệm Trợ lý Hỏi đáp RAG có trích dẫn mốc thời gian
- Nhấp sang tab **Trợ lý hỏi đáp (Chat)**:
  - Gõ câu hỏi: *"Trong cuộc họp ai là người được phân công nhiệm vụ và nội dung công việc là gì?"*.
  - Bấm nút **Gửi**.
  - Sau khoảng 1-2 giây, trợ lý trả về câu trả lời mạch lạc dạng Markdown.
  - Phía dưới câu trả lời xuất hiện các Badge trích dẫn âm thanh (ví dụ: `[Thầy Hướng Dẫn @ 00:45 - 01:15]`).
  - Bạn bấm vào Badge trích dẫn đó -> Trình phát âm thanh lập tức tua về giây thứ 45 để bạn nghe đối chứng đoạn âm thanh gốc!

### Bước 8: Xuất biên bản cuộc họp
- Nhấp vào nút **Xuất biên bản (Export)** ở góc trên bên phải.
- Chọn **Microsoft Word (.docx)**: Trình duyệt tải về tệp Word định dạng văn phòng chuẩn mực. Mở tệp trên máy để xem biên bản họp hoàn chỉnh.
- Chọn **Markdown (.md)** hoặc **PDF**: Kiểm tra tệp tải về thành công.

### Bước 9: Chia sẻ cuộc họp qua Link
- Nhấp vào nút **Chia sẻ (Share)**.
- Bật công tắc chia sẻ và chọn quyền **Chỉ xem (Viewer)**.
- Bấm **Sao chép liên kết**.
- Mở một cửa sổ trình duyệt ẩn danh (Incognito) và dán link chia sẻ vào.
- Bạn có thể xem toàn bộ biên bản, nghe audio và chat hỏi đáp RAG mà không cần phải đăng nhập tài khoản!

### Bước 10: Kiểm tra Nâng cấp gói cước qua VietQR
- Bấm vào huy hiệu hạn mức **QuotaBadge** trên thanh điều hướng.
- Modal Bảng giá hiển thị 3 gói cước. Nhấn nút **Nâng cấp ngay** tại **Gói Chuyên Nghiệp (Pro - 99.000 VNĐ)**.
- Modal hiển thị mã VietQR động Napas247 của ngân hàng bạn đã cấu hình kèm mã đơn hàng `DHxxxxxx`.
- Khi có giao dịch thực tế hoặc khi bấm nút Test Webhook trên trang SePay, SePay bắn webhook về EC2.
- Cửa sổ VietQR lập tức tự động đóng lại và thông báo nâng cấp thành công. Hạn mức của bạn nhảy vọt lên **600 phút (Gói Pro)**!

---

## 9. Cấu hình Tên miền và Chứng chỉ SSL HTTPS Miễn phí (Tùy chọn nâng cao)

Nếu bạn có tên miền riêng (ví dụ: `meeting.plxg.vn`):
1. Đăng nhập trang quản lý DNS tên miền của bạn (Cloudflare, Namecheap, v.v.).
2. Thêm bản ghi **A Record**:
   - Tên: `meeting` (hoặc `@`)
   - Giá trị IP: Địa chỉ Elastic IP của máy ảo EC2.
3. Trên máy chủ EC2, cài đặt công cụ Certbot để cấp chứng chỉ SSL Let's Encrypt:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot certonly --standalone -d meeting.plxg.vn
   ```
4. Gắn đường dẫn chứng chỉ vào tệp `nginx/nginx.conf` tại khối `listen 443 ssl`:
   ```nginx
   ssl_certificate /etc/letsencrypt/live/meeting.plxg.vn/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/meeting.plxg.vn/privkey.pem;
   ```
5. Khởi động lại Nginx: `docker compose -f docker-compose.prod.yml restart nginx`. Trang web của bạn sẽ có biểu tượng ổ khóa xanh bảo mật HTTPS tuyệt đối.

---

## 10. Hướng dẫn Khắc phục Sự cố Thường gặp (Troubleshooting)

### Sự cố 1: Container AI Service hoặc Celery Worker bị văng (Out of Memory - OOM)
- **Dấu hiệu:** Cuộc họp mãi ở trạng thái `processing`, chạy lệnh `docker compose ps` thấy worker có trạng thái `Exit 137`.
- **Nguyên nhân:** Máy chủ EC2 bị thiếu RAM khi tải mô hình embedding.
- **Cách xử lý:** 
  1. Kiểm tra bạn đã bật Swap 4GB ở Mục 5 chưa bằng lệnh `free -h`.
  2. Khởi động lại worker: `docker compose -f docker-compose.prod.yml restart celery-worker`.

### Sự cố 2: Ghi âm trực tiếp trên trang `/live` báo lỗi không kết nối được WebSocket
- **Dấu hiệu:** Bấm bắt đầu ghi âm nhưng báo lỗi kết nối máy chủ.
- **Nguyên nhân:** Cổng hoặc Nginx chưa cấu hình nâng cấp giao thức WebSocket.
- **Cách xử lý:** Đảm bảo tệp `nginx/nginx.conf` có đầy đủ khối cấu hình `proxy_set_header Upgrade $http_upgrade;` và `proxy_set_header Connection "upgrade";` (cấu hình này đã được chúng tôi thiết lập sẵn).

### Sự cố 3: Không nghe được âm thanh hoặc không tua được trên thanh phát
- **Dấu hiệu:** Bấm nút Play nhưng trình phát báo lỗi 404 hoặc không phát được.
- **Nguyên nhân:** Thư mục volume chia sẻ `/tmp/meeting_storage` chưa được cấp quyền đọc ghi giữa backend và ai-service.
- **Cách xử lý:** 
  Chạy lệnh cấp quyền trên EC2:
  ```bash
  sudo chmod -R 777 /tmp/meeting_storage
  ```

### Sự cố 4: Chuyển khoản thành công nhưng gói cước không tự động nâng cấp
- **Dấu hiệu:** Tiền đã trừ trong app ngân hàng nhưng tài khoản web vẫn là gói Free.
- **Nguyên nhân:** SePay gửi Webhook thất bại do sai API Key hoặc URL Webhook chưa mở cổng 80/443 trên AWS Security Group.
- **Cách xử lý:** 
  1. Vào SePay Dashboard -> **Lịch sử Webhook** xem mã lỗi (HTTP 401 hoặc Timeout).
  2. Nếu mã 401: Kiểm tra giá trị `SEPAY_WEBHOOK_API_KEY` trong file `.env` trên EC2 phải khớp 100% với chuỗi API Key đã nhập trên SePay.
  3. Kiểm tra nhật ký nhận Webhook trên backend bằng lệnh:
     ```bash
     docker compose -f docker-compose.prod.yml logs backend-api | grep webhook
     ```

---

## 11. Tổng kết

Toàn bộ hệ thống **Meeting Voice Assistant** đã được tối ưu hóa ở mức cao nhất:
- **Kiến trúc Không GPU:** Tiết kiệm hàng triệu đồng chi phí thuê máy chủ mỗi tháng.
- **Xử lý Hai lượt chuyên sâu:** Kết hợp hoàn hảo giữa Gladia Cloud ASR tiếng Việt và Gemini 2.0 Flash.
- **Tự động hóa hoàn chỉnh:** Từ khâu tiếp nhận âm thanh, gỡ băng, tóm tắt, xuất biên bản đến thanh toán tự động qua VietQR Napas247.

Chúc bạn triển khai thành công hệ thống lên AWS EC2 và có một buổi bảo vệ Đồ án tốt nghiệp đạt kết quả xuất sắc nhất!
