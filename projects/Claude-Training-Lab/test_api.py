import os
import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"API Key loaded: {api_key[:20]}...")

try:
    proxy_url = "http://10.206.63.11:3128"

    client = Anthropic(
        api_key=api_key,
        http_client=httpx.Client(proxy=proxy_url, timeout=60.0),
    )

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'API is working' if you can read this"}
        ],
    )

    print("API Connection successful!")
    print(f"Response: {message.content[0].text}")

except Exception as e:
    print(f"API Connection failed: {e}")