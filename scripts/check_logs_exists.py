import os
path = r"C:\Users\cuong\.gemini\antigravity-ide\brain\104c994b-ed89-4af4-a29d-99678d037f59\.system_generated\tasks"
if os.path.exists(path):
    print("Directory exists")
    files = os.listdir(path)
    print("Files found:", len(files))
    for f in sorted(files):
        if "2691" in f or "2747" in f or "2757" in f or "2738" in f:
            print(f, os.path.getsize(os.path.join(path, f)))
else:
    print("Directory does not exist")
