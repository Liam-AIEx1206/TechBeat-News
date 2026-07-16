import paramiko
import os
import tarfile
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def make_tarfile(output_filename, source_dir):
    print(f"Creating archive {output_filename}...")
    def exclude_func(tarinfo):
        name = tarinfo.name.replace('\\\\', '/').replace('\\', '/')
        if name.startswith('./'):
            name = name[2:]
        
        # Exclude local environment files to prevent overriding server env variables
        if name.endswith('.env') or name.endswith('.env.local') or name.endswith('.env.production') or name.endswith('.env.development'):
            return None
            
        excludes = ['.git', 'node_modules', '.next', '__pycache__', '.venv', 'playwright_cache', 'my-video', 'oh-my-ppt', '.pytest_cache', '.conda', '.agents', '.gemini', '.cache', '.npm', 'scripts']
        if any(f"/{ex}/" in f"/{name}/" or name.endswith(f"/{ex}") for ex in excludes):
            return None
        if name.endswith('.tar.gz') or name.endswith('.zip'):
            return None
        # Exclude temporary diagnostic scripts
        temp_scripts = ['find_large_files.py', 'check_my_video_subdirs.py', 'check_app_subdirs.py', 'check_remote_upload.py', 'check_build_logs.py', 'test_tar_size.py', 'check_logs_exists.py']
        if any(name.endswith(s) for s in temp_scripts):
            return None
        # slide-engine: CHỈ giữ data/templates (mẫu), loại session/cache/db/out nặng
        se_heavy = (
            'slide-engine/data/storage', 'slide-engine/data/downloads',
            'slide-engine/data/exports', 'slide-engine/data/uploads',
            'slide-engine/data/html-thumbnails', 'slide-engine/data/styles-dev',
            'slide-engine/data/skills-dev', 'slide-engine/data/ohmyppt-export',
            'slide-engine/out', 'slide-engine/boot.log',
        )
        if name.startswith(se_heavy):
            return None
        if name.startswith('slide-engine/data/') and ('.db' in name or '.sqlite' in name):
            return None
        return tarinfo

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir), filter=exclude_func)
    print("Archive created.")

def deploy():
    hostname = '138.199.233.75'
    username = 'aiteam'
    password = '61bWVquJdiftUFkRgptioKt9AP6fJbnA'
    
    tar_name = 'TechBeat-News-Deploy.tar.gz'
    make_tarfile(tar_name, '.')

    print(f"Connecting to {hostname} as {username}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname, port=22, username=username, password=password, timeout=10)
        print("Connected successfully!")
        
        print("Uploading archive via SFTP...")
        sftp = client.open_sftp()
        sftp.put(tar_name, tar_name)
        sftp.close()
        print("Upload complete!")
        
        commands = [
            "if [ -d projects/pinkyne-hub/DailyByte-News ]; then find projects/pinkyne-hub/DailyByte-News -mindepth 1 -maxdepth 1 ! -name 'my-video' -exec rm -rf {} +; else mkdir -p projects/pinkyne-hub/DailyByte-News; fi",
            f"tar -xzf {tar_name} -C projects/pinkyne-hub/DailyByte-News --strip-components=1",
            f"rm {tar_name}",
            "cd projects/pinkyne-hub/DailyByte-News && cp .env.compose.example .env",
            "cd projects/pinkyne-hub/DailyByte-News && sed -i 's|NEXTAUTH_URL=http://localhost:3000|NEXTAUTH_URL=https://xnew.labpinky.com|g' .env",
            "cd projects/pinkyne-hub/DailyByte-News && echo 'TUNNEL_TOKEN=eyJhIjoiYzJlZTU3NWRkMmE4MWMxMjU0MWUzMzA5YTFjOTA5MjEiLCJ0IjoiN2QyYmQ1MTUtNzA2ZC00YWI5LTk5YWItMDBiZTIzZWZmYTE2IiwicyI6IlpETmhZMlkzTTJJdFpEVmtaaTAwT1dRNExUbG1aVEl0WVdJMU5HSmpOMlprTkRSayJ9' >> .env",
            f"cd projects/pinkyne-hub/DailyByte-News && echo '{password}' | sudo -S docker compose up -d --build"
        ]
        
        for cmd in commands:
            print(f"\\nExecuting: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            for line in iter(stdout.readline, ""):
                print(line, end="")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                print(f"Command failed with exit status {exit_status}")
                for err_line in iter(stderr.readline, ""):
                    print(err_line, end="")
            else:
                print("Command succeeded.")
                
        print("\nDeployment completed successfully!")
        
        print("\nSyncing local environment variables to the remote server...")
        from scripts.update_remote_env import run as update_remote_env
        update_remote_env()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    deploy()
