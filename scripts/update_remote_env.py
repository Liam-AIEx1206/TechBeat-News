import paramiko
import sys
import re

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run():
    hostname = '138.199.233.75'
    username = 'aiteam'
    password = '61bWVquJdiftUFkRgptioKt9AP6fJbnA'
    
    print("Reading local backend/.env...")
    env_vars = {}
    try:
        with open('backend/.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip()
    except Exception as e:
        print(f"Error reading local env: {e}")
        return

    # Check key variables we want to copy
    keys_to_copy = ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL', 'FALLBACK_API_KEY', 'FALLBACK_BASE_URL', 'FALLBACK_MODEL', 'GROQ_API_KEY']
    env_content_to_append = ""
    for k in keys_to_copy:
        if k in env_vars:
            env_content_to_append += f"{k}={env_vars[k]}\n"

    # Also read from app/.env.local for Google client credentials
    print("Reading local app/.env.local...")
    app_env_vars = {}
    try:
        with open('app/.env.local', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    app_env_vars[key.strip()] = val.strip()
    except Exception as e:
        print(f"Error reading app/.env.local: {e}")

    google_keys = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'NEXTAUTH_SECRET']
    for k in google_keys:
        if k in app_env_vars:
            env_content_to_append += f"{k}={app_env_vars[k]}\n"

    # Set the NEXTAUTH_URL to the production domain
    env_content_to_append += "NEXTAUTH_URL=https://xnew.labpinky.com\n"

    if not env_content_to_append:
        print("No keys found to copy!")
        return

    print("Connecting to remote server...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname, port=22, username=username, password=password, timeout=10)
        print("Connected successfully!")
        
        # Read existing remote .env to see if keys are already there
        print("Reading remote .env...")
        stdin, stdout, stderr = client.exec_command("cat TechBeat-News/.env")
        remote_env_content = stdout.read().decode('utf-8')
        
        # We will append the new keys
        print("Appending keys to remote .env...")
        sftp = client.open_sftp()
        with sftp.open('TechBeat-News/.env', 'a') as f:
            f.write("\n# Appended by update_remote_env.py\n" + env_content_to_append)
        sftp.close()
        print("Remote .env updated successfully.")

        # Re-run docker compose up -d to pick up new env vars for backend and frontend
        cmd = f"cd TechBeat-News && echo '{password}' | sudo -S docker compose up -d --build backend frontend"
        print(f"Running command: {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")
        
        exit_status = stdout.channel.recv_exit_status()
        print(f"Docker Compose finished with status: {exit_status}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    run()
