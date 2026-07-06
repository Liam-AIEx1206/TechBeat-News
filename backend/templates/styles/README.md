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

Đã xác nhận: oh-my-ppt để 74 style ở `resources/styles/<tên>/`, mỗi style đúng
3 file `style.json` + `SKILL.md` + `preview.html`.

```powershell
git clone https://github.com/arcsin1/oh-my-ppt.git D:\oh-my-ppt
# copy TẤT CẢ 74 style vào app (mỗi style giữ nguyên thư mục 3 file)
Copy-Item "D:\oh-my-ppt\resources\styles\*" -Destination "D:\AI_Video_Edit\backend\templates\styles\" -Recurse
```

Restart backend là xong (loader cache theo mtime nên đổi/thêm file tự nạp lại).

**Lưu ý:** `SKILL.md` của oh-my-ppt viết bằng tiếng Trung — KHÔNG sao. Model đọc
hiểu spec (màu/typography/layout là ngôn ngữ trung tính) và vẫn sinh slide chữ
Việt. `style.json` dùng `name:{zh,en}` — loader lấy tên tiếng Anh làm nhãn.

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
