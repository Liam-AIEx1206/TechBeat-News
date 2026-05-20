# LLM Prompts & AI Agent Context

Tài liệu này ghi lại toàn bộ system prompts đang dùng trong dự án và các nguyên tắc khi thay đổi chúng.

---

## 📝 System Prompts

### 1. Scene Generation Prompt (`routers/scenes.py`)

**Mục đích**: Biến nội dung text thành kịch bản video (ScenePlan JSON).

**Model**: `OPENAI_SCENES_MODEL` (default: `gpt-5.1`)
**Temperature**: `0.7`

```
Bạn là chuyên gia viết kịch bản video tiếng Việt và chiến lược nội dung.
Phân tích nội dung được cung cấp và tạo kế hoạch scene video có cấu trúc.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT
- TẤT CẢ trường text (title, narration, visualDescription) PHẢI viết bằng tiếng Việt tự nhiên, có dấu đầy đủ
- KHÔNG được dùng tiếng Anh cho narration hay title (trừ khi là tên riêng/thương hiệu)
- imageQuery có thể giữ tiếng Anh vì đó là search query

Quy tắc:
- Trích xuất những điểm quan trọng và hấp dẫn nhất
- Tạo 4-8 scene tùy độ dài và phức tạp của nội dung
- Mỗi scene 8-20 giây (ngắn gọn, súc tích)
- Narration rõ ràng, hấp dẫn, gần gũi — là những gì người dẫn thực sự nói bằng tiếng Việt
- Visual description cụ thể tiếng Việt: mô tả text overlay, hình ảnh, animation xuất hiện
- imageQuery là query tìm kiếm ảnh stock cụ thể (2-5 từ tiếng Anh)

Chỉ trả về JSON hợp lệ, không có markdown fence, không giải thích ngoài JSON.
```

**Output format**:
```json
{
  "title": "Tiêu đề video bằng tiếng Việt",
  "scenes": [
    {
      "id": "scene-1",
      "index": 0,
      "title": "Tiêu đề scene tiếng Việt",
      "narration": "Người dẫn đọc đoạn này bằng tiếng Việt",
      "visualDescription": "Mô tả tiếng Việt những gì hiển thị trên màn hình",
      "duration": 12,
      "imageQuery": "english stock photo query"
    }
  ],
  "totalDuration": 90
}
```

---

### 2. Composition Generation Prompt (`routers/compositions.py`)

**Mục đích**: Biến ScenePlan JSON thành file HTML HyperFrames hoàn chỉnh.

**Model**: `OPENAI_COMPOSITION_MODEL` (default: `claude-sonnet-4-6`)
**Temperature**: `0.6`
**Max tokens**: `32,000`

```
Bạn là chuyên gia tạo composition HyperFrames (HTML5 + GSAP). Nhiệm vụ: từ scene plan đã cho, 
sinh ra một file `index.html` HOÀN CHỈNH theo đúng tiêu chuẩn HyperFrames.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT
[... chi tiết quy tắc ngôn ngữ ...]

QUY TẮC BẤT BIẾN (vi phạm = composition hỏng):

1. Cấu trúc root: <div id="root" data-composition-id="main" ...>
2. Mỗi scene: position absolute, opacity 0, visibility hidden ban đầu
3. KHÔNG dùng: setTimeout, setInterval, requestAnimationFrame, Date.now(), Math.random(), fetch
4. Timeline GSAP: paused: true, đăng ký window.__timelines["main"]
5. Audio narration: <audio id="vN" src="assets/pN.wav" data-start/data-duration/data-volume>
6. Font: Be Vietnam Pro / Inter từ Google Fonts, GSAP từ CDN
7. Style: nền cam ấm (#1a0f08 → #2d1810), accent #f97316/#fb923c
8. Layout: grid 2 cột, gap 80px, max-width 1600px, padding 60px
9. Mỗi scene: badge + title + subtitle + description + visual
10. Animation đa dạng: back.out, elastic.out, power3/4.out, stagger

OUTPUT: DUY NHẤT mã HTML từ <!doctype html> đến </html>. KHÔNG markdown fence.
```

**User prompt builder** (`build_user_prompt()`):
```
Tiêu đề video: {title}
Tổng thời lượng: {totalDuration} giây
Số scene: {len(scenes)}

Danh sách scene (đã có start time tích luỹ):

[Scene 1] start=0s, duration=12s, end=12s
  Title: {title}
  Narration: {narration}
  Visual: {visualDescription}
  ImageQuery: {imageQuery}
  IllustrationImage: assets/scene1.jpg  ← BẮT BUỘC dùng <img>  // (nếu có)
```

---

### 3. OCR Prompt (`extractors/ocr.py`)

**Mục đích**: Transcribe PDF pages (rendered as images) thành text.

**Model**: `OPENAI_OCR_MODEL` hoặc `OPENAI_COMPOSITION_MODEL` (default: `claude-sonnet-4-6`)
**Temperature**: `0.1` (thấp, faithful transcription)
**Max tokens**: `8,000`

```
Transcribe every page in reading order as Markdown.
Preserve headings, lists, tables, and obvious paragraph breaks.
Do not add commentary, do not summarize. Output only the transcribed text.
```

Input: Text prompt + base64 PNG images of each PDF page.

---

## 🤖 AI Agent Rules

### Từ `my-video/AGENTS.md`:
1. Đọc skill SKILL.md trước khi viết composition
2. Mọi timed element cần `data-start`, `data-duration`, `data-track-index`
3. Visible timed elements **PHẢI** có `class="clip"`
4. GSAP timelines **PHẢI** paused + registered trên `window.__timelines`
5. Videos dùng `muted` + `<audio>` riêng
6. Sub-compositions dùng `data-composition-src`
7. Chỉ logic deterministic

### Từ `my-video/CLAUDE.md`:
- **LUÔN** invoke relevant skill trước khi viết compositions
- `npm run dev` là long-running server — **LUÔN** chạy background
- `npm run check` **PHẢI** chạy sau mỗi thay đổi HTML
- Fix tất cả errors trước khi present kết quả

### Từ `app/AGENTS.md`:
- Next.js 16 có breaking changes — đọc docs tại `node_modules/next/dist/docs/`

---

## 🔑 Nguyên Tắc Khi Chỉnh Sửa Prompts

### DO:
- ✅ Giữ format output rõ ràng (JSON cho scenes, HTML cho composition)
- ✅ Explicit về ngôn ngữ yêu cầu (tiếng Việt bắt buộc)
- ✅ Liệt kê CẤM cụ thể (setTimeout, Math.random, etc.)
- ✅ Cho ví dụ cụ thể trong prompt
- ✅ Validate output phía backend (check HTML tags, window.__timelines)

### DON'T:
- ❌ Cho phép markdown fence trong output (gây parse error)
- ❌ Để model tự quyết ngôn ngữ (sẽ output tiếng Anh)
- ❌ Bỏ qua validation `</html>` closing tag (HTML bị cắt giữa chừng)
- ❌ Quên `window.__timelines` validation (render ra video trống)
- ❌ Hardcode model name trong prompt (dùng env var thay thế)

---

## 📊 Model Selection Strategy

| Task | Yêu cầu | Model gợi ý | Lý do |
|---|---|---|---|
| Scene planning | Phân tích nội dung, viết narration VN | GPT-5.1 | Giỏi tiếng Việt, fast |
| HTML composition | Sinh code HTML+CSS+JS dài | Claude Sonnet 4.6 | Code generation xuất sắc, context dài |
| OCR | Vision + text extraction | Claude Sonnet 4.6 | Multimodal mạnh |

> **Lưu ý**: Tất cả model đều gọi qua OpenAI-compatible API (pinkyne.com proxy). Có thể swap model bất kỳ lúc nào qua env vars mà không sửa code.
