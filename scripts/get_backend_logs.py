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
        
        # Get backend logs (last 2000 lines)
        cmd = "cd TechBeat-News && docker compose logs --tail 2000 backend"
        print(f"Running command: {cmd}")
        sys.stdout.flush()
        
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        
        filtered_lines = []
        for line in iter(stdout.readline, ""):
            # Filter out the container health checks to focus on real app logs
            if "GET /health" not in line and "health" not in line.lower():
                filtered_lines.append(line)
        
        print("\n--- FILTERED BACKEND LOGS (excluding health checks) ---")
        # Print the last 100 non-healthcheck lines
        for line in filtered_lines[-150:]:
            print(line, end="")
        sys.stdout.flush()
        
        exit_status = stdout.channel.recv_exit_status()
        print(f"\nCommand finished with exit status: {exit_status}")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()
    finally:
        client.close()

if __name__ == '__main__':
    run()
