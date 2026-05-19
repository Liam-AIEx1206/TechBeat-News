import io
import re


def extract_from_docx(data: bytes, filename: str) -> dict:
    from docx import Document

    doc = Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ")
    return {"title": title.strip(), "text": text[:20000], "source": filename}


def extract_from_pptx(data: bytes, filename: str) -> dict:
    from pptx import Presentation

    prs = Presentation(io.BytesIO(data))

    slides_text = []
    for slide in prs.slides:
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = " ".join(run.text for run in para.runs).strip()
                    if line:
                        parts.append(line)
        if parts:
            slides_text.append("\n".join(parts))

    text = "\n\n".join(slides_text)
    title = re.sub(r"\.[^.]+$", "", filename).replace("-", " ").replace("_", " ")
    return {"title": title.strip(), "text": text[:20000], "source": filename}
