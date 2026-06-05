import os
from dotenv import load_dotenv

load_dotenv()

USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
MODEL_NAME = os.getenv("MODEL", "qwen2.5:3b")
DATABASE_URL = os.getenv("DATABASE_URL")

DEFAULT_CUSTOMER_NAME = "Khách demo AI Sales Brain"
WELCOME_MESSAGE = "Chào bạn, mình là chatbot AI demo. Bạn muốn hỏi gì?"

APP_HEIGHT = 550
CHAT_FRAME_HEIGHT = 550