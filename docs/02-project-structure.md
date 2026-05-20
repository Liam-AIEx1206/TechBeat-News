# Cấu Trúc Thư Mục & Mã Nguồn Chi Tiết

---

## 📂 Cây Thư Mục Tổng Thể

```
D:\AI_Video_Edit\
│
├── app/                          # ── FRONTEND (Next.js 16 + React 19) ──
│   ├── app/                      # Next.js App Router
│   │   ├── layout.tsx            # Root layout: font, metadata, mesh background
│   │   ├── page.tsx              # Trang chính: state machine 4 stage (input → generating → preview → build)
│   │   ├── globals.css           # Design system: mesh-bg, glass, btn-glow, gradient-text, shimmer, fade-up
│   │   └── favicon.ico
│   ├── components/
│   │   ├── InputPanel.tsx        # Form nhập URL hoặc upload file
│   │   ├── SceneList.tsx         # Container danh sách scene, CRUD operations
│   │   ├── SceneCard.tsx         # Card hiển thị/sửa 1 scene + chọn ảnh
│   │   ├── ImagePicker.tsx       # Modal tìm & chọn ảnh từ DuckDuckGo
│   │   ├── VideoBuilder.tsx      # Orchestrator 4-stage build pipeline UI
│   │   └── CompositionGenerator.tsx  # (Legacy) Standalone composition generator
│   ├── types/
│   │   └── scene.ts              # TypeScript interfaces: Scene, ScenePlan, ExtractedContent
│   ├── public/                   # Static assets (SVG icons)
│   ├── package.json              # Dependencies: next, react, @anthropic-ai/sdk, cheerio, pdf-parse, officeparser
│   ├── next.config.ts            # serverExternalPackages: pdf-parse, officeparser
│   ├── postcss.config.mjs        # Tailwind v4 via @tailwindcss/postcss
│   ├── tsconfig.json             # Target ES2017, path alias @/* → ./*
│   └── .env.local.example
│
├── backend/                      # ── BACKEND (FastAPI + Python) ──
│   ├── main.py                   # FastAPI app: CORS, routers, static file serving
│   ├── requirements.txt          # Dependencies: fastapi, openai, gTTS, pydub, PyMuPDF, httpx, ...
│   ├── routers/
│   │   ├── llm.py                # OpenAI client singleton + model selector
│   │   ├── extract.py            # POST /extract/url, POST /extract/file
│   │   ├── scenes.py             # POST /generate-scenes (SSE streaming)
│   │   ├── compositions.py       # POST /generate-composition (SSE), POST /save-composition
│   │   ├── build.py              # POST /build-video (SSE, full pipeline orchestrator)
│   │   └── images.py             # GET /image-search (DuckDuckGo scraping)
│   ├── extractors/
│   │   ├── url.py                # BeautifulSoup URL extraction
│   │   ├── pdf.py                # OCR (LLM vision) + pypdf fallback
│   │   ├── ocr.py                # Vision LLM OCR: render PDF → PNG → multimodal request
│   │   └── office.py             # python-docx, python-pptx extractors
│   └── .env.example
│
├── my-video/                     # ── HYPERFRAMES VIDEO PROJECT ──
│   ├── index.html                # Main composition (43KB, auto-generated bởi pipeline)
│   ├── hyperframes.json          # HyperFrames config: registry, paths
│   ├── package.json              # Scripts: dev (preview), check (lint), render, publish
│   ├── meta.json                 # Project metadata
│   ├── assets/                   # Media assets: ảnh minh họa, audio TTS (pN.wav)
│   ├── renders/                  # Output MP4 files
│   ├── docs/                     # Pipeline documentation
│   ├── AGENTS.md                 # AI Agent rules cho HyperFrames
│   └── CLAUDE.md                 # Claude-specific rules cho HyperFrames
│
├── .agents/skills/               # ── AI AGENT SKILLS ──
│   ├── hyperframes/              # Core HyperFrames patterns
│   ├── hyperframes-cli/          # CLI dev loop patterns
│   ├── hyperframes-media/        # TTS, transcribe, bg-removal
│   ├── gsap/                     # GSAP animation patterns
│   ├── css-animations/           # CSS keyframe patterns
│   ├── tailwind/                 # Tailwind v4 patterns
│   ├── three/                    # Three.js patterns
│   ├── lottie/                   # Lottie animation patterns
│   └── ...                       # 15+ skills total
│
├── docs/                         # ── TÀI LIỆU DỰ ÁN (thư mục này) ──
├── skills-lock.json              # Lock file cho agent skills
└── .gitignore
```

---

## 🗃️ Chi Tiết Từng Module

### Frontend (`app/`)

#### State Machine chính (`page.tsx`)
Trang chính hoạt động theo mô hình **state machine** với 4 trạng thái:

```
input → generating → preview → build
```

| Stage | Mô tả | Component chính |
|---|---|---|
| `input` | Người dùng nhập URL hoặc upload file | `InputPanel` |
| `generating` | AI đang viết kịch bản (SSE stream) | Spinner + stream buffer |
| `preview` | Xem & chỉnh sửa kịch bản scene | `SceneList` → `SceneCard` |
| `build` | Dựng video 4 bước tự động | `VideoBuilder` |

#### Components

| Component | File | Chức năng |
|---|---|---|
| `InputPanel` | `components/InputPanel.tsx` | URL input + file drag-drop upload |
| `SceneList` | `components/SceneList.tsx` | CRUD scene: add, delete, reorder, update |
| `SceneCard` | `components/SceneCard.tsx` | Display/edit mode cho 1 scene, tích hợp ImagePicker |
| `ImagePicker` | `components/ImagePicker.tsx` | Modal overlay: search ảnh DuckDuckGo, grid preview, click-to-pick |
| `VideoBuilder` | `components/VideoBuilder.tsx` | 4-stage pipeline UI: composition → save → TTS → render |
| `CompositionGenerator` | `components/CompositionGenerator.tsx` | (Legacy) Standalone HTML generator, không dùng trong flow chính |

#### Types (`types/scene.ts`)

```typescript
interface Scene {
  id: string;
  index: number;
  title: string;           // Tiếng Việt
  narration: string;        // Lời dẫn tiếng Việt
  visualDescription: string;// Mô tả hình ảnh
  duration: number;         // Giây
  imageQuery?: string;      // English search query
  imageUrl?: string;        // URL ảnh đã chọn
}

interface ScenePlan {
  title: string;
  scenes: Scene[];
  totalDuration: number;
}

interface ExtractedContent {
  title: string;
  text: string;
  source: string;
}
```

---

### Backend (`backend/`)

#### API Endpoints

| Method | Path | Router | Mô tả |
|---|---|---|---|
| `POST` | `/extract/url` | `extract.py` | Trích xuất nội dung từ URL (BeautifulSoup) |
| `POST` | `/extract/file` | `extract.py` | Trích xuất nội dung từ file upload (PDF/DOCX/PPTX) |
| `POST` | `/generate-scenes` | `scenes.py` | SSE stream: LLM sinh ScenePlan JSON |
| `POST` | `/generate-composition` | `compositions.py` | SSE stream: LLM sinh HTML composition |
| `POST` | `/save-composition` | `compositions.py` | Ghi HTML vào my-video/index.html |
| `POST` | `/build-video` | `build.py` | SSE stream: Full build pipeline (composition + save + TTS + render) |
| `GET` | `/image-search` | `images.py` | DuckDuckGo image search API |
| `GET` | `/health` | `main.py` | Health check |

#### Extractors

| Extractor | File | Công nghệ |
|---|---|---|
| URL | `extractors/url.py` | httpx + BeautifulSoup |
| PDF | `extractors/pdf.py` | OCR (LLM vision via PyMuPDF render) + pypdf fallback |
| OCR | `extractors/ocr.py` | PyMuPDF rasterize → base64 → multimodal LLM call |
| DOCX | `extractors/office.py` | python-docx |
| PPTX | `extractors/office.py` | python-pptx |

#### LLM Configuration (`routers/llm.py`)

- Sử dụng **OpenAI-compatible API** (qua base URL tuỳ chỉnh)
- Hỗ trợ nhiều model cho các task khác nhau:
  - `OPENAI_SCENES_MODEL`: Sinh kịch bản (default: GPT-5.1)
  - `OPENAI_COMPOSITION_MODEL`: Sinh HTML (default: Claude Sonnet 4.6)
  - `OPENAI_OCR_MODEL`: OCR PDF (default: Claude Sonnet 4.6)

---

### Video Project (`my-video/`)

| File/Thư mục | Vai trò |
|---|---|
| `index.html` | Main composition — được auto-generate bởi build pipeline |
| `hyperframes.json` | Config HyperFrames: registry URL, paths |
| `package.json` | Scripts: `dev` (preview), `check` (lint), `render` (MP4) |
| `meta.json` | Project metadata (id, name, createdAt) |
| `assets/` | Ảnh minh họa (sceneN.jpg), audio TTS (pN.wav, vN.wav) |
| `renders/` | Output MP4 files (gitignored) |
| `AGENTS.md` | Rules cho AI agents khi làm việc với HyperFrames |
| `CLAUDE.md` | Rules chi tiết cho Claude Code agent |
