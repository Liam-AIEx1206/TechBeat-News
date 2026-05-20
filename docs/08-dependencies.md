# Dependency Map & Tech Stack

Tài liệu này liệt kê toàn bộ dependencies, versions, và vai trò của chúng trong dự án.

---

## 📦 Frontend Dependencies (`app/package.json`)

### Production Dependencies

| Package | Version | Vai trò |
|---|---|---|
| `next` | `16.2.6` | React framework, App Router, SSR |
| `react` | `19.2.4` | UI library |
| `react-dom` | `19.2.4` | React DOM renderer |
| `@anthropic-ai/sdk` | `^0.96.0` | Anthropic Claude SDK (có thể dùng cho client-side calls) |
| `cheerio` | `^1.2.0` | Server-side HTML parsing (có thể dùng trong API routes) |
| `officeparser` | `^7.0.3` | Parse Office docs (có thể dùng trong API routes) |
| `pdf-parse` | `^2.4.5` | PDF text extraction (có thể dùng trong API routes) |

### Dev Dependencies

| Package | Version | Vai trò |
|---|---|---|
| `tailwindcss` | `^4` | CSS framework (v4, CSS-first config) |
| `@tailwindcss/postcss` | `^4` | PostCSS plugin cho Tailwind v4 |
| `typescript` | `^5` | Type checker |
| `@types/node` | `^20.19.41` | Node.js types |
| `@types/react` | `^19` | React types |
| `@types/react-dom` | `^19` | React DOM types |
| `@types/pdf-parse` | `^1.1.5` | pdf-parse types |

### Config Notes
- `next.config.ts`: `serverExternalPackages: ["pdf-parse", "officeparser"]` — cần thiết để Node.js binary modules hoạt động trong Next.js
- `postcss.config.mjs`: chỉ dùng `@tailwindcss/postcss` (Tailwind v4 CSS-first approach)

---

## 🐍 Backend Dependencies (`backend/requirements.txt`)

| Package | Version | Vai trò |
|---|---|---|
| `fastapi` | `0.115.6` | Web framework |
| `uvicorn[standard]` | `0.32.1` | ASGI server |
| `openai` | `>=1.54.0` | OpenAI-compatible API client (dùng cho tất cả LLM calls) |
| `gTTS` | `>=2.5.0` | Google Text-to-Speech (tiếng Việt) |
| `pydub` | `>=0.25.1` | Audio processing (MP3→WAV conversion, duration measurement) |
| `PyMuPDF` | `>=1.24.0` | PDF rasterization (alias: `fitz`) — render PDF pages thành PNG cho OCR |
| `httpx` | `0.28.1` | Async HTTP client (URL extraction, image download, DuckDuckGo search) |
| `beautifulsoup4` | `4.12.3` | HTML parsing (URL content extraction) |
| `pypdf` | `5.1.0` | PDF text extraction (fallback khi OCR fail) |
| `python-docx` | `1.1.2` | DOCX file reading |
| `python-pptx` | `1.0.2` | PPTX file reading |
| `python-multipart` | `0.0.20` | File upload handling (FastAPI requirement) |
| `python-dotenv` | `1.0.1` | Load .env files |

### System Requirements (không trong requirements.txt)
| Tool | Vai trò | Cài đặt |
|---|---|---|
| `FFmpeg` | Audio/video encoding | System install required |
| `Chrome/Chromium` | Headless render | System install required |
| `Node.js 18+` | npx hyperframes render | System install required |

---

## 🎬 HyperFrames Dependencies (`my-video/package.json`)

| Package | Version | Vai trò |
|---|---|---|
| `hyperframes` | `0.6.20` | Video framework (dùng qua `npx --yes hyperframes@0.6.20`) |

### CDN Dependencies (trong composition HTML)
| Library | CDN URL | Vai trò |
|---|---|---|
| GSAP | `https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js` | Animation engine |
| Be Vietnam Pro | Google Fonts | Vietnamese font |
| Inter | Google Fonts | Alternative font |

---

## 🤖 Agent Skills (`skills-lock.json`)

Tất cả skills từ `heygen-com/hyperframes` repository:

| Skill | Mô tả |
|---|---|
| `hyperframes` | Core composition patterns |
| `hyperframes-cli` | CLI dev loop: init, lint, preview, render |
| `hyperframes-media` | TTS (Kokoro), transcribe (Whisper), bg-removal |
| `hyperframes-registry` | Install blocks/components |
| `gsap` | GSAP animation patterns |
| `css-animations` | CSS keyframe patterns |
| `tailwind` | Tailwind v4 patterns |
| `animejs` | Anime.js patterns |
| `lottie` | Lottie animation patterns |
| `three` | Three.js patterns |
| `typegpu` | WebGPU patterns |
| `waapi` | Web Animations API patterns |
| `website-to-hyperframes` | URL → video pipeline |
| `remotion-to-hyperframes` | Remotion → HyperFrames migration |
| `contribute-catalog` | Contribute to registry |

---

## 🔗 External Services

| Service | Mục đích | Auth |
|---|---|---|
| `api.pinkyne.com/v1` | LLM API (OpenAI-compatible proxy) | API key required |
| Google Fonts | Font loading | No auth |
| Google TTS (gTTS) | Vietnamese text-to-speech | No auth (free, rate-limited) |
| DuckDuckGo | Image search | No auth (scraping) |
| jsDelivr CDN | GSAP library hosting | No auth |
| HyperFrames registry | Block/component registry | No auth |

---

## ⚠️ Known Constraints

1. **gTTS rate limiting**: Google TTS miễn phí nhưng có thể bị rate limit khi gọi nhiều. Không có retry logic hiện tại.
2. **DuckDuckGo vqd token**: Có thể thay đổi format bất cứ lúc nào (scraping, không phải official API). Cần monitor.
3. **PyMuPDF import**: Lazy import (`import fitz`) — server vẫn start được nếu chưa cài PyMuPDF, nhưng PDF OCR sẽ fail.
4. **pydub FFmpeg dependency**: pydub cần FFmpeg binary để convert audio. Nếu không có FFmpeg, TTS fallback sang giữ MP3 (HyperFrames chấp nhận).
5. **Windows asyncio**: Uvicorn trên Windows dùng selector event loop → không dùng được `asyncio.create_subprocess_exec`. Render phải chạy qua `subprocess.Popen` + threading.
6. **HyperFrames version pinned**: `0.6.20` — hardcoded trong cả `package.json` và `build.py`. Upgrade cần sửa cả hai nơi.
