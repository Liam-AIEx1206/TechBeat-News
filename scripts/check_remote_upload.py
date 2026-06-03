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
        
        # Check if the tarball is on the remote server and print its size
        stdin, stdout, stderr = client.exec_command("ls -lh TechBeat-News-Deploy.tar.gz", get_pty=True)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        
        print("ls output:")
        print(out)
        print(err)
        sys.stdout.flush()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.stdout.flush()
    finally:
        client.close()

if __name__ == '__main__':
    run()
