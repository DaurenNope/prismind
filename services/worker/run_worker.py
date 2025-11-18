from __future__ import annotations

import argparse
import os

from redis import Redis
from rq import Connection, Queue, Worker

from services.common.job_queue import get_queues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an RQ worker for Prismind queues")
    parser.add_argument(
        "--queue",
        "-q",
        action="append",
        required=True,
        help="Queue name to listen on (can be provided multiple times)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    queue_names = args.queue
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    queues = get_queues(queue_names)

    with Connection(connection):
        worker = Worker(queues)
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
