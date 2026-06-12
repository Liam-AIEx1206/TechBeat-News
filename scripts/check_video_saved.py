import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('138.199.233.75', port=22, username='aiteam', password='61bWVquJdiftUFkRgptioKt9AP6fJbnA', timeout=10)

cmds = [
    "docker inspect dailybyte-backend --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}\n{{end}}'",
    "ls -lht /home/aiteam/TechBeat-News/my-video/history/users/ 2>/dev/null",
    "ls /home/aiteam/TechBeat-News/my-video/renders/*.mp4 2>/dev/null | tail -3",
]

for cmd in cmds:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(f"=== {cmd[:70]} ===")
    print(out or err or '(empty)')

client.close()
