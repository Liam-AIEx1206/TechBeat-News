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
    
    test_code = """
import sys
sys.path.insert(0, '/app')

import asyncio
from pathlib import Path
from routers.build import _openai_tts_to_wav

async def main():
    # Let's fire 10 concurrent requests to simulate the parallel rendering pipeline
    text = "Xin chào, đây là thử nghiệm tải đồng thời giọng nói nhân tạo."
    target_dir = Path("/tmp/test_concurrent_tts")
    target_dir.mkdir(exist_ok=True)
    
    async def run_one(i):
        target_path = target_dir / f"test_{i}.wav"
        # Alternate voices
        voice = "nova" if i % 2 == 0 else "onyx"
        try:
            success = await _openai_tts_to_wav(text, target_path, voice_name=voice)
            return i, success, None
        except Exception as e:
            import traceback
            return i, False, traceback.format_exc()
            
    tasks = [run_one(i) for i in range(15)]
    results = await asyncio.gather(*tasks)
    
    for i, success, err in results:
        print(f"Task {i}: success={success}, err={err}")

asyncio.run(main())
"""
    import base64
    encoded_code = base64.b64encode(test_code.encode('utf-8')).decode('utf-8')
    
    cmd_write = f"docker exec -i dailybyte-backend python -c \"import base64; open('/tmp/test_tts.py', 'w').write(base64.b64decode('{encoded_code}').decode('utf-8'))\""
    stdin, stdout, stderr = client.exec_command(cmd_write)
    stdout.read()
    
    cmd_run = "docker exec -i -w /app dailybyte-backend python /tmp/test_tts.py"
    stdin, stdout, stderr = client.exec_command(cmd_run)
    print("Run output:")
    print(stdout.read().decode('utf-8'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
