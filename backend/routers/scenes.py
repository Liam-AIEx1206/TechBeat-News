import json
import os
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import chat_completions_with_fallback

router = APIRouter()


def build_system_prompt_full(video_duration: int | None = None) -> str:
    if video_duration is not None and video_duration > 0:
        if video_duration <= 60:
            n_scenes = "exactly 4 scenes (phân cảnh)"
            words_per_scene = "45-55 từ"
            secs_per_scene = "15-18 giây"
            total_duration_desc = f"tổng {video_duration} giây (1 phút)"
            rule_scenes = (
                f"- Scene 1 — Mở đầu & bối cảnh: 15s, hook đặt vấn đề nhanh gọn, súc tích\n"
                f"- Scene 2-3 — Nội dung chính: 15s mỗi scene, đi sâu vào khía cạnh cốt lõi\n"
                f"- Scene 4 — Kết luận & Tầm quan trọng: 15s, tổng kết thông điệp chính"
            )
            narration_ex = "45-55 từ tiếng Việt giải thích đầy đủ: vấn đề, nguyên nhân, số liệu cốt lõi"
            total_duration_val = video_duration
        elif video_duration <= 120:
            n_scenes = "5-6 scene"
            words_per_scene = "65-75 từ"
            secs_per_scene = "20-25 giây"
            total_duration_desc = f"tổng {video_duration} giây (2 phút)"
            rule_scenes = (
                f"- Scene 1 — Mở đầu & bối cảnh: 20s\n"
                f"- Scene 2-4 — Nội dung chính: 20-25s mỗi scene\n"
                f"- Scene cuối (Scene 5 hoặc 6) — Kết luận: 20s"
            )
            narration_ex = "65-75 từ tiếng Việt: vấn đề, nguyên nhân, số liệu, ý nghĩa"
            total_duration_val = video_duration
        else:  # e.g., 180 (3 minutes)
            n_scenes = "7-8 scene"
            words_per_scene = "70-85 từ"
            secs_per_scene = "22-28 giây"
            total_duration_desc = f"tổng {video_duration} giây (3 phút)"
            rule_scenes = (
                f"- Scene 1 — Mở đầu & bối cảnh: 22-25s\n"
                f"- Scene 2-6 — Nội dung chính: 25-28s mỗi scene\n"
                f"- Scene cuối (Scene 7 hoặc 8) — Kết luận: 22-25s"
            )
            narration_ex = "70-85 từ tiếng Việt: vấn đề, nguyên nhân, số liệu, ý nghĩa"
            total_duration_val = video_duration
    elif video_duration == -1:
        n_scenes = "as many scenes (phân cảnh) as needed to fully cover the content of the article detailedly without any summarization or omissions"
        words_per_scene = "60-90 từ (ngoại trừ Scene 1)"
        secs_per_scene = "20-30 giây (ngoại trừ Scene 1)"
        total_duration_desc = "tổng thời lượng thực tế dựa trên độ dài văn bản gốc (Không tóm tắt / Không giới hạn)"
        rule_scenes = (
            "- BẮT BUỘC tạo Phân cảnh 1 (Scene 1) là Phân cảnh Intro (Giới thiệu/Khái quát) dài khoảng 1-2 phút (150-250 từ narration) khái quát toàn bộ nội dung chính sẽ nói trong video được sinh ra từ tư liệu người dùng. Kịch bản phần intro này do AI tự thiết kế, viết một cách lôi cuốn, sinh động nhất.\n"
            "- Từ Phân cảnh 2 trở đi, tạo số lượng phân cảnh tự do, không bị giới hạn, đảm bảo chuyển tải chi tiết 100% nội dung bài viết gốc, mỗi scene diễn đạt trọn vẹn một phần nội dung thông tin tự nhiên, KHÔNG tóm tắt hay cắt xén chi tiết."
        )
        narration_ex = "60-90 từ tiếng Việt giải thích đầy đủ: thông tin, bối cảnh, số liệu chi tiết tương ứng"
        total_duration_val = 240
    else:
        n_scenes = "5-6 scene"
        words_per_scene = "60-90 từ"
        secs_per_scene = "25-35 giây"
        total_duration_desc = "tổng 150-180 giây (2.5-3 phút)"
        rule_scenes = (
            "- Scene 1 — Mở đầu & bối cảnh: 20-25s, hook hấp dẫn, đặt vấn đề rõ ràng\n"
            "- Scene 2-4 — Nội dung chính: 30-40s mỗi scene, mỗi scene một khía cạnh sâu khác nhau\n"
            "- Scene 5 — Chi tiết / Dẫn chứng: 30-35s, số liệu, ví dụ cụ thể từ bài báo\n"
            "- Scene cuối — Kết luận & Tầm quan trọng: 20-30s, tổng kết, mở ra tương lai"
        )
        narration_ex = "60-90 từ tiếng Việt giải thích đầy đủ: vấn đề, nguyên nhân, số liệu, ý nghĩa"
        total_duration_val = 165

    return f"""Bạn là chuyên gia viết kịch bản video tin tức tiếng Việt cho đài truyền hình.
Nhiệm vụ: chuyển nội dung bài báo thành kịch bản video ĐẦY ĐỦ, SÂU SẮC — KHÔNG tóm tắt sơ sài.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT tự nhiên, có dấu đầy đủ
- KHÔNG dùng tiếng Anh cho narration/title (trừ tên riêng/thương hiệu)
- imageQuery giữ tiếng Anh (2-5 từ, dùng để tìm ảnh stock)

━━━ QUY TẮC NARRATION (QUAN TRỌNG NHẤT) ━━━
Mỗi narration PHẢI giải thích ĐẦY ĐỦ theo công thức:
  VẤN ĐỀ/SỰ KIỆN LÀ GÌ → TẠI SAO xảy ra / quan trọng → SỐ LIỆU / DẪN CHỨNG CỤ THỂ → Ý NGHĨA / HỆ QUẢ
Viết như phóng viên truyền hình đang đọc bản tin — người xem CHƯA BIẾT GÌ về chủ đề này.
KHÔNG chỉ nêu tên sự kiện, PHẢI kể câu chuyện đằng sau với đầy đủ bối cảnh.
Mỗi narration dài đúng {words_per_scene} tiếng Việt (tương đương {secs_per_scene} đọc tự nhiên).

━━━ QUY TẮC SCENE & CHỐNG TÓM TẮT SƠ SÀI ━━━
- {n_scenes}, {total_duration_desc}
{rule_scenes}
- visualDescription: mô tả cụ thể text overlay, infographic, animation sẽ hiển thị

⚠️ CẤM VIẾT TÓM TẮT NGẮN CŨN / SƠ SÀI: Nếu phần nội dung gốc nào quá ngắn hoặc nghèo dữ liệu để tạo thành một scene phong phú, hãy gộp lại hoặc chủ động viết phân tích mở rộng chi tiết hơn để làm giàu nội dung.
⚠️ visualDescription PHẢI CỰC KỲ CHI TIẾT & CỤ THỂ: Đối với mỗi scene, visualDescription BẮT BUỘC phải liệt kê rõ ràng ít nhất 3-4 thông số/dữ liệu thực tế, các ví dụ thực tế (như tên các hàm, dòng code mẫu, tên các file cấu hình, số lượng commit, mốc thời gian cụ thể, tên công ty, số liệu phần trăm...) tương ứng với chủ đề đang nói. Cấm ghi chung chung kiểu "hiển thị một biểu đồ" hoặc "hiển thị vài icon". Thông tin này sẽ giúp máy sinh HTML tự động chia khối bento, grid card, timeline hay progress bar một cách trực quan, sinh động và ngăn nắp nhất.

Chỉ trả về JSON hợp lệ, KHÔNG markdown fence, KHÔNG giải thích ngoài JSON.

Định dạng JSON:
{{
  "title": "Tiêu đề video bằng tiếng Việt",
  "scenes": [
    {{
      "id": "scene-1",
      "index": 0,
      "title": "Tiêu đề scene tiếng Việt",
      "narration": "{narration_ex}",
      "visualDescription": "Mô tả cực kỳ cụ thể: danh sách 3-4 key points/thông số/dữ liệu thực tế và các ví dụ thực tiễn như code, thông số benchmark, mốc thời gian cụ thể...",
      "duration": 15,
      "imageQuery": "english stock photo query"
    }}
  ],
  "totalDuration": {total_duration_val}
}}"""


def build_system_prompt_groq(max_scenes: int, video_duration: int | None = None) -> str:
    if video_duration is not None:
        if video_duration == -1:
            target_scenes = max_scenes
            words = "60-90 (ngoại trừ Scene 1 dài 150-250 từ)"
            duration_desc = "thời lượng không giới hạn"
            scene_structure = (
                "- BẮT BUỘC tạo Phân cảnh 1 (Scene 1) là Phân cảnh Intro (Giới thiệu/Khái quát) dài khoảng 1-2 phút (150-250 từ narration) khái quát toàn bộ nội dung chính sẽ nói trong video được sinh ra từ tư liệu người dùng. Kịch bản phần intro này do AI tự thiết kế, viết một cách lôi cuốn, sinh động nhất.\n"
                "- Từ Phân cảnh 2 trở đi, tạo số lượng phân cảnh tự do để truyền tải chi tiết 100% nội dung gốc, mỗi scene diễn đạt trọn vẹn một phần nội dung thông tin tự nhiên, KHÔNG tóm tắt hay cắt xén chi tiết."
            )
        elif video_duration <= 60:
            target_scenes = 4
            words = "45-55"
            duration_desc = f"tổng {video_duration} giây"
            scene_structure = (
                f"- Scene 1: mở đầu & bối cảnh 15s\n"
                f"- Scene 2-3: nội dung chính 15s mỗi scene\n"
                f"- Scene 4: kết luận 15s"
            )
        elif video_duration <= 120:
            target_scenes = min(max_scenes, 5)
            words = "65-75"
            duration_desc = f"tổng {video_duration} giây"
            scene_structure = (
                f"- Scene 1: mở đầu & bối cảnh 20s\n"
                f"- Scene 2 đến {target_scenes-1}: nội dung chính 20-25s mỗi scene\n"
                f"- Scene {target_scenes}: kết luận 20s"
            )
        else:
            target_scenes = max_scenes
            words = "70-85"
            duration_desc = f"tổng {video_duration} giây"
            scene_structure = (
                f"- Scene 1: mở đầu & bối cảnh 22-25s\n"
                f"- Scene 2 đến {target_scenes-1}: nội dung chính 25-28s mỗi scene\n"
                f"- Scene {target_scenes}: kết luận 22-25s"
            )
    else:
        target_scenes = max_scenes
        words = "50-75"
        duration_desc = "tổng 120-180 giây"
        scene_structure = (
            f"- Scene 1: mở đầu & bối cảnh 20-25s\n"
            f"- Scene 2 đến {target_scenes-1}: nội dung chính 25-35s mỗi scene\n"
            f"- Scene {target_scenes}: kết luận 20-25s"
        )

    return f"""Bạn là chuyên gia viết kịch bản video tin tức tiếng Việt.
Viết kịch bản ĐẦY ĐỦ, SÂU SẮC — không tóm tắt sơ sài.

⚠️ TIẾNG VIỆT bắt buộc, có dấu đầy đủ. imageQuery giữ tiếng Anh.

QUY TẮC NARRATION:
- Mỗi narration: VẤN ĐỀ → TẠI SAO → SỐ LIỆU CỤ THỂ → Ý NGHĨA
- Viết như phóng viên truyền hình — người xem chưa biết gì về chủ đề
- Dài {words} từ tiếng Việt (đọc tự nhiên)

QUY TẮC SCENE & CHỐNG TÓM TẮT SƠ SÀI:
- Tạo TỐI ĐA {target_scenes} scene, {duration_desc}
{scene_structure}

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
      "narration": "{words} từ tiếng Việt: vấn đề, nguyên nhân, số liệu, ý nghĩa",
      "visualDescription": "Mô tả cực kỳ cụ thể: danh sách 3-4 key points/thông số/dữ liệu thực tế và các ví dụ thực tiễn như code, thông số benchmark, mốc thời gian cụ thể...",
      "duration": 15,
      "imageQuery": "english stock photo query"
    }}
  ],
  "totalDuration": {video_duration if video_duration else 150}
}}"""


class ScenesRequest(BaseModel):
    content: str
    title: str
    videoDuration: int | None = None


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_scenes(content: str, title: str, video_duration: int | None = None):
    full_text = ""
    groq_max = int(os.getenv("GROQ_MAX_SCENES", "5"))

    try:
        prompt = f"Tạo kế hoạch scene video.\n\nTiêu đề: {title}\n\nNội dung:\n{content}"
        if video_duration and video_duration > 0:
            if video_duration <= 60:
                n_scenes = "exactly 4"
                words_per_scene = "45-55"
                secs_per_scene = "15"
            elif video_duration <= 120:
                n_scenes = "5-6"
                words_per_scene = "65-75"
                secs_per_scene = "20-25"
            else:
                n_scenes = "7-8"
                words_per_scene = "70-85"
                secs_per_scene = "22-28"
            prompt += (
                f"\n\n⚠️ YÊU CẦU ĐẶC BIỆT VỀ THỜI LƯỢNG (BẮT BUỘC): "
                f"Target video = {video_duration} giây. "
                f"Tạo đúng {n_scenes} scene, mỗi scene {secs_per_scene}s, tổng totalDuration = {video_duration}. "
                f"QUAN TRỌNG NHẤT: Mỗi narration BẮT BUỘC phải dài {words_per_scene} từ tiếng Việt (tương đương {secs_per_scene} giây đọc). "
                f"Narration súc tích nhưng đầy đủ thông tin, KHÔNG lan man, viết vừa đủ dài để đạt đúng thời lượng yêu cầu. "
                f"Nếu viết quá ngắn, video sẽ bị thiếu thời lượng trầm trọng (ví dụ 1 phút but chỉ có 35s). Đây là yêu cầu TUYỆT ĐỐI."
            )
        elif video_duration == -1:
            prompt += (
                f"\n\n⚠️ YÊU CẦU ĐẶC BIỆT (KHÔNG TÓM TẮT - KHÔNG GIỚI HẠN THỜI LƯỢNG):\n"
                f"- BẮT BUỘC tạo Phân cảnh 1 (Scene 1) là Phân cảnh Intro (Giới thiệu/Khái quát) dài khoảng 1-2 phút (từ 150 đến 250 từ narration) khái quát toàn bộ nội dung chính sẽ nói trong video được sinh ra từ tư liệu người dùng. Kịch bản phần intro này do AI tự thiết kế, viết một cách lôi cuốn, sinh động nhất.\n"
                f"- Từ Phân cảnh 2 trở đi, hãy chia kịch bản thành số lượng scene tự do (không giới hạn) để diễn đạt đầy đủ, chi tiết 100% nội dung bài viết gốc.\n"
                f"- Tuyệt đối KHÔNG tóm tắt sơ sài, KHÔNG lược bỏ các thông số, mốc thời gian, tên gọi hoặc số liệu quan trọng.\n"
                f"- Mỗi scene viết narration dài khoảng 60-90 từ tiếng Việt (đọc trong khoảng 20-30 giây)."
            )

        def _kwargs(provider_name: str) -> dict:
            if provider_name in ("groq", "groq-fast"):
                return {
                    "messages": [
                        {"role": "system", "content": build_system_prompt_groq(groq_max, video_duration)},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "stream": True,
                }
            return {
                "messages": [
                    {"role": "system", "content": build_system_prompt_full(video_duration)},
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
        stream_scenes(body.content, body.title, body.videoDuration),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
