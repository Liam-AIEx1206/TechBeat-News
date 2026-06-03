import re
from pathlib import Path

def validate_html(html_path: Path):
    content = html_path.read_text(encoding="utf-8")
    
    # Let's find all scenes
    scene_matches = list(re.finditer(r'<div\b[^>]*\bid\s*=\s*["\'](scene\d+)["\'][^>]*>', content, re.IGNORECASE))
    print(f"Found {len(scene_matches)} scene start tags:")
    
    for i, m in enumerate(scene_matches):
        scene_id = m.group(1)
        tag = m.group(0)
        start_pos = m.start()
        
        # Determine the next scene's start position or the end of the root div
        next_pos = scene_matches[i+1].start() if i < len(scene_matches) - 1 else len(content)
        segment = content[start_pos:next_pos]
        
        # Count open and close div tags in this segment
        open_divs = len(re.findall(r'<div\b', segment, re.IGNORECASE))
        close_divs = len(re.findall(r'</div>', segment, re.IGNORECASE))
        balance = open_divs - close_divs
        
        has_scene_class = "class=" in tag.lower() and "scene" in tag.lower()
        
        print(f"  - {scene_id}: open_divs={open_divs}, close_divs={close_divs}, balance={balance}, class_ok={has_scene_class}")
        print(f"    Tag: {tag}")
        if balance != 0:
            print(f"    WARNING: {scene_id} is NOT balanced! Balance is {balance}")
        if not has_scene_class:
            print(f"    WARNING: {scene_id} is MISSING the .scene class!")

if __name__ == "__main__":
    html_path = Path(__file__).parent / "my-video" / "index.html"
    if not html_path.exists():
        html_path = Path(__file__).resolve().parent.parent / "my-video" / "index.html"
    print(f"Validating HTML at: {html_path}")
    validate_html(html_path)
