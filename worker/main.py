import asyncio
import logging

from app.config import get_settings
from app.db.session import session_factory
from app.queue.client import QueueError, get_queue
from app.storage.s3 import S3Storage
from worker.pipeline import process_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_forever() -> None:
    settings = get_settings()
    queue = get_queue()
    storage = S3Storage(settings)
    while True:
        try:
            message = await queue.dequeue(timeout_seconds=5)
        except QueueError:
            logger.exception("Queue read failed")
            await asyncio.sleep(2)
            continue
        if message is None:
            continue
        async with session_factory() as db:
            await process_message(message, db, queue, storage, settings)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
