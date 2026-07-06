import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.pinkyne.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not api_key:
    # Try GROQ as fallback
    api_key = os.getenv("GROQ_API_KEY")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

print(f"Using API Key: {api_key[:10]}... Base URL: {base_url} Model: {model}")

client = OpenAI(api_key=api_key, base_url=base_url)

styles_dir = Path(__file__).parent.parent / "backend" / "templates" / "styles"

# Category translations
category_map = {
    "东方 · 国风": "Oriental · Traditional",
    "大胆 · 宣言": "Bold · Statement",
    "插画 · 手绘": "Illustration · Hand-drawn",
    "效果 · 戏剧": "Dramatic · Cinematic",
    "暖色 · 治愈": "Warm · Healing",
    "杂志 · 编辑": "Magazine · Editorial",
    "活力 · 创意": "Vibrant · Creative",
    "浅色 · 专业": "Light · Professional",
    "浅色 · 极简": "Light · Minimalist",
    "浅色 · 柔和": "Light · Soft",
    "深色 · 奢华": "Dark · Luxury",
    "深色 · 沉稳": "Dark · Minimalist",
    "深色 · 科技": "Dark · Tech",
    "自然 · 有机": "Natural · Organic",
    "tech": "Tech"
}

# Collect descriptions to translate
to_translate = []
styles_data = []

for d in sorted(styles_dir.iterdir()):
    if not d.is_dir():
        continue
    sj = d / "style.json"
    if not sj.exists():
        continue
    try:
        meta = json.loads(sj.read_text(encoding="utf-8"))
        styles_data.append((sj, meta))
        desc = meta.get("description", "")
        # Check if description has Chinese characters
        if re.search(r"[\u4e00-\u9fff]", desc):
            to_translate.append({
                "id": d.name,
                "description": desc
            })
    except Exception as e:
        print(f"Error loading {sj}: {e}")

print(f"Found {len(to_translate)} descriptions containing Chinese characters.")

# Translate in batches
batch_size = 30
translated_map = {}

for i in range(0, len(to_translate), batch_size):
    batch = to_translate[i:i+batch_size]
    prompt = (
        "You are a professional translator. Translate the following Chinese slide style descriptions "
        "into elegant, concise, and natural English descriptions suitable for a UI presentation. "
        "Maintain the tone and nuance (e.g. references to colors, minimalism, professional look). "
        "Return the output strictly as a JSON object where the keys are the style IDs and the values "
        "are the translated English descriptions. Do not include markdown formatting or backticks around the JSON.\n\n"
        f"Input data:\n{json.dumps(batch, ensure_ascii=False, indent=2)}"
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise JSON translator. You only output valid JSON without any markdown formatting, explanation, or code blocks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        # Clean potential markdown fences
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                content = "\n".join(lines[1:-1])
        
        batch_translations = json.loads(content)
        translated_map.update(batch_translations)
        print(f"Translated batch {i // batch_size + 1} successfully.")
    except Exception as e:
        print(f"Error translating batch starting at {i}: {e}")
        # Try individual fallbacks if batch fails
        for item in batch:
            try:
                single_prompt = f"Translate to elegant English: \"{item['description']}\""
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Translate the input to elegant, concise English suitable for a UI description."},
                        {"role": "user", "content": single_prompt}
                    ]
                )
                translated_map[item['id']] = resp.choices[0].message.content.strip()
                print(f"Individual fallback translation for {item['id']} succeeded.")
            except Exception as ex:
                print(f"Failed to translate {item['id']}: {ex}")

# Write changes back to style.json
for sj, meta in styles_data:
    changed = False
    
    # 1. Update category
    cat = meta.get("category", "")
    if cat in category_map:
        meta["category"] = category_map[cat]
        changed = True
        
    # 2. Update description
    style_id = sj.parent.name
    if style_id in translated_map:
        meta["description"] = translated_map[style_id]
        changed = True
        
    # 3. If name has Chinese, make sure name.en is used as name or translate it
    name_field = meta.get("name")
    if isinstance(name_field, dict):
        # We can keep name.zh but let's make sure the name.en exists
        # In style_packs.py, label will default to name.en, which is already English
        pass
    
    if changed:
        try:
            sj.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Updated {sj.parent.name}")
        except Exception as e:
            print(f"Failed to write to {sj}: {e}")

print("Done translating all styles!")
