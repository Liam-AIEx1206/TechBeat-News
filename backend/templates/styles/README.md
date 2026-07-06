# Style packs — chọn phong cách thay vì chọn màu

Mỗi style là **một thư mục** ở đây: `backend/templates/styles/<style-id>/` gồm
đúng 3 file theo format của [oh-my-ppt](https://github.com/arcsin1/oh-my-ppt)
(Apache-2.0):

```
styles/
  cyberpunk-neon/
    style.json      # metadata: label, labelEn, description, category, aliases…
    SKILL.md        # đặc tả thiết kế cho AI (màu, font, hoạ tiết, layout) — LINH HỒN của style
    preview.html    # demo 16:9 inline-CSS — dùng làm thumbnail chọn style
  japanese-minimal/
    ...
```

## Cách thêm style từ oh-my-ppt (bạn clone repo họ về)

1. `git clone https://github.com/arcsin1/oh-my-ppt` (hoặc dùng bản build).
2. Tìm thư mục chứa style — thường ở `resources/styles/` hoặc do tool
   `arcsin1/style-generate-skill` sinh ra (mỗi style là 1 folder 3 file).
3. **Copy nguyên thư mục style** (giữ đủ `style.json` + `SKILL.md` + `preview.html`)
   vào đây, mỗi style một thư mục con. Tên thư mục = `style-id`.
4. Restart backend (hoặc chỉ cần đổi file — loader cache theo mtime, tự nạp lại).

Không cần chỉnh gì thêm: loader đọc khoan dung, `/styles` tự liệt kê, StylePicker
tự hiện thumbnail từ `preview.html`.

## Loader hiểu gì từ mỗi file

- **style.json**: lấy `label / labelEn / description / category / aliases`. Nếu có
  field `palette`/`colors`/`theme` dạng `{bg, accent, text1, …}` thì dùng luôn.
- **SKILL.md**: đọc nguyên văn, chèn vào prompt sinh slide làm design-spec chính.
  Màu/font/hoạ tiết AI bám theo đây.
- **preview.html**: render làm thumbnail trong màn chọn style.
- **Palette cho reference SVG**: nếu style.json không khai báo palette, loader tự
  trích mã hex trong SKILL.md và suy `bg/accent/text…` (tối→nền, sáng→chữ,
  bão hoà→accent). Đây chỉ là gần đúng cho phần token màu; nguồn màu chính xác
  vẫn là prose trong SKILL.md mà AI đọc.

## Tự viết style mới

Giữ đúng 3 file như trên. Tối thiểu cần `SKILL.md` (mô tả phong cách) — `style.json`
và `preview.html` khuyến nghị có để hiện đẹp trong picker.
