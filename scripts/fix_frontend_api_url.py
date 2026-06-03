import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run():
    hostname = '138.199.233.75'
    username = 'aiteam'
    password = '61bWVquJdiftUFkRgptioKt9AP6fJbnA'
    
    print("Connecting to remote server...")
    sys.stdout.flush()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname, port=22, username=username, password=password, timeout=10)
        print("Connected!")
        sys.stdout.flush()
        
        # Modify remote .env to fix NEXT_PUBLIC_API_URL
        print("Updating NEXT_PUBLIC_API_URL in remote .env...")
        cmd_sed = "sed -i 's|NEXT_PUBLIC_API_URL=http://localhost:8000|NEXT_PUBLIC_API_URL=/api-backend|g' TechBeat-News/.env"
        stdin, stdout, stderr = client.exec_command(cmd_sed)
        stdout.read() # Wait for completion
        
        # Verify the file was updated
        stdin, stdout, stderr = client.exec_command("grep NEXT_PUBLIC_API_URL TechBeat-News/.env")
        print(f"Current setting in remote .env: {stdout.read().decode('utf-8').strip()}")
        
        # Rebuild frontend
        print("Rebuilding frontend container with new API URL...")
        cmd_build = f"cd TechBeat-News && echo '{password}' | sudo -S docker compose up -d --build frontend"
        stdin, stdout, stderr = client.exec_command(cmd_build, get_pty=True)
        for line in iter(stdout.readline, ""):
            print(line, end="")
            sys.stdout.flush()
            
        exit_status = stdout.channel.recv_exit_status()
        print(f"\nFrontend rebuild finished with status: {exit_status}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()
    finally:
        client.close()

if __name__ == '__main__':
    run()
