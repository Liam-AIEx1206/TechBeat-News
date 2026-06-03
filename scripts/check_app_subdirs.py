import os

def main():
    path = "./app"
    if not os.path.exists(path):
        print("app does not exist")
        return
        
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            total = 0
            for root, dirs, files in os.walk(entry.path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
            print(f"{entry.name} (dir): {total / 1024 / 1024:.2f} MB")
        else:
            print(f"{entry.name} (file): {entry.stat().st_size / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    main()
