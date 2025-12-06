#!/usr/bin/env python3
"""Quick test of parallel processing"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()

async def test_async_claude():
    """Test async Claude API"""
    print("Testing AsyncAnthropic...")

    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No API key found")
        return

    client = AsyncAnthropic(api_key=api_key)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'test successful'"}]
        )
        print(f"✓ Response: {response.content[0].text}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_parallel_calls():
    """Test multiple parallel calls"""
    print("\nTesting parallel calls...")

    api_key = os.getenv('CLAUDE_API_KEY')
    client = AsyncAnthropic(api_key=api_key)

    async def make_call(n):
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=20,
            messages=[{"role": "user", "content": f"Say: call {n}"}]
        )
        return response.content[0].text

    try:
        results = await asyncio.gather(
            make_call(1),
            make_call(2),
            make_call(3)
        )

        for i, result in enumerate(results, 1):
            print(f"  Call {i}: {result}")

        print("✓ Parallel calls successful")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("="*50)
    print("Async Claude API Test")
    print("="*50 + "\n")

    await test_async_claude()
    await test_parallel_calls()

    print("\n" + "="*50)
    print("All tests complete!")
    print("="*50)

if __name__ == '__main__':
    asyncio.run(main())
