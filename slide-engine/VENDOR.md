# Vendor provenance

Code trong `vendor/` được bê **nguyên vẹn (byte-identical)** từ dự án
[arcsin1/oh-my-ppt](https://github.com/arcsin1/oh-my-ppt) — Apache-2.0.

- **Commit pin:** `0159edf66f51eec9cf85ab2bfe16b2da40c355e4` (2026-06-28)
- **Cách lấy:** `git clone --depth 1 https://github.com/arcsin1/oh-my-ppt.git` tại repo root
  (thư mục `oh-my-ppt/` chỉ là bản tham chiếu, KHÔNG commit vào repo này).

## Quy tắc

1. File trong `vendor/` **không được sửa** — giữ 100% luồng oh-my-ppt.
   Cây thư mục mirror đúng `oh-my-ppt/src/` (ví dụ `vendor/main/utils/html-pptx/`
   ↔ `src/main/utils/html-pptx/`) để mọi import tương đối giữ nguyên.
2. Điểm thay thế duy nhất được phép: các module dính Electron, đặt ở `src/`:
   - `src/renderer-playwright.ts` thay `src/main/utils/html-pptx/renderer.ts`
     (BrowserWindow → Playwright Chromium; port 1:1 từng bước).
   - `shims/electron-log/` thay package `electron-log` (console shim, cùng API).
3. Nâng cấp vendor = clone lại đúng commit mới, copy đè, cập nhật commit pin ở đây.

## Đã vendor

| Đường dẫn vendor | Nguồn oh-my-ppt | Ghi chú |
|---|---|---|
| `vendor/main/utils/html-pptx/*.ts` (7 file, trừ renderer.ts) | `src/main/utils/html-pptx/` | Pipeline HTML → PPTX (extract + OOXML writer + fonts) |
| `vendor/main/animation/pptx-animation-map.ts` | `src/main/animation/` | Map animation → PPTX |
| `vendor/main/animation/data-anim-schema.ts` | `src/main/animation/` | Schema animation |
