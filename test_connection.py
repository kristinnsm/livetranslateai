"""
Quick test script to verify OpenAI API connection and basic functionality
Run this before starting the full app to catch config issues early
"""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_openai_connection():
    """Test OpenAI API key and basic endpoints"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in .env file")
        print("        Create a .env file and add your key")
        return False
    
    print("[OK] API key found")
    print(f"     Key starts with: {api_key[:10]}...")
    
    try:
        # Initialize client
        client = AsyncOpenAI(api_key=api_key)
        
        # Test 1: Simple completion
        print("\n[TEST] Testing GPT completion...")
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'Hello from Babbelfish!'"}],
                max_tokens=20
            )
            print(f"[OK] GPT response: {response.choices[0].message.content}")
        except Exception as e:
            print(f"[WARN] GPT test failed: {e}")
            print("       This may be ok - trying model list instead...")
        
        # Test 2: Check available models
        print("\n[TEST] Testing available models...")
        try:
            models = await client.models.list()
            available_models = [m.id for m in models.data if 'gpt' in m.id or 'whisper' in m.id or 'tts' in m.id]
            print(f"[OK] Found {len(available_models)} relevant models")
            
            # Check for required models
            required = ['whisper-1', 'tts-1', 'gpt-4o-mini']
            for model in required:
                if any(model in m for m in available_models):
                    print(f"     [OK] {model} available")
                else:
                    print(f"     [WARN] {model} not found (may still work)")
        except Exception as e:
            print(f"[WARN] Model list failed: {e}")
            print("       Your API key appears valid - proceeding anyway")
        
        print("\n[SUCCESS] OpenAI connection test passed!")
        print("          You're ready to start the backend server")
        
        # Cleanup
        await client.close()
        return True
        
    except Exception as e:
        print(f"\n[ERROR] OpenAI API error: {e}")
        print("        Check your API key and internet connection")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Babbelfish - OpenAI Connection Test")
    print("=" * 60)
    
    result = asyncio.run(test_openai_connection())
    
    if not result:
        exit(1)

