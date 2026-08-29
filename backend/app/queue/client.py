from functools import lru_cache
from typing import Protocol

from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.queue.messages import JobMessage


class QueueError(RuntimeError):
    """Raised when a queue operation cannot be completed."""


class QueueClient(Protocol):
    async def enqueue(self, message: JobMessage) -> None: ...

    async def dequeue(self, timeout_seconds: int = 5) -> JobMessage | None: ...


class RedisQueue:
    def __init__(self, settings: Settings) -> None:
        self.queue_name = "video-translator:jobs"
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    async def enqueue(self, message: JobMessage) -> None:
        try:
            await self.client.rpush(self.queue_name, message.model_dump_json())
        except Exception as exc:
            raise QueueError("Unable to enqueue job message") from exc

    async def dequeue(self, timeout_seconds: int = 5) -> JobMessage | None:
        try:
            item = await self.client.blpop(self.queue_name, timeout=timeout_seconds)
            if item is None:
                return None
            return JobMessage.model_validate_json(item[1])
        except Exception as exc:
            raise QueueError("Unable to dequeue job message") from exc

    async def close(self) -> None:
        await self.client.aclose()


@lru_cache
def get_queue() -> RedisQueue:
    return RedisQueue(get_settings())
