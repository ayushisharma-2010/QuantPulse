"""
Test Groq API key directly
"""
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv('GROQ_API_KEY')
print(f"API Key loaded: {api_key[:20]}...{api_key[-10:]}")
print(f"API Key length: {len(api_key)}")

try:
    client = Groq(api_key=api_key)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Say hello in one word"}
        ],
        max_tokens=10
    )
    
    print(f"\n✅ API Key is VALID!")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"\n❌ API Key is INVALID or there's an error:")
    print(f"Error: {e}")
