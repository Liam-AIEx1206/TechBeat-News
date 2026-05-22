# TechBeat AI News Studio — Tài liệu hệ thống

> **Phiên bản tài liệu:** 2026-05-22  
> **Stack:** Next.js 14 (App Router) + FastAPI + HyperFrames + ElevenLabs + Claude / GPT

---

## 1. Tổng quan hệ thống

**TechBeat** là công cụ tạo video tin tức tự động bằng AI. Người dùng chỉ cần cung cấp **một link bài viết** hoặc **upload file** — hệ thống tự động tóm tắt nội dung, viết kịch bản, sinh giọng đọc tiếng Việt, dựng video HTML và xuất file MP4 1080p 30fps.

```
[Bài viết / File] ──► [AI tóm tắt + kịch bản] ──► [HTML composition] ──► [TTS] ──► [MP4]
```

---

## 2. Input — Đầu vào hợp lệ

### 2.1 URL bài viết
| Thuộc tính | Chi tiết |
|---|---|
| Định dạng | URL đầy đủ bắt đầu bằng `https://` |
| Nguồn hỗ trợ | TechCrunch, VnExpress, The Verge, Medium, và hầu hết các trang tin tức |
| Giới hạn | Các trang JS-only (SPA không có SSR) hoặc có paywall có thể thất bại |
| API gọi | `POST /extract/url` → `{ url: string }` |
| Trả về | `{ title, text, source }` |

### 2.2 File upload
| Loại file | Extractor |
|---|---|
| `.pdf` | `extractors/pdf.py` |
| `.docx` | `extractors/office.py` |
| `.pptx` | `extractors/office.py` |
| API gọi | `POST /extract/file` (multipart/form-data) |
| Kéo-thả | Hỗ trợ drag & drop trực tiếp lên drop zone |

### 2.3 Lựa chọn tùy chỉnh (trước khi build)
| Tùy chọn | Loại | Mặc định |
|---|---|---|
| **Theme** | 8 lựa chọn (Cyber Orange, Neo Cyan, Violet Pulse, Matrix Green, Crimson Broadcast, Aurora Mint, Y2K Magenta, Gold Editorial) | `cyber-orange` |
| **Giọng đọc TTS** | Các giọng trong **My Voices** của tài khoản ElevenLabs | Giọng mặc định cấu hình trong `ELEVENLABS_VOICE_ID` |
| **Ảnh minh họa** | Tìm kiếm từ Openverse (CC license, không cần API key) | Mock visual do AI sinh |
| **Narration** | Chỉnh sửa từng scene thủ công | AI viết tự động |

---

## 3. Output — Đầu ra

| Đầu ra | Định dạng | Vị trí |
|---|---|---|
| **Video MP4** | 1920×1080 px · 30 fps | `my-video/renders/*.mp4` · được serve tại `/renders/<filename>.mp4` |
| **Composition HTML** | HTML + GSAP animation | `my-video/index.html` |
| **Giọng đọc TTS** | WAV (hoặc MP3 nếu pydub lỗi) | `my-video/assets/p1.wav`, `p2.wav`, … |
| **Ảnh minh họa** | JPG/PNG/WebP | `my-video/assets/scene1.jpg`, `scene2.jpg`, … |
| **Lịch sử** | Được lưu vào Supabase (`extractions` table) | Xem tại `/history` |

---

## 4. Luồng hoạt động (End-to-End Flow)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                          │
│                                                                     │
│  [Dashboard] → [Input] → [Generating] → [Preview] → [HtmlPreview] → [Build]
└─────────────────────────────────────────────────────────────────────┘
         │            │            │            │           │           │
         ▼            ▼            ▼            ▼           ▼           ▼
      Màn hình    URL/File     Streaming     Xem &      Xem HTML     Render
      chào        nhập         SSE từ        chỉnh       live +       MP4
                               Claude        sửa         pick ảnh
                                             kịch bản
```

### Bước 1 — Trích xuất nội dung (`/extract/url` hoặc `/extract/file`)

```
URL/File
   │
   ▼ Backend: extractors/url.py | pdf.py | office.py
   │   - URL: requests + BeautifulSoup scrape → lấy title + main text
   │   - PDF: pdfplumber → text
   │   - DOCX/PPTX: python-docx / python-pptx → text
   │
   ▼ { title: string, text: string, source: string }
   │
   └─► Frontend lưu ExtractedContent vào state → chuyển sang generateScenes()
```

### Bước 2 — Tạo kịch bản (`POST /generate-scenes` — SSE Stream)

```
{ content: string, title: string }
   │
   ▼ Backend: routers/scenes.py → chat_completions_with_fallback()
   │   Provider chain: primary (Pinkyne/GPT) → anthropic (Claude) → groq → groq-fast
   │   Model scenes: claude-haiku-4-5-20251001 (primary) | claude-sonnet-4-6 (fallback)
   │   System prompt: viết 4-8 phân cảnh tiếng Việt + imageQuery tiếng Anh
   │
   ▼ SSE events:
   │   { type: "chunk", text: "..." }   → hiển thị real-time trên màn Generating
   │   { type: "warning", message: "..." } → cảnh báo fallback provider
   │   { type: "done", scenePlan: {...} }  → chuyển sang màn Preview
   │   { type: "error", message: "..." }   → quay lại Input
   │
   ▼ ScenePlan {
       title, theme, voiceId, totalDuration,
       scenes: [{ id, index, title, narration, visualDescription, duration, imageQuery }]
     }
```

### Bước 3 — Xem & chỉnh sửa kịch bản (Frontend only, không gọi API)

```
ScenePlan hiển thị:
- ThemePicker: chọn 1 trong 8 themes
- VoicePicker: chọn giọng từ My Voices ElevenLabs (gọi GET /voices/elevenlabs)
- SceneList: danh sách scene có thể chỉnh narration, title, duration, imageQuery
- ImagePicker: search Openverse (GET /image-search?q=...) → chọn ảnh cho scene
```

### Bước 4 — Sinh HTML composition (`POST /generate-composition` — SSE Stream)

```
{ title, scenes, totalDuration, theme }
   │
   ▼ Backend: routers/compositions.py → chat_completions_with_fallback()
   │   Provider chain: primary → anthropic → groq → groq-fast
   │   Model composition: claude-sonnet-4-6
   │
   │   System prompt (rich / compact tùy provider):
   │   - Inject BASE_CSS_TEMPLATE với theme tokens
   │   - LLM chỉ viết HTML structure + style overrides ≤120 dòng
   │   - KHÔNG viết GSAP timeline (bị strip server-side)
   │   - Layout patterns: split / centered / hero / magazine / data
   │   - Visual patterns: img-frame, stat-hero, terminal, feat-grid, compare, tl-list, quote-block, data-viz
   │
   ▼ SSE events:
   │   { type: "chunk", text: "..." }    → preview real-time trong HtmlPreviewStage
   │   { type: "done", html: "...", mergedScenes?, mergedTotalDuration? }
   │   { type: "error", message: "..." }
   │
   ▼ compositionHtml lưu vào ScenePlan.compositionHtml
   └─► ScenePreviewIframe render iframe từng scene (seek GSAP timeline đến đúng timestamp)
```

### Bước 5 — Build video (`POST /build-video` — SSE Stream)

```
BuildRequest { title, scenes, totalDuration, compositionHtml, theme, voiceId }
   │
   ▼ Stage 0: Tải ảnh minh họa
   │   - Với mỗi scene có imageUrl → download → lưu assets/sceneN.jpg
   │
   ▼ Stage 1: Composition HTML
   │   - Nếu compositionHtml từ bước 4 đã có → dùng luôn (skip LLM)
   │   - Nếu không → gọi lại generate-composition
   │   - Lưu vào my-video/index.html
   │
   ▼ Stage 2: Save index.html
   │   - Ghi file vào project HyperFrames
   │
   ▼ Stage 3: TTS (Text-to-Speech)
   │   - Với mỗi scene: synthesize_tts(narration) → assets/pN.wav
   │   - Primary: ElevenLabs (ELEVENLABS_API_KEY) với model eleven_multilingual_v2
   │   - Fallback: gTTS (Google TTS, tiếng Việt)
   │   - Đo thời lượng audio thực tế (pydub)
   │   - patch_html_timing(): strip GSAP timeline LLM viết → inject timeline mới
   │     với duration = ceil(audio_duration) + 1s buffer
   │
   ▼ Stage 4: Render MP4
   │   - npx hyperframes@0.6.20 render (trong my-video/)
   │   - Chromium headless seek GSAP timeline → FFmpeg encode
   │   - Output: my-video/renders/<timestamp>.mp4
   │
   ▼ SSE events:
       { type: "stage", stage: "composition|save|tts|render", status: "start|progress|done|error" }
       { type: "comp_chunk", text: "..." }  → stream HTML live nếu phải gọi LLM
       { type: "stage", stage: "render", status: "log", line: "..." } → render log
       { type: "done", videoUrl: "/renders/xxx.mp4", videoPath: "..." }
       { type: "error", ... }
```

---

## 5. Các màn hình (Screens)

### Màn 1: Dashboard (`stage = "dashboard"`)

**Mục đích:** Màn chào, giới thiệu sản phẩm.

**Giao diện:**
- Canvas animated — 240 ngôi sao rơi, nebula glow cam
- Parallax blob animations (3 blob màu cam/vàng)
- Badge "On Air" + đồng hồ live (cập nhật mỗi giây)
- Ticker bottom: "TECHBEAT LIVE · AI bản tin tự động · Render 1080p · 30fps · …"
- Heading lớn: **"Tin công nghệ thành video"**
- Stats row: `1080p · 6–8 phân cảnh · vi-VN TTS · Claude AI Sonnet 4`

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Click **"▶ Bắt đầu tạo video"** | Chuyển sang màn Input |
| Click **"📋 Lịch sử video"** | Điều hướng tới `/history` |
| Click avatar (UserMenu) | Xem thông tin tài khoản / Đăng xuất |

---

### Màn 2: Input (`stage = "input"`)

**Mục đích:** Nhận nội dung đầu vào từ người dùng.

**Giao diện:**
- Header stepper: bước 1/4 đang active
- Cột trái: mô tả quy trình 3 bước (01 Trích xuất → 02 AI kịch bản → 03 Render MP4)
- Cột phải: InputPanel
  - Ô nhập URL (glow khi focus)
  - Button "Trích xuất →" (active khi có URL)
  - Divider "hoặc"
  - Drop zone kéo-thả file (PDF / DOCX / PPTX)

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Nhập URL → Enter hoặc click "Trích xuất →" | Gọi `POST /extract/url` → chuyển sang Generating |
| Kéo file vào drop zone | Gọi `POST /extract/file` → chuyển sang Generating |
| Click drop zone → chọn file | Như trên |
| Nếu lỗi | Hiện banner đỏ ⚠ + ở lại màn Input |

---

### Màn 3: Generating (`stage = "generating"`)

**Mục đích:** Hiển thị tiến trình AI đang viết kịch bản (streaming).

**Giao diện:**
- Heading "Claude Sonnet đang suy nghĩ..."
- Terminal box: hiển thị live stream JSON từ LLM (cuộn tự động)
- Counter "X ký tự" cập nhật real-time
- Cursor nhấp nháy ở cuối stream

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Xem stream chạy (passive) | — |
| Click **"✕ Huỷ và quay lại"** | Abort request, quay về màn Input |

> ⚠ Thời gian chờ: 20–40 giây tùy độ dài bài và provider LLM.

---

### Màn 4: Preview — Xem & chỉnh kịch bản (`stage = "preview"`)

**Mục đích:** Người dùng review và chỉnh sửa kịch bản trước khi dựng.

**Giao diện:**
- Header: tiêu đề video + button "→ Xem trước HTML"
- **ThemePicker**: 8 theme cards (chọn visual style cho video)
- **VoicePicker**: dropdown chọn giọng ElevenLabs
- **SceneList**: danh sách card cho từng scene
  - Tiêu đề scene, thời lượng, narration, visual description
  - Mỗi card có thể mở rộng để chỉnh sửa

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Chọn theme khác | Cập nhật `scenePlan.theme` |
| Chọn giọng TTS khác | Cập nhật `scenePlan.voiceId` |
| Chỉnh narration / title / imageQuery của scene | Cập nhật scene trong state |
| Click **"→ Xem trước HTML"** | Chuyển sang HtmlPreview (bắt đầu sinh HTML) |
| Click **"← Bắt đầu lại"** (header) | Reset về màn Input |

---

### Màn 5: HtmlPreview — Xem trước trực quan (`stage = "htmlPreview"`)

**Mục đích:** Xem trước composition HTML thực tế, chỉnh sửa từng scene, chọn ảnh.

**Giao diện (3 cột):**

**Cột trái — Danh sách scene:**
- Nút bấm từng scene (01, 02, ...) với tên ngắn và thời lượng
- Chấm màu vàng = scene đã sửa nhưng chưa regen

**Cột giữa — Preview iframe:**
- `ScenePreviewIframe`: render HTML trong `<iframe>` 1920×1080 được scale xuống
- Hiển thị đúng scene đang chọn (seek GSAP timeline)
- Label: "Scene preview · 1920×1080" + "01 / 06"

**Cột phải — Panel chỉnh sửa scene:**
- Field: **Tiêu đề scene** (input)
- Field: **Narration tiếng Việt** (textarea, hiện số ký tự)
- Field: **Ảnh minh họa** (preview ảnh + button "↑ Chọn ảnh")
- Button **"↻ Regen scene"**: gọi `POST /regen-scene` để sinh lại chỉ scene đó

**Phía dưới (full width):**
- **ThemePicker**: đổi theme → regen toàn bộ HTML
- **VoicePicker**: đổi giọng (không cần regen HTML)

**Modal ImagePicker:**
- Tìm kiếm Openverse (`GET /image-search?q=...`)
- Hiển thị grid ảnh CC-license
- Click ảnh → gán vào scene

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Click scene trong cột trái | Đổi active scene, cập nhật preview |
| Chỉnh narration / tiêu đề | Đánh dấu scene "dirty" (chấm vàng) |
| Click "↑ Chọn ảnh" | Mở ImagePicker modal |
| Click ảnh trong ImagePicker | Gán `imageUrl` cho scene |
| Click "↻ Regen scene" | `POST /regen-scene` → cập nhật HTML cho scene đó |
| Chọn theme khác | Clear compositionHtml → trigger regen toàn bộ (tự động) |
| Chọn giọng khác | Cập nhật `voiceId`, không cần regen |
| Click **"🎬 Dựng video MP4 →"** | Chuyển sang màn Build |
| Click "← Quay lại kịch bản" | Quay về màn Preview |

> ℹ Khi lần đầu vào màn này, hệ thống tự động gọi `POST /generate-composition` và hiển thị trạng thái "⚡ AI đang dựng HTML…" + terminal stream.

---

### Màn 6: Build — Dựng video (`stage = "build"`)

**Mục đích:** Chạy toàn bộ pipeline render, theo dõi tiến trình và tải video.

**Giao diện:**

**Header card:**
- Trạng thái: "Chuẩn bị dựng" / "Đang dựng..." / "✓ Video sẵn sàng"
- Tiêu đề video
- Thông tin: N phân cảnh · Xss · 1920×1080 · 30fps · TTS: elevenlabs/gtts
- Timer tổng thời gian dựng (cập nhật live)
- Button: **"🎬 Bắt đầu dựng"** / **"Huỷ"** / **"Dựng lại"**

**Stage grid (2×2):**
| Stage | Icon | Mô tả |
|---|---|---|
| 🎨 Sinh HTML | LLM viết composition + GSAP | Skip nếu đã có từ bước HtmlPreview |
| 💾 Lưu file | Ghi index.html vào project | — |
| 🎙️ Giọng đọc | ElevenLabs / gTTS | 1 scene = 1 file WAV |
| 🎬 Render MP4 | Chromium + FFmpeg | — |

- Mỗi stage card: trạng thái (pending / active 🟠 / done ✓ / error !) + timer riêng

**Terminal streams:**
- `composition.html (live stream)` — màu tím, hiện HTML LLM đang sinh
- `render log` — màu cam, hiện output của `npx hyperframes render`

**Progress bar:** % render (parsed từ log)

**Kết quả (sau khi done):**
- Video player HTML5 (16:9, toàn chiều rộng)
- Button **"⬇ Tải xuống"** (download MP4)
- Button **"↗ Mở tab mới"** (xem trực tiếp)
- Đường dẫn file hệ thống

**Người dùng có thể làm:**
| Hành động | Kết quả |
|---|---|
| Click "🎬 Bắt đầu dựng" | Gọi `POST /build-video` → pipeline SSE chạy |
| Xem stage cards (passive) | Theo dõi từng bước |
| Xem terminal stream (passive) | Debug nếu cần |
| Click "Huỷ" | Abort SSE connection, dừng pipeline |
| Click "⬇ Tải xuống" | Download file MP4 |
| Click "↗ Mở tab mới" | Xem video trong tab mới |
| Click "← Quay lại" | Quay về HtmlPreview |
| Click "🎬 Dựng lại" | Chạy lại pipeline từ đầu |

---

## 6. API Endpoints tổng hợp

| Method | Endpoint | Mô tả | Auth |
|---|---|---|---|
| `POST` | `/extract/url` | Trích xuất nội dung từ URL | Không |
| `POST` | `/extract/file` | Trích xuất nội dung từ file | Không |
| `POST` | `/generate-scenes` | Sinh kịch bản (SSE stream) | Không |
| `POST` | `/generate-composition` | Sinh HTML composition (SSE stream) | Không |
| `POST` | `/regen-scene` | Sinh lại 1 scene trong HTML | Không |
| `POST` | `/build-video` | Build toàn bộ pipeline (SSE stream) | Không |
| `GET` | `/image-search?q=&limit=18` | Tìm ảnh Openverse CC-license | Không |
| `GET` | `/voices/elevenlabs` | Danh sách giọng ElevenLabs | Không |
| `GET` | `/history` | Lịch sử extraction của user | JWT |
| `GET` | `/renders/<file>.mp4` | Serve file MP4 đã render | Không |
| `GET` | `/assets/<file>` | Serve ảnh / audio assets | Không |
| `GET` | `/health` | Health check | Không |

---

## 7. LLM Provider Chain

Hệ thống tự động fallback khi provider hết quota:

```
1. Primary    → Pinkyne proxy (GPT-5.1 / claude-haiku / claude-sonnet)
2. Anthropic  → claude-sonnet-4-6 (direct API)
3. Groq       → llama-3.3-70b-versatile (free tier)
4. Groq-fast  → meta-llama/llama-4-scout-17b (khi Groq 70B hết TPD)
```

Khi fallback sang provider khác, frontend hiển thị banner `[!] Primary LLM hết quota — đã chuyển sang {provider}`.

---

## 8. TTS Chain

```
1. ElevenLabs (primary) — ELEVENLABS_API_KEY cần set
   Model: eleven_multilingual_v2
   Voices: các giọng trong My Voices của tài khoản ElevenLabs
   
2. gTTS (fallback) — Google TTS, ngôn ngữ vi, không cần key
```

---

## 9. Màn đăng nhập (`/login`)

- Xác thực qua Supabase Auth (email/password hoặc OAuth)
- Middleware Next.js kiểm tra session JWT trước khi truy cập `/history`
- Màn chính (`/`) không yêu cầu đăng nhập

---

## 10. Điểm chú ý kỹ thuật

| Vấn đề | Giải pháp |
|---|---|
| GSAP timeline LLM tự viết dùng duration ước tính → sai timing | `patch_html_timing()` strip toàn bộ `<script>` chứa `gsap.timeline`, inject timeline mới với duration thật từ TTS |
| Scene đầu tiên bị đen trước khi timeline seek | `#scene1 { opacity: 1; visibility: visible }` trong BASE_CSS là fallback frame-0 |
| Groq có TPM cap thấp → composition HTML bị cắt | Prompt compact + giảm `GROQ_MAX_SCENES` (env) |
| Windows asyncio không hỗ trợ subprocess → render lỗi | `run_render()` dùng `threading` + `subprocess.Popen` thay vì `asyncio.subprocess` |
| Ảnh từ Openverse có thể bị 403 khi download | `Referer: duckduckgo.com` header khi download |

---

*Tài liệu này mô tả toàn bộ luồng người dùng từ input đến output. Xem thêm:*
- *[01-project-overview.md](./01-project-overview.md) — Tổng quan kiến trúc*
- *[04-frontend-architecture.md](./04-frontend-architecture.md) — Chi tiết Frontend*
- *[05-backend-architecture.md](./05-backend-architecture.md) — Chi tiết Backend*
- *[07-llm-prompts-and-agents.md](./07-llm-prompts-and-agents.md) — System prompts LLM*
