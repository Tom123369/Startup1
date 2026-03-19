import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_resend():
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")
    to_email = "mauryabhatia0007@gmail.com" # From the user's screenshot
    
    print(f"Testing Resend with API Key: {api_key[:10]}...")
    print(f"From: {from_email}")
    print(f"To: {to_email}")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"PredictIQ <{from_email}>",
                    "to": [to_email],
                    "subject": "Resend Test",
                    "html": "<p>This is a test</p>"
                }
            )
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_resend())
