import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    DEBUG = os.getenv("DEBUG") == "True"

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "stream:onboarding-events")
    REDIS_CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "grp:avatar-persona")
    REDIS_CONSUMER_NAME = os.getenv("REDIS_CONSUMER_NAME", "avatar-worker-1")
    REDIS_BLOCK_MS = int(os.getenv("REDIS_BLOCK_MS", "5000"))
    REDIS_COUNT = int(os.getenv("REDIS_COUNT", "20"))

    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "64"))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4.1-mini-2025-04-14")
    CHAT_TOP_K = int(os.getenv("CHAT_TOP_K", "3"))

    # 프로젝트 정책상 사용 가능한 모델만 허용한다.
    ALLOWED_CHAT_MODELS = {
        "gpt-5-codex",
        "gpt-5-2025-08-07",
        "gpt-5-chat-latest",
        "gpt-4.1-2025-04-14",
        "gpt-4o-2024-05-13",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-11-20",
        "o3-2025-04-16",
        "o1-preview-2024-09-12",
        "o1-2024-12-17",
        "gpt-5-mini-2025-08-07",
        "gpt-5-nano-2025-08-07",
        "gpt-4.1-mini-2025-04-14",
        "gpt-4.1-nano-2025-04-14",
        "gpt-4o-mini-2024-07-18",
        "o4-mini-2025-04-16",
        "o1-mini-2024-09-12",
        "codex-mini-latest",
    }


settings = Settings()
