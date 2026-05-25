import io
import re


def extract_from_docx(data: bytes, filename: str) -> dict:
    from docx import Document

    doc = Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ")
    print(f"[DOCX] '{filename}' — {len(text)} ký tự")
    return {"title": title.strip(), "text": text, "source": filename}  # không giới hạn


def extract_from_pptx(data: bytes, filename: str) -> dict:
    from pptx import Presentation

    # Namespace for DrawingML text elements (used in XML fallback)
    _A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

    prs = Presentation(io.BytesIO(data))
    total_slides = len(prs.slides)
    print(f"[PPTX] '{filename}' — tổng số slide: {total_slides}")

    def _xml_text(element) -> list[str]:
        """Fallback: extract every <a:t> text node from raw XML (handles SmartArt, etc.)"""
        try:
            texts = element.findall(f".//{{{_A_NS}}}t")
            return [t.text.strip() for t in texts if t.text and t.text.strip()]
        except Exception:
            return []

    def _shape_lines(shape, depth: int = 0) -> list[str]:
        """Recursively extract text lines from any shape type."""
        if depth > 8:
            return []
        lines: list[str] = []

        # ── GROUP: recurse into children ──────────────────────────────────
        # Use two methods: MSO_SHAPE_TYPE enum AND hasattr fallback
        is_group = False
        try:
            from pptx.enum.shapes import MSO_SHAPE_TYPE  # type: ignore
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                is_group = True
        except Exception:
            pass
        # hasattr fallback: GroupShapes object has a .shapes iterable
        if not is_group and hasattr(shape, "shapes"):
            try:
                _ = iter(shape.shapes)  # confirm it's iterable
                is_group = True
            except Exception:
                pass

        if is_group:
            try:
                for child in shape.shapes:
                    lines.extend(_shape_lines(child, depth + 1))
            except Exception as grp_err:
                print(f"[PPTX]     GROUP iter error: {grp_err}")
            return lines

        # ── Text frame ────────────────────────────────────────────────────
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                line = para.text.strip()
                if line:
                    lines.append(line)

        # ── Tables ───────────────────────────────────────────────────────
        if shape.has_table:
            for row in shape.table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))

        # ── XML fallback (SmartArt, WordArt, embedded text frames) ───────
        if not lines:
            xml_lines = _xml_text(shape.element)
            if xml_lines:
                lines.extend(xml_lines)

        return lines

    def _shape_type_name(shape) -> str:
        """Human-readable shape type for logging."""
        try:
            return str(shape.shape_type).split(".")[-1]
        except Exception:
            try:
                return str(int(shape.shape_type))
            except Exception:
                return "?"

    slides_text: list[str] = []
    slides_with_content = 0

    for i, slide in enumerate(prs.slides):
        slide_num = i + 1
        parts: list[str] = []
        shape_count = len(slide.shapes)
        shape_errors = 0
        shape_infos: list[str] = []

        for shape in slide.shapes:
            s_type = _shape_type_name(shape)
            s_name = getattr(shape, "name", "?")
            try:
                extracted = _shape_lines(shape)
                parts.extend(extracted)
                shape_infos.append(f"{s_name}[{s_type}]={len(extracted)}ln")
            except Exception as e:
                shape_errors += 1
                shape_infos.append(f"{s_name}[{s_type}]=ERR")
                print(f"[PPTX]   Slide {slide_num}: lỗi shape '{s_name}' ({s_type}) — {e}")

        # Speaker notes — often contain the richest explanatory content
        notes_added = False
        try:
            if slide.has_notes_slide:
                notes_tf = slide.notes_slide.notes_text_frame
                if notes_tf:
                    notes = notes_tf.text.strip()
                    ignore = {"click to add notes", "nhấp để thêm ghi chú", ""}
                    if notes.lower() not in ignore:
                        parts.append(f"[Ghi chú slide]: {notes}")
                        notes_added = True
        except Exception as e:
            print(f"[PPTX]   Slide {slide_num}: lỗi đọc ghi chú — {e}")

        slide_chars = sum(len(p) for p in parts)
        status = "✓" if parts else "⚠ TRỐNG"
        note_tag = " +notes" if notes_added else ""
        err_tag = f" [{shape_errors} shape-lỗi]" if shape_errors else ""
        shapes_detail = ", ".join(shape_infos) if shape_infos else "—"
        print(
            f"[PPTX]   Slide {slide_num:2d}/{total_slides}: "
            f"{shape_count} shapes ({shapes_detail}), "
            f"{len(parts)} dòng, {slide_chars} ký tự{note_tag}{err_tag} {status}"
        )

        if parts:
            slides_with_content += 1
            slides_text.append(f"=== Slide {slide_num} ===\n" + "\n".join(parts))

    text = "\n\n".join(slides_text)  # không giới hạn — gửi full nội dung cho LLM
    total_chars = len(text)

    print(
        f"[PPTX] Tổng kết: {slides_with_content}/{total_slides} slide có nội dung, "
        f"{total_chars} ký tự (không cắt)"
    )

    # Derive title from first slide
    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ")
    try:
        if prs.slides:
            for shape in prs.slides[0].shapes:
                if shape.has_text_frame:
                    t = shape.text_frame.text.strip()
                    if t:
                        title = t.split("\n")[0][:120]
                        break
    except Exception:
        pass

    return {"title": title.strip(), "text": text, "source": filename}
