import httpx, json, asyncio

async def test():
    scenes = [
        {"id": "s1", "index": 0, "title": "Gioi thieu", "narration": "Mo dau video ve AI.", "visualDescription": "Hero cinematic", "duration": 8, "imageUrl": None, "imageAsset": None, "imageQuery": None},
        {"id": "s2", "index": 1, "title": "Noi dung chinh", "narration": "Noi dung chinh ve xu huong AI nam 2025.", "visualDescription": "Data visualization", "duration": 10, "imageUrl": None, "imageAsset": None, "imageQuery": None},
    ]
    base = {"title": "Test", "scenes": scenes, "totalDuration": 18, "theme": "cyber-orange"}

    async with httpx.AsyncClient(timeout=60) as c:
        # Step 1: gen scene 1
        r1 = await c.post("http://127.0.0.1:8000/gen-scene-one", json={**base, "sceneIndex": 1})
        d1 = r1.json()
        print("Scene 1 status:", r1.status_code)
        print("Scene 1 layout:", d1.get("layout"))
        print("Scene 1 html_len:", len(d1.get("html", "")))

        # Step 2: gen scene 2 passing existingHtml + newContext
        r2 = await c.post("http://127.0.0.1:8000/gen-scene-one", json={
            **base, "sceneIndex": 2,
            "existingHtml": d1["html"],
            "previousContext": d1["newContext"]
        })
        d2 = r2.json()
        print("Scene 2 status:", r2.status_code)
        print("Scene 2 layout:", d2.get("layout"))
        print("Scene 2 html_len:", len(d2.get("html", "")))
        print("Scene 2 done:", d2.get("done"))

        html = d2.get("html", "")
        print("Has id=scene1:", 'id="scene1"' in html)
        print("Has id=scene2:", 'id="scene2"' in html)
        print("Placeholder removed:", "SCENES_PLACEHOLDER" not in html)

asyncio.run(test())
