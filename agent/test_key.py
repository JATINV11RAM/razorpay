import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('GEMINI_API_KEY')
print(f"Length: {len(key) if key else 0}")
print(f"Start: {key[:8] if key else None}")