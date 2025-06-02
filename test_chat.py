#!/usr/bin/env python3
"""
Simple test script for the streaming chat API
"""

import asyncio
import aiohttp
import json
import sys


async def test_streaming_chat():
    """Test the streaming chat endpoint"""
    
    url = "http://localhost:8000/api/v1/chat/stream"
    
    # Test message
    message = input("Enter your message (or press Enter for default): ").strip()
    if not message:
        message = "Tell me a short joke"
    
    payload = {"message": message}
    
    print(f"\nSending: {message}")
    print("Response:")
    print("-" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    print(f"Error: HTTP {response.status}")
                    print(await response.text())
                    return
                
                full_response = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            
                            if 'content' in data:
                                content = data['content']
                                print(content, end='', flush=True)
                                full_response += content
                            elif 'done' in data and data['done']:
                                print("\n" + "-" * 50)
                                print("Stream completed!")
                                break
                            elif 'error' in data:
                                print(f"\nError: {data['error']}")
                                break
                        except json.JSONDecodeError:
                            continue
                
                print(f"\nFull response: {full_response}")
                
        except aiohttp.ClientError as e:
            print(f"Connection error: {e}")
            print("Make sure the server is running on http://localhost:8000")
        except KeyboardInterrupt:
            print("\nInterrupted by user")


async def test_health_check():
    """Test the health check endpoint"""
    
    url = "http://localhost:8000/health"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Health check: {data}")
                    return True
                else:
                    print(f"Health check failed: HTTP {response.status}")
                    return False
        except aiohttp.ClientError as e:
            print(f"Health check error: {e}")
            return False


async def main():
    print("Simple Chat API Test")
    print("=" * 50)
    
    # Test health check first
    print("Testing health check...")
    if not await test_health_check():
        print("Server might not be running. Start it with:")
        print("python -m uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("\nTesting streaming chat...")
    await test_streaming_chat()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!") 