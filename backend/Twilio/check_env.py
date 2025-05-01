import os

from dotenv import load_dotenv

load_dotenv()

print("AWS_REGION:", repr(os.getenv("AWS_REGION")))
print("YOUR_SERVER_URL:", repr(os.getenv("YOUR_SERVER_URL")))
