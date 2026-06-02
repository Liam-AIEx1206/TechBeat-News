import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('138.199.233.75', username='aiteam', password='61bWVquJdiftUFkRgptioKt9AP6fJbnA')

import sys
commands = [
    "cd TechBeat-News",
    "git pull origin ver2",
    "echo '61bWVquJdiftUFkRgptioKt9AP6fJbnA' | sudo -S docker compose up -d --build frontend backend"
]

stdin, stdout, stderr = client.exec_command(" && ".join(commands))
for line in stdout:
    sys.stdout.buffer.write(line.encode('utf-8'))
for line in stderr:
    sys.stderr.buffer.write(line.encode('utf-8'))
client.close()
