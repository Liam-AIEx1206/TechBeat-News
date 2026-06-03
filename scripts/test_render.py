import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('138.199.233.75', username='aiteam', password='61bWVquJdiftUFkRgptioKt9AP6fJbnA')

commands = [
    "cd TechBeat-News",
    "echo '61bWVquJdiftUFkRgptioKt9AP6fJbnA' | sudo -S docker exec -w /data/my-video dailybyte-backend npx --yes hyperframes@0.6.20 render"
]

stdin, stdout, stderr = client.exec_command(" && ".join(commands))
print(stdout.read().decode())
print(stderr.read().decode())
client.close()
