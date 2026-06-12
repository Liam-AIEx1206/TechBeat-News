import paramiko
import sys

hostname = '138.199.233.75'
username = 'aiteam'
password = '61bWVquJdiftUFkRgptioKt9AP6fJbnA'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname, port=22, username=username, password=password, timeout=10)
    print("Connected successfully!")
    
    # Run docker exec dailybyte-backend env
    cmd = "docker exec dailybyte-backend env"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("=== CONTAINER ENV ===")
    print(stdout.read().decode('utf-8'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
