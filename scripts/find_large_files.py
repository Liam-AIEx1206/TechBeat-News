import os

def get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_dir_size(entry.path)
    except Exception:
        pass
    return total

def main():
    root = "."
    items = []
    for entry in os.scandir(root):
        if entry.is_file():
            items.append((entry.name, entry.stat().st_size, "file"))
        elif entry.is_dir():
            size = get_dir_size(entry.path)
            items.append((entry.name, size, "dir"))
            
    items.sort(key=lambda x: x[1], reverse=True)
    print("Top items in root directory:")
    for name, size, item_type in items:
        print(f"{name} ({item_type}): {size / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    main()
