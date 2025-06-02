import smtplib
from dotenv import load_dotenv
import os

load_dotenv("config.env")

try:
    with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
        print("SMTP login successful!")
except Exception as e:
    print(f"SMTP failed: {str(e)}")