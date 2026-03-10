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


settings = Settings()
