import asyncio
import os
from routers.llm import chat_completions_with_fallback

async def main():
    print("Calling LLM...")
    try:
        stream, p, m = await chat_completions_with_fallback(
            model_kind='composition',
            messages=[{'role':'user','content':'hello'}],
            stream=True
        )
        print(f"Provider: {p}, Model: {m}")
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                print(content, end='', flush=True)
        print("\nDone!")
    except Exception as e:
        print(f"\nError: {type(e).__name__} - {e}")

asyncio.run(main())
