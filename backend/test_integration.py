# -*- coding: utf-8 -*-
import json
import httpx
import asyncio

async def test_generate_composition_integration():
    url = "http://127.0.0.1:8000/generate-composition"
    
    payload = {
        "title": "Báo cáo thử nghiệm thế hệ mới",
        "theme": "cyber-orange",
        "totalDuration": 20,
        "scenes": [
            {
                "id": "scene-1",
                "index": 0,
                "title": "Mở đầu kỷ nguyên AI mới",
                "narration": "Chào mừng đến với kỷ nguyên trí tuệ nhân tạo thế hệ mới của chúng ta.",
                "visualDescription": "Hiển thị card lớn B14 TECH-CARD chứa thông tin Google I/O 2026, tags: AI, Cloud, Future.",
                "duration": 10
            },
            {
                "id": "scene-2",
                "index": 1,
                "title": "Sự phát triển đột phá",
                "narration": "Chúng ta đang thấy sự tăng trưởng vượt bậc về hiệu năng của mô hình mới.",
                "visualDescription": "Hiển thị B11 STAT-LIST với chỉ số 10x tốc độ, 50% rẻ hơn.",
                "duration": 10
            }
        ]
    }
    
    print("Sending POST request to /generate-composition...")
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"Failed with status: {response.status_code}")
                    body = await response.aread()
                    print(body.decode("utf-8"))
                    return
                
                print("Connected! Reading SSE stream:")
                done_received = False
                chunks_received = 0
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type")
                            print(f"Event: {event_type}")
                            
                            if event_type == "model_info":
                                print(f"  Model: {event.get('model')} via {event.get('provider')}")
                            elif event_type == "chunk":
                                chunks_received += 1
                                # Just print the first few chunks to avoid flooding
                                if chunks_received <= 5:
                                    print(f"  Chunk: {repr(event.get('text'))}")
                            elif event_type == "done":
                                done_received = True
                                html_len = len(event.get("html", ""))
                                print(f"✓ Event done received! Final HTML length: {html_len} characters")
                                # Print first 15 lines of the final HTML to inspect formatting
                                html_lines = event.get("html", "").split("\n")
                                print("\n--- FIRST 20 LINES OF GENERATED HTML ---")
                                print("\n".join(html_lines[:20]))
                                print("----------------------------------------\n")
                            elif event_type == "warning":
                                print(f"  Warning: {event.get('message')}")
                            elif event_type == "error":
                                print(f"  Error: {event.get('message')}")
                        except Exception as parse_err:
                            print(f"  Failed to parse event: {line} - Error: {parse_err}")
                
                if done_received:
                    print("OK: Integration test passed successfully!")
                else:
                    print("FAIL: Event 'done' was never received.")
    except Exception as e:
        print(f"Exception during request: {e}")

if __name__ == "__main__":
    asyncio.run(test_generate_composition_integration())
