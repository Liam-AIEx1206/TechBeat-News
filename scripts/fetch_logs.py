import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('138.199.233.75', username='aiteam', password='61bWVquJdiftUFkRgptioKt9AP6fJbnA')

commands = [
    "cd TechBeat-News",
    "echo '--- TRẠNG THÁI DOCKER ---'",
    "sudo -S docker compose ps",
    "echo '\\n--- LOG FRONTEND (20 dòng cuối) ---'",
    "sudo -S docker compose logs --tail 20 frontend",
    "echo '\\n--- LOG BACKEND (20 dòng cuối) ---'",
    "sudo -S docker compose logs --tail 20 backend"
]

stdin, stdout, stderr = client.exec_command(" && ".join(commands))
stdin.write('61bWVquJdiftUFkRgptioKt9AP6fJbnA\n')
stdin.flush()

for line in stdout:
    sys.stdout.buffer.write(line.encode('utf-8'))
for line in stderr:
    sys.stderr.buffer.write(line.encode('utf-8'))
client.close()
