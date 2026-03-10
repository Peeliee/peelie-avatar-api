from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import text

from apps.avatar.service import AvatarIngestService, build_payload_from_stream
from core.config import settings
from core.db import Base, async_session_factory, engine

# Ensure model metadata is imported before create_all is called.
from apps.avatar import models as _avatar_models  # noqa: F401


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("avatar-worker")


def has_stream_messages(messages: list[tuple[str, list[tuple[str, dict[str, str]]]]]) -> bool:
    return bool(messages) and any(stream_messages for _, stream_messages in messages)


async def ensure_tables() -> None:
    async with engine.begin() as conn:
        # pgvector 타입이 필요한 테이블 생성 전에 extension을 보장한다.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(
            name=settings.REDIS_STREAM_KEY,
            groupname=settings.REDIS_CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
        logger.info("consumer group created: %s", settings.REDIS_CONSUMER_GROUP)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def process_messages(redis: Redis, messages: list[tuple[str, list[tuple[str, dict[str, str]]]]]) -> None:
    for _, stream_messages in messages:
        for message_id, fields in stream_messages:
            raw_event_id = fields.get("event_id", "unknown")
            raw_user_id = fields.get("user_id", "unknown")
            try:
                event = build_payload_from_stream(fields)
                async with async_session_factory() as session:
                    service = AvatarIngestService(session)
                    created = await service.ingest(event)
                    await session.commit()

                await redis.xack(settings.REDIS_STREAM_KEY, settings.REDIS_CONSUMER_GROUP, message_id)
                logger.info(
                    "processed and acked: record_id=%s event_id=%s user_id=%s created=%s",
                    message_id,
                    event.event_id,
                    event.user_id,
                    created,
                )
            except Exception:
                logger.exception(
                    "processing failed (not acked): record_id=%s event_id=%s user_id=%s",
                    message_id,
                    raw_event_id,
                    raw_user_id,
                )


async def worker_loop() -> None:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await ensure_tables()
    await ensure_group(redis)

    logger.info(
        "worker started: stream=%s group=%s consumer=%s",
        settings.REDIS_STREAM_KEY,
        settings.REDIS_CONSUMER_GROUP,
        settings.REDIS_CONSUMER_NAME,
    )

    while True:
        pending_messages = await redis.xreadgroup(
            groupname=settings.REDIS_CONSUMER_GROUP,
            consumername=settings.REDIS_CONSUMER_NAME,
            streams={settings.REDIS_STREAM_KEY: "0"},
            count=settings.REDIS_COUNT,
        )
        if has_stream_messages(pending_messages):
            await process_messages(redis, pending_messages)
            continue

        new_messages = await redis.xreadgroup(
            groupname=settings.REDIS_CONSUMER_GROUP,
            consumername=settings.REDIS_CONSUMER_NAME,
            streams={settings.REDIS_STREAM_KEY: ">"},
            count=settings.REDIS_COUNT,
            block=settings.REDIS_BLOCK_MS,
        )
        if not has_stream_messages(new_messages):
            await asyncio.sleep(0.05)
            continue

        await process_messages(redis, new_messages)


if __name__ == "__main__":
    asyncio.run(worker_loop())
