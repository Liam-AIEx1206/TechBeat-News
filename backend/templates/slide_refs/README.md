# Khung slide mẫu (Reference Slides)

Đây là **cơ chế khống chế chất lượng output** của luồng gen slide — mô phỏng
`reference_style.svg` của PPT Master: mỗi lần gen, backend chọn 1 file mẫu theo
layout, thay màu theo theme, rồi nhét **nguyên SVG mẫu** vào prompt với chỉ dẫn
*"bắt chước cấu trúc/finishing — thay toàn bộ nội dung"*. Model bám khung sẵn
thay vì tự tưởng tượng bố cục.

## Bộ mẫu hiện có

| File | Layout key | Dùng cho |
|------|-----------|----------|
| `ref_cover.svg` | `cover_hero` | Slide mở đầu |
| `ref_cards.svg` | `card_grid`, `comparison` | 2–3 card có icon |
| `ref_kpi.svg` | `kpi_stats` | Số liệu + bar chart |
| `ref_split.svg` | `split_asym` | Cột chữ + panel ảnh |
| `ref_timeline.svg` | `timeline_process` | Chuỗi bước/mốc thời gian |
| `ref_ending.svg` | `ending_cta`, `quote_breathing` | Slide kết |

Mapping nằm ở `_REF_FOR_LAYOUT` trong `backend/routers/slides.py`.

## Tự thêm/sửa khung mẫu

1. **Vẽ SVG 1280×720** (`viewBox="0 0 1280 720"`), tuân thủ luật PPTX:
   không `<style>`/class/rgba/mask/foreignObject/group-opacity; màu HEX;
   font kết thúc bằng `Arial, Helvetica, sans-serif`.
2. **Tokenize màu** — dùng đúng các token sau thay cho HEX cứng, backend sẽ
   thay theo theme người dùng chọn:
   `__BG__ __BG2__ __SURFACE__ __ACCENT__ __ACCENT2__ __ACCENT3__ __TEXT1__ __TEXT2__`
3. **Icon**: dùng placeholder `<use data-icon="phosphor-duotone/rocket" x=".." y=".."
   width="48" height="48" fill="__ACCENT__"/>` — tên icon phải tồn tại trong
   `backend/templates/icons/<lib>/`.
4. **Ảnh** (nếu khung có panel ảnh): `<image href="__SLIDE_IMAGE__" ...
   preserveAspectRatio="xMidYMid slice" clip-path="url(#imgClip)"/>` — token này
   được thay bằng ảnh thật của scene (hoặc cả panel được model thay bằng visual
   native khi scene không có ảnh).
5. Lưu file vào thư mục này rồi **đăng ký** trong `_REF_FOR_LAYOUT`
   (map layout key → tên file không đuôi `.svg`).
6. **Kiểm tra bằng mắt** trước khi dùng: render thử
   ```bash
   # thay token bằng palette rồi render PNG bằng backend/lib/svg_render.py
   python3 - <<'PY'
   import asyncio, sys; sys.path.insert(0, 'backend/lib')
   import importlib.util as ilu
   for n in ('finalize_svg','svg_render'):
       s=ilu.spec_from_file_location(n,f'backend/lib/{n}.py'); m=ilu.module_from_spec(s); s.loader.exec_module(m)
       globals()[n]=m
   PAL={"__BG__":"#08080f","__BG2__":"#0f0f1a","__SURFACE__":"#141420","__ACCENT__":"#f97316",
        "__ACCENT2__":"#fb923c","__ACCENT3__":"#fbbf24","__TEXT1__":"#f5f3ff","__TEXT2__":"#a09db8"}
   svg=open('backend/templates/slide_refs/ref_moi.svg').read()
   for k,v in PAL.items(): svg=svg.replace(k,v)
   svg=finalize_svg.embed_icons_in_svg_string(svg)
   png=asyncio.run(svg_render.render_svg_to_png(svg))
   open('preview.png','wb').write(png)
   PY
   ```

## Khung mẫu gốc của PPT Master (tham khảo thêm)

`ppt-master-ref/skills/ppt-master/templates/layouts/` có 7 bộ theme hoàn chỉnh
(cover/toc/chapter/content/ending + design_spec.md mỗi bộ): academic_defense,
ai_ops, government_blue, government_red, medical_university, pixel_retro,
psychology_attachment — hầu hết nền sáng, phong cách báo cáo doanh nghiệp/học
thuật. Muốn dùng bộ nào: copy SVG vào đây, đổi HEX cứng thành token màu ở trên,
đăng ký layout key là xong.
