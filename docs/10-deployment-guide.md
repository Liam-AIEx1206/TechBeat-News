# Hướng dẫn Triển khai Hệ thống (Production Deployment Guide)

Tài liệu này hướng dẫn chi tiết từng bước triển khai hệ thống **AI Video Edit (TechBeat/DailyByte News)** lên môi trường sản xuất (Production), áp dụng kiến trúc tối giản hiệu quả cao: sử dụng **Cloudflare R2** cho kho lưu trữ, chạy bất đồng bộ trực tiếp không hàng đợi (Direct Async Tasks), và đóng gói Docker container.

---

## 1. Yêu cầu Hệ thống tối thiểu (Prerequisites)

* **Hệ điều hành**: Linux (Ubuntu 22.04 LTS hoặc mới hơn) đã cài đặt **Docker** và **Docker Compose v2**.
* **Cấu hình Phần cứng**:
  * **CPU**: Tối thiểu 2 vCPUs (Khuyên dùng 4 vCPUs chuyên dụng cho việc render video).
  * **RAM**: Tối thiểu 4 GB (Khuyên dùng 8 GB để tránh lỗi Out Of Memory khi Chrome Headless render video).
  * **Ổ cứng**: Tối thiểu 40 GB SSD.
* **Tài khoản Dịch vụ**:
  * Tài khoản **Cloudflare** (Đã kích hoạt R2 Storage và trỏ tên miền qua Cloudflare DNS).
  * Cơ sở dữ liệu **PostgreSQL** (Có thể tự host hoặc dùng dịch vụ Managed như Supabase / Neon / AWS RDS).

---

## 2. Chuẩn bị Cơ sở hạ tầng (Infrastructure Setup)

### 2.1. Cấu hình Cloudflare R2
1. Truy cập **Cloudflare Dashboard** -> **R2 Object Storage**.
2. Tạo 3 Bucket tương ứng với các nhiệm vụ:
   * `techbeat-videos`: Lưu trữ video kết xuất hoàn thiện (`.mp4`).
   * `techbeat-compositions`: Lưu trữ các bản thiết kế tĩnh (`.html`).
   * `techbeat-assets`: Lưu trữ tài nguyên nhạc nền, audio phân cảnh (`.wav`, `.mp3`) và ảnh minh họa.
3. Tạo **R2 API Token**:
   * Truy cập **Manage R2 API Tokens** -> **Create API Token**.
   * Cấp quyền **Edit (Read/Write)** cho các Bucket vừa tạo.
   * Lưu lại các giá trị: **Access Key ID**, **Secret Access Key** và **R2 Endpoint** (có dạng `https://<account-id>.r2.cloudflarestorage.com`).

### 2.2. Khởi tạo Cơ sở dữ liệu
Chạy file mã SQL khởi tạo schema tại [schema.sql](file:///d:/AI_Video_Edit/docs/schema.sql) trên công cụ SQL Editor của Supabase hoặc cơ sở dữ liệu PostgreSQL của bạn để tạo các bảng `users`, `projects` và `extractions`.

---

## 3. Cấu hình Biến môi trường (Environment Variables)

Tạo các tệp cấu hình môi trường bảo mật trên máy chủ production:

### 3.1. Cấu hình Backend (`backend/.env`)
```env
# --- DATABASE ---
DATABASE_URL=postgresql://postgres:your-db-password@your-db-host:5432/postgres

# --- CLOUDFLARE R2 (S3-COMPATIBLE) ---
# Điền R2 Endpoint của bạn (Lưu ý: bỏ tên bucket ở cuối endpoint)
S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY=your-r2-access-key-id
S3_SECRET_KEY=your-r2-secret-access-key
S3_BUCKET_NAME=techbeat-prod-storage

# --- LLM API KEYS ---
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# --- CHROMIUM PATH FOR DOCKER ---
# Đường dẫn này cực kỳ quan trọng cho Puppeteer bên trong Docker container
PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser
```

### 3.2. Cấu hình Frontend (`app/.env.production`)
```env
# --- API ENDPOINT ---
# Trỏ URL API của Next.js về địa chỉ Backend FastAPI production công khai
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## 4. Container hóa hệ thống với Docker Compose

Tạo tệp `docker-compose.yml` tại thư mục gốc của dự án (`D:\AI_Video_Edit\docker-compose.yml`) để điều phối cả Frontend và Backend:

```yaml
version: '3.8'

services:
  # --- BACKEND FastAPI ---
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: techbeat-backend
    restart: always
    # ports có thể bỏ qua hoàn toàn nếu dùng Cloudflare Tunnel
    ports:
      - "127.0.0.1:8009:8000"
    volumes:
      - backend-renders:/app/renders
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - S3_ENDPOINT=${S3_ENDPOINT}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
      - S3_BUCKET_NAME=${S3_BUCKET_NAME}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # --- FRONTEND Next.js ---
  frontend:
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: techbeat-frontend
    restart: always
    # ports có thể bỏ qua hoàn toàn nếu dùng Cloudflare Tunnel
    ports:
      - "127.0.0.1:3009:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
    depends_on:
      - backend

  # --- CLOUDFLARE TUNNEL (cloudflared) ---
  # Kích hoạt dịch vụ này để định tuyến tên miền trực tiếp thông qua Cloudflare Tunnel
  # Không cần mở bất kỳ cổng nào trên Firewall của server và không sợ xung đột cổng!
  tunnel:
    image: cloudflare/cloudflared:latest
    container_name: techbeat-tunnel
    restart: always
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN} # Lấy Token từ Cloudflare Zero Trust Dashboard
    depends_on:
      - frontend
      - backend

volumes:
  backend-renders:
```

### 4.1. Giải pháp 1: Sử dụng Cloudflare Tunnel (Khuyên dùng - Cực kỳ bảo mật & Không lộ cổng)
**Cloudflare Tunnel (cloudflared)** là giải pháp tối ưu và an toàn nhất hiện nay. Nó thiết lập một kết nối an toàn, mã hóa hai chiều từ server của bạn ra Cloudflare edge.

**Ưu điểm vượt trội**:
* **Không cần mở bất kỳ cổng nào** (như cổng 80, 443, 3000, 8000) trên firewall của máy chủ vật lý.
* Không cần cấu hình Nginx hay cài đặt SSL Let's Encrypt cục bộ trên server.
* Ngăn chặn hoàn toàn việc tin tặc quét IP và cổng mở của server.

**Các bước thiết lập**:
1. Truy cập **Cloudflare Zero Trust Dashboard** (`one.dash.cloudflare.com`).
2. Chọn **Access** -> **Tunnels** -> **Create a Tunnel**.
3. Đặt tên cho Tunnel (ví dụ: `techbeat-server`) và chọn **Save tunnel**.
4. Chọn tab **Docker**, sao chép đoạn mã Token của Tunnel (dòng ký tự dài sau `--token`) và dán vào file `.env` trên máy chủ:
   ```env
   TUNNEL_TOKEN=eyJhIjoiY2...your-unique-tunnel-token...
   ```
5. Trên Cloudflare Zero Trust Dashboard, chọn tab **Public Hostname** và tạo 2 đường dẫn định tuyến trực tiếp vào mạng nội bộ Docker:
   * **Đường dẫn Frontend**:
     * Subdomain: *(để trống hoặc `www`)*, Domain: `yourdomain.com`
     * Service: **HTTP**
     * URL: `frontend:3000` *(Tên service trong file docker-compose)*
   * **Đường dẫn API Backend**:
     * Subdomain: `api`, Domain: `yourdomain.com`
     * Service: **HTTP**
     * URL: `backend:8000` *(Tên service trong file docker-compose)*
6. Khởi chạy hệ thống bằng Docker Compose. Cloudflare Tunnel sẽ tự động kết nối và trỏ các tên miền tương ứng về đúng container trong mạng Docker nội bộ mà **không làm lộ bất kỳ cổng nào của server ra ngoài**.

---

### 4.2. Giải pháp 2: Sử dụng Nginx Reverse Proxy (Truyền thống)
Nếu bạn muốn sử dụng phương pháp định tuyến truyền thống thông qua Nginx Reverse Proxy cục bộ trên server, hãy cấu hình như sau:

Tạo cấu hình Nginx (ví dụ tại `/etc/nginx/sites-available/techbeat`):

```nginx
# --- CẤU HÌNH FRONTEND (Next.js) ---
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3009;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# --- CẤU HÌNH BACKEND API (FastAPI) ---
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8009;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Kích hoạt cấu hình và tải lại Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/techbeat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### ⚠️ Lưu ý đặc biệt về Dockerfile của Backend:
Dockerfile của Backend phải đảm bảo cài đặt **Chromium Headless** và các **font chữ tiếng Việt** để tránh lỗi kết xuất và lỗi hiển thị font. Cấu trúc mẫu Dockerfile tối ưu:

```dockerfile
FROM python:3.11-slim

# Cài đặt công cụ hệ thống, Chromium Headless và các Font chữ Việt hóa
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    ffmpeg \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Đảm bảo đường dẫn thực thi của Puppeteer
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 5. Cấu hình Cloudflare CDN, SSL & WAF

Để ứng dụng chạy an toàn và nhanh chóng trên internet, hãy cấu hình các thiết lập sau trên bảng điều khiển **Cloudflare DNS**:

1. **Bản ghi DNS (Proxy Status)**:
   * Bản ghi A hoặc CNAME cho Frontend (ví dụ: `yourdomain.com`) -> **Proxy status: Proxied (Orange cloud)**.
   * Bản ghi A hoặc CNAME cho Backend API (ví dụ: `api.yourdomain.com`) -> **Proxy status: Proxied (Orange cloud)**.
2. **Cấu hình SSL/TLS**:
   * Truy cập **SSL/TLS** -> chọn chế độ **Full** hoặc **Full (Strict)** để mã hóa toàn bộ dữ liệu từ trình duyệt của người dùng qua Cloudflare tới máy chủ Docker của bạn.
3. **Web Application Firewall (WAF)**:
   * Tạo một Firewall Rule để hạn chế spam request vào endpoint `/build-video` hoặc `/gen-scene-one` dựa trên tần suất (Rate Limiting) nhằm ngăn chặn việc lạm dụng hoặc làm cạn kiệt tài khoản API LLM/TTS của bạn.

---

## 6. Khởi động và Kiểm tra Hệ thống

### 6.1. Chạy hệ thống
Trên máy chủ sản xuất, thực hiện lệnh sau tại thư mục gốc để khởi động hệ thống dưới nền:
```bash
docker compose up -d --build
```

### 6.2. Kiểm tra log và trạng thái
* Xem log của FastAPI Backend để chắc chắn server chạy ổn định và kết nối DB thành công:
  ```bash
  docker compose logs -f backend
  ```
* Kiểm tra xem Chrome Headless có hoạt động trơn tru trong container trong lần render đầu tiên bằng cách theo dõi các dòng log dạng `[render] Render complete`.

---

## 7. Quy trình Cập nhật Hệ thống (CI/CD)

Khi cập nhật mã nguồn (ví dụ: vá lỗi, thay đổi giao diện):
1. Đảm bảo toàn bộ test suite cục bộ chạy thành công:
   ```bash
   pytest backend/
   ```
2. Thực hiện cập nhật trên server bằng cách kéo code mới nhất từ git và khởi động lại container:
   ```bash
   git pull origin v1.1
   docker compose up -d --build
   ```
   *Nhờ cơ chế volume tĩnh `backend-renders`, các video đang được kết xuất dở sẽ không bị mất khi container khởi động lại.*
