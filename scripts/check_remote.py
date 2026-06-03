import paramiko

def check_remote_status():
    hostname = '138.199.233.75'
    username = 'aiteam'
    password = '61bWVquJdiftUFkRgptioKt9AP6fJbnA'
    
    print(f"Connecting to {hostname} via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(hostname, port=22, username=username, password=password, timeout=10)
        print("Connected successfully!\n")
        
        # Command 1: Check active git commit hash on server
        cmd_git = "cd TechBeat-News && git log -n 1 --oneline"
        print(f"Executing: {cmd_git}")
        stdin, stdout, stderr = client.exec_command(cmd_git)
        print("--- Active Git Commit ---")
        print(stdout.read().decode('utf-8').strip())
        print(stderr.read().decode('utf-8').strip())
        print("-------------------------\n")
        
        # Command 2: Check docker compose status and container update times
        cmd_docker = "cd TechBeat-News && docker compose ps"
        print(f"Executing: {cmd_docker}")
        stdin, stdout, stderr = client.exec_command(cmd_docker)
        print("--- Running Docker Containers ---")
        print(stdout.read().decode('utf-8').strip())
        print(stderr.read().decode('utf-8').strip())
        print("---------------------------------\n")

    except Exception as e:
        print(f"Error checking remote status: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    check_remote_status()
