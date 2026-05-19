import json
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import get_async_client, get_model

router = APIRouter()


SYSTEM_PROMPT = """Bạn là chuyên gia viết kịch bản video tiếng Việt và chiến lược nội dung.
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

Định dạng JSON:
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
}"""


class ScenesRequest(BaseModel):
    content: str
    title: str


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_scenes(content: str, title: str):
    try:
        client = get_async_client()
    except ValueError as e:
        yield sse({"type": "error", "message": str(e)})
        return

    full_text = ""

    try:
        prompt = f"Tạo kế hoạch scene video.\n\nTiêu đề: {title}\n\nNội dung:\n{content}"

        stream = await client.chat.completions.create(
            model=get_model("scenes"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            stream=True,
        )

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
            yield sse({"type": "done", "scenePlan": scene_plan})
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
