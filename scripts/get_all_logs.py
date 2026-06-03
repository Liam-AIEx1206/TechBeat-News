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
        
        containers = ['frontend', 'backend', 'tunnel']
        for container in containers:
            print(f"\n==================== {container.upper()} LOGS ====================")
            cmd = f"cd TechBeat-News && docker compose logs --tail 40 {container}"
            stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
            for line in iter(stdout.readline, ""):
                print(line, end="")
            sys.stdout.flush()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()
    finally:
        client.close()

if __name__ == '__main__':
    run()
