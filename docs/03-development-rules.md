# Quy Tắc Phát Triển (Development Rules)

Tài liệu này liệt kê tất cả các quy tắc bắt buộc khi phát triển dự án TechBeat. Vi phạm bất kỳ quy tắc nào sẽ gây lỗi hoặc kết quả sai.

---

## 📋 Mục Lục Quy Tắc

- [1. Ngôn ngữ & Nội dung](#1-ngôn-ngữ--nội-dung)
- [2. Frontend Rules](#2-frontend-rules)
- [3. Backend Rules](#3-backend-rules)
- [4. HyperFrames Composition Rules](#4-hyperframes-composition-rules)
- [5. GSAP Timeline Rules](#5-gsap-timeline-rules)
- [6. Build Pipeline Rules](#6-build-pipeline-rules)
- [7. SSE Streaming Rules](#7-sse-streaming-rules)
- [8. LLM Prompting Rules](#8-llm-prompting-rules)

---

## 1. Ngôn Ngữ & Nội Dung

### ⚠️ BẮT BUỘC TIẾNG VIỆT
- **TẤT CẢ** text hiển thị trên video (title, subtitle, badge, description, narration) **PHẢI** viết bằng tiếng Việt tự nhiên, có dấu đầy đủ
- **KHÔNG** được dùng tiếng Anh cho narration hay title (trừ tên riêng/thương hiệu)
- `imageQuery` có thể giữ tiếng Anh (vì là search query cho stock photo)
- Chỉ dùng tiếng Anh cho: tên class CSS, comment code, tên biến

### Font tiếng Việt
- Frontend: **Be Vietnam Pro** (Google Fonts) — subset `latin` + `vietnamese`
- Composition: **Be Vietnam Pro** hoặc **Inter** (hỗ trợ dấu tiếng Việt)

---

## 2. Frontend Rules

### Next.js 16 Breaking Changes
> ⚠️ **CẢNH BÁO**: Next.js 16 có nhiều breaking change so với phiên bản cũ. Luôn đọc guide tại `node_modules/next/dist/docs/` trước khi viết code. (Xem `app/AGENTS.md`)

### Tech Stack cố định
- **Next.js 16** + **React 19** + **TypeScript**
- **Tailwind CSS v4** (qua `@tailwindcss/postcss`, KHÔNG phải v3)
- Path alias: `@/*` → `./*`
- Target: `ES2017`

### Design System (globals.css)
- **Bảng màu chủ đạo**: Cam ấm (orange)
  - Background: `#fff7ed` (kem nhạt)
  - Primary: `#f97316` (orange-500)
  - Text: `#1c1917` (stone-900)
- **Pattern classes** (PHẢI dùng, KHÔNG viết inline):
  - `.glass` / `.glass-strong` — Glassmorphism card
  - `.btn-glow` — Button gradient cam + glow shadow
  - `.gradient-text` — Animated gradient text
  - `.mesh-bg` — Animated mesh gradient background
  - `.shimmer` — Loading skeleton
  - `.fade-up` — Entry animation
  - `.pulse-ring` — Active indicator

### Component conventions
- Tất cả component đều là `"use client"` (client-side rendering)
- API URL lấy từ `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`
- Sử dụng `AbortController` cho mọi API call có thể cancel
- Error messages hiển thị bằng tiếng Việt

---

## 3. Backend Rules

### FastAPI conventions
- CORS cho phép: `http://localhost:3000`, `http://localhost:3001`
- Tất cả streaming endpoint trả về `StreamingResponse` với `media_type="text/event-stream"`
- Headers bắt buộc cho SSE: `Cache-Control: no-cache`, `X-Accel-Buffering: no`

### LLM Client (`routers/llm.py`)
- Sử dụng **OpenAI-compatible SDK** (`openai` package)
- Client là **singleton** (khởi tạo 1 lần, tái sử dụng)
- Base URL và model đều config qua env vars
- **KHÔNG hardcode API key hay model name trong code**

### Static file serving
- `my-video/renders/` mount tại `/renders` trên FastAPI
- `my-video/assets/` mount tại `/assets` trên FastAPI
- Project path config qua `HYPERFRAMES_PROJECT` env var

### Extract text limits
- Tất cả extractors **giới hạn 20,000 ký tự** text trả về (`text[:20000]`)

---

## 4. HyperFrames Composition Rules

### ⚠️ QUY TẮC BẤT BIẾN (vi phạm = composition hỏng)

#### 4.1 Cấu trúc root
```html
<div id="root"
     data-composition-id="main"
     data-start="0"
     data-width="1920"
     data-height="1080"
     data-duration="{TOTAL_SECONDS}">
```

#### 4.2 Scene layout
- Mỗi scene là `<div class="scene" id="sceneN">` (N = 1, 2, 3...)
- `position: absolute`, `width: 100%`, `height: 100%`
- Ban đầu: `opacity: 0`, `visibility: hidden`
- Layout: Grid 2 cột (info-col + visual-col), gap 80px, max-width 1600px, padding 60px

#### 4.3 Thành phần bắt buộc mỗi scene
- **scene-badge**: "Phần N" (tiếng Việt)
- **scene-title**: h1 4.5rem
- **scene-subtitle**: h2 2.2rem màu cam
- **scene-description**: p 1.3rem
- **visual-col**: Mock visual hoặc `<img>` nếu có ảnh minh họa

#### 4.4 Audio narration (bắt buộc)
```html
<audio id="vN" src="assets/pN.wav"
       data-start="{start}" data-duration="{duration}" data-volume="1">
</audio>
```
Đặt **sau cùng** trong div root, ngay trước `</div>` đóng root.

#### 4.5 CẤM TUYỆT ĐỐI
- ❌ `setTimeout` / `setInterval`
- ❌ `requestAnimationFrame`
- ❌ `Date.now()` / `Math.random()`
- ❌ `fetch` / network request ngoài
- ❌ Bất kỳ logic bất đồng bộ không deterministic

> **Lý do**: HyperFrames render bằng cách tua timeline từng frame. Mọi thứ bất đồng bộ sẽ không hoạt động khi render.

#### 4.6 CDN Dependencies
- GSAP: `https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js`
- Font: Google Fonts (Be Vietnam Pro / Inter)

---

## 5. GSAP Timeline Rules

### 5.1 Timeline phải paused
```javascript
const tl = gsap.timeline({ paused: true });
```

### 5.2 PHẢI đăng ký trên window
```javascript
window.__timelines = window.__timelines || {};
window.__timelines["main"] = tl;
```
> **Thiếu dòng này = render ra video trống.** Backend validate bằng check `"window.__timelines" in html`.

### 5.3 Scene timing pattern
```javascript
// Mỗi scene: fade in → content animation → fade out → hide
tl.set("#sceneN", { opacity: 0, visibility: "visible" }, start);
tl.to("#sceneN", { opacity: 1, duration: 0.6, ease: "power3.out" }, start);
// ... animate content ...
tl.to("#sceneN", { opacity: 0, duration: 0.5, ease: "power2.in" }, start + duration - 0.6);
tl.set("#sceneN", { visibility: "hidden" }, start + duration);
```

### 5.4 Ease đa dạng
Sử dụng nhiều loại ease khác nhau cho animation phong phú:
- `back.out(1.7)` — badge
- `power4.out` — title
- `power3.out` — subtitle
- `power2.out` — description
- `elastic.out` — accent elements

---

## 6. Build Pipeline Rules

### 6.1 Pipeline stages (theo thứ tự)

| # | Stage | Event key | Mô tả |
|---|---|---|---|
| 0 | Download ảnh | (internal) | Tải ảnh minh họa đã chọn về `assets/` |
| 1 | Composition | `composition` | LLM sinh HTML |
| 2 | Save | `save` | Ghi `index.html` |
| 3 | TTS | `tts` | Google TTS → `assets/pN.wav` |
| 4 | Render | `render` | `npx hyperframes render` → MP4 |

### 6.2 TTS Timing Sync
Sau khi TTS sinh audio, pipeline **PHẢI** patch HTML:
1. Đo duration thực tế từng audio file (pydub)
2. Tính lại `data-start` và `data-duration` cho `<audio>` tags
3. Patch `data-duration` trên root div
4. **Inject JS script** rebuild GSAP timeline với timing mới

> **Lý do**: Duration TTS thực tế khác với duration dự kiến trong kịch bản. Nếu không patch, video sẽ bị lệch tiếng.

### 6.3 Buffer rule
Mỗi scene: `ceil(audio_duration) + 1 giây` buffer cho breathing room.

### 6.4 Render execution (Windows)
- Trên Windows: dùng `npx.cmd` (không phải `npx`)
- Render chạy qua `subprocess.Popen` trong thread riêng (tránh asyncio event loop conflict trên Windows)
- Log từ subprocess được đẩy qua `asyncio.Queue` về SSE stream

---

## 7. SSE Streaming Rules

### 7.1 Format chung
```
data: {"type":"chunk","text":"..."}\n\n
data: {"type":"done","scenePlan":{...}}\n\n
data: {"type":"error","message":"..."}\n\n
```

### 7.2 Event types theo endpoint

#### `/generate-scenes`:
- `chunk` → `{type: "chunk", text: "..."}` — streaming text
- `done` → `{type: "done", scenePlan: {...}}` — kết quả cuối
- `error` → `{type: "error", message: "..."}`

#### `/generate-composition`:
- `chunk` → `{type: "chunk", text: "..."}` — streaming HTML
- `done` → `{type: "done", html: "..."}` — HTML hoàn chỉnh
- `error` → `{type: "error", message: "..."}`

#### `/build-video`:
- `stage` → `{type: "stage", stage: "...", status: "start|progress|done|skipped|log", ...}`
- `done` → `{type: "done", videoUrl: "/renders/...", videoPath: "..."}`
- `error` → `{type: "error", stage: "...", message: "...", log: "..."}`

### 7.3 Frontend SSE parsing pattern
```javascript
// Split buffer by \n\n, parse "data: " prefix
const split = buf.split("\n\n");
buf = split.pop() ?? "";
for (const line of split) {
  if (!line.startsWith("data: ")) continue;
  const event = JSON.parse(line.slice(6));
  // handle event...
}
```

---

## 8. LLM Prompting Rules

### 8.1 Scene generation prompt
- System prompt bắt buộc tiếng Việt
- Output: **JSON thuần** (không markdown fence, không giải thích)
- Temperature: `0.7`
- Scene count: 4-8 scene
- Scene duration: 8-20 giây

### 8.2 Composition generation prompt
- System prompt chỉ định chi tiết: cấu trúc HTML, style, animation
- Temperature: `0.6`
- `max_tokens: 32000`
- Output: **HTML thuần** từ `<!doctype html>` đến `</html>` (không markdown fence)
- Backend validate:
  1. Phải có `<html` tag
  2. Phải có `</html>` closing tag
  3. Phải có `window.__timelines` registration

### 8.3 Prompt includes image assets
Khi scene có ảnh đã tải về:
```
IllustrationImage: assets/scene1.jpg  ← BẮT BUỘC dùng <img src="assets/scene1.jpg"> trong visual-col
```

---

## 9. Git & Development Rules

### 9.1 Gitignore quan trọng
- `node_modules/` — tất cả
- `.next/` — Next.js build cache
- `.env*` — secrets
- `my-video/renders/` — output MP4
- `my-video/.thumbnails/` / `.waveform-cache/` — HyperFrames cache
- `.agents/` / `.claude/` / `.gemini/` — AI agent configs

### 9.2 Agent skills
- Skills cài từ `heygen-com/hyperframes` repo
- Lock file: `skills-lock.json` (commit vào git)
- Skills path: `.agents/skills/`
- **PHẢI đọc skill SKILL.md trước khi sử dụng patterns liên quan**
