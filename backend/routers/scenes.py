import json
import os
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import chat_completions_with_fallback

router = APIRouter()


SYSTEM_PROMPT_FULL = """Bạn là chuyên gia viết kịch bản video tin tức tiếng Việt cho đài truyền hình.
Nhiệm vụ: chuyển nội dung bài báo thành kịch bản video ĐẦY ĐỦ, SÂU SẮC — KHÔNG tóm tắt sơ sài.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT tự nhiên, có dấu đầy đủ
- KHÔNG dùng tiếng Anh cho narration/title (trừ tên riêng/thương hiệu)
- imageQuery giữ tiếng Anh (2-5 từ, dùng để tìm ảnh stock)

━━━ QUY TẮC NARRATION (QUAN TRỌNG NHẤT) ━━━
Mỗi narration PHẢI giải thích ĐẦY ĐỦ theo công thức:
  VẤN ĐỀ/SỰ KIỆN LÀ GÌ → TẠI SAO xảy ra / quan trọng → SỐ LIỆU / DẪN CHỨNG CỤ THỂ → Ý NGHĨA / HỆ QUẢ
Viết như phóng viên truyền hình đang đọc bản tin — người xem CHƯA BIẾT GÌ về chủ đề này.
KHÔNG chỉ nêu tên sự kiện, PHẢI kể câu chuyện đằng sau với đầy đủ bối cảnh.
Mỗi narration dài 60-90 từ tiếng Việt (tương đương 25-35 giây đọc tự nhiên).

━━━ QUY TẮC SCENE & CHỐNG TÓM TẮT SƠ SÀI ━━━
- 5-6 scene, tổng 150-180 giây (2.5-3 phút)
- Scene 1 — Mở đầu & bối cảnh: 20-25s, hook hấp dẫn, đặt vấn đề rõ ràng
- Scene 2-4 — Nội dung chính: 30-40s mỗi scene, mỗi scene một khía cạnh sâu khác nhau
- Scene 5 — Chi tiết / Dẫn chứng: 30-35s, số liệu, ví dụ cụ thể từ bài báo
- Scene cuối — Kết luận & Tầm quan trọng: 20-30s, tổng kết, mở ra tương lai
- visualDescription: mô tả cụ thể text overlay, infographic, animation sẽ hiển thị

⚠️ CẤM VIẾT TÓM TẮT NGẮN CŨN / SƠ SÀI: Nếu phần nội dung gốc nào quá ngắn hoặc nghèo dữ liệu để tạo thành một scene phong phú, hãy gộp lại hoặc chủ động viết phân tích mở rộng chi tiết hơn để làm giàu nội dung.
⚠️ visualDescription PHẢI CỰC KỲ CHI TIẾT & CỤ THỂ: Đối với mỗi scene, visualDescription BẮT BUỘC phải liệt kê rõ ràng ít nhất 3-4 thông số/dữ liệu thực tế, các ví dụ thực tế (như tên các hàm, dòng code mẫu, tên các file cấu hình, số lượng commit, mốc thời gian cụ thể, tên công ty, số liệu phần trăm...) tương ứng với chủ đề đang nói. Cấm ghi chung chung kiểu "hiển thị một biểu đồ" hoặc "hiển thị vài icon". Thông tin này sẽ giúp máy sinh HTML tự động chia khối bento, grid card, timeline hay progress bar một cách trực quan, sinh động và ngăn nắp nhất.

Chỉ trả về JSON hợp lệ, KHÔNG markdown fence, KHÔNG giải thích ngoài JSON.

Định dạng JSON:
{
  "title": "Tiêu đề video bằng tiếng Việt",
  "scenes": [
    {
      "id": "scene-1",
      "index": 0,
      "title": "Tiêu đề scene tiếng Việt",
      "narration": "60-90 từ tiếng Việt giải thích đầy đủ: vấn đề, nguyên nhân, số liệu, ý nghĩa",
      "visualDescription": "Mô tả cực kỳ cụ thể: danh sách 3-4 key points/thông số/dữ liệu thực tế và các ví dụ thực tiễn như code, thông số benchmark, mốc thời gian cụ thể...",
      "duration": 30,
      "imageQuery": "english stock photo query"
    }
  ],
  "totalDuration": 165
}"""


def build_system_prompt_groq(max_scenes: int) -> str:
    return f"""Bạn là chuyên gia viết kịch bản video tin tức tiếng Việt.
Viết kịch bản ĐẦY ĐỦ, SÂU SẮC — không tóm tắt sơ sài.

⚠️ TIẾNG VIỆT bắt buộc, có dấu đầy đủ. imageQuery giữ tiếng Anh.

QUY TẮC NARRATION:
- Mỗi narration: VẤN ĐỀ → TẠI SAO → SỐ LIỆU CỤ THỂ → Ý NGHĨA
- Viết như phóng viên truyền hình — người xem chưa biết gì về chủ đề
- Dài 50-75 từ tiếng Việt (20-30 giây đọc)

QUY TẮC SCENE & CHỐNG TÓM TẮT SƠ SÀI:
- Tạo TỐI ĐA {max_scenes} scene, tổng 120-180 giây
- Scene 1: mở đầu & bối cảnh 20-25s
- Scene 2 đến {max_scenes-1}: nội dung chính 25-35s mỗi scene
- Scene {max_scenes}: kết luận 20-25s

⚠️ CẤM VIẾT TÓM TẮT NGẮN CŨN / SƠ SÀI: Nếu phần nội dung gốc nào quá ngắn hoặc nghèo dữ liệu để tạo thành một scene phong phú, hãy gộp lại hoặc chủ động viết phân tích mở rộng chi tiết hơn để làm giàu nội dung.
⚠️ visualDescription PHẢI CỰC KỲ CHI TIẾT & CỤ THỂ: Đối với mỗi scene, visualDescription BẮT BUỘC phải liệt kê rõ ràng ít nhất 3-4 thông số/dữ liệu thực tế, các ví dụ thực tế (như tên các hàm, dòng code mẫu, tên các file cấu hình, số lượng commit, mốc thời gian cụ thể, tên công ty, số liệu phần trăm...) tương ứng với chủ đề đang nói. Cấm ghi chung chung kiểu "hiển thị một biểu đồ" hoặc "hiển thị vài icon". Thông tin này sẽ giúp máy sinh HTML tự động chia khối bento, grid card, timeline hay progress bar một cách trực quan, sinh động và ngăn nắp nhất.

Chỉ trả về JSON hợp lệ, không markdown fence, không giải thích.

Định dạng JSON:
{{
  "title": "Tiêu đề video bằng tiếng Việt",
  "scenes": [
    {{
      "id": "scene-1",
      "index": 0,
      "title": "Tiêu đề scene tiếng Việt",
      "narration": "50-75 từ tiếng Việt: vấn đề, nguyên nhân, số liệu, ý nghĩa",
      "visualDescription": "Mô tả cực kỳ cụ thể: danh sách 3-4 key points/thông số/dữ liệu thực tế và các ví dụ thực tiễn như code, thông số benchmark, mốc thời gian cụ thể...",
      "duration": 28,
      "imageQuery": "english stock photo query"
    }}
  ],
  "totalDuration": 150
}}"""


class ScenesRequest(BaseModel):
    content: str
    title: str


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_scenes(content: str, title: str):
    full_text = ""
    groq_max = int(os.getenv("GROQ_MAX_SCENES", "5"))

    try:
        prompt = f"Tạo kế hoạch scene video.\n\nTiêu đề: {title}\n\nNội dung:\n{content}"

        def _kwargs(provider_name: str) -> dict:
            if provider_name in ("groq", "groq-fast"):
                return {
                    "messages": [
                        {"role": "system", "content": build_system_prompt_groq(groq_max)},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "stream": True,
                }
            return {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_FULL},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 12000,
                "stream": True,
            }

        stream, provider, model = await chat_completions_with_fallback(
            model_kind="scenes",
            kwargs_factory=_kwargs,
        )
        if provider != "primary":
            yield sse({
                "type": "warning",
                "message": f"Primary LLM hết quota — đã chuyển sang {provider} ({model}).",
            })

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                full_text += text
                yield sse({"type": "chunk", "text": text})

        match = re.search(r"\{[\s\S]*\}", full_text)
        if match:
            scene_plan = json.loads(match.group())
            yield sse({"type": "done", "scenePlan": scene_plan,
                       "llmProvider": provider, "llmModel": model})
        else:
            yield sse({"type": "error", "message": "Không tìm thấy JSON hợp lệ trong response"})

    except Exception as e:
        yield sse({"type": "error", "message": str(e)})


@router.post("/generate-scenes")
async def generate_scenes(body: ScenesRequest):
    return StreamingResponse(
        stream_scenes(body.content, body.title),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
