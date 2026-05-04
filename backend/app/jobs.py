import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal

from fastapi import WebSocket

JobStatus = Literal["pending", "indexing", "indexed", "answering", "done", "error"]


@dataclass
class Job:
    id: str
    query: str
    article_title: str | None
    status: JobStatus = "pending"
    error: str | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


_jobs: dict[str, Job] = {}


def create_job(query: str, article_title: str | None) -> Job:
    job = Job(id=str(uuid.uuid4()), query=query, article_title=article_title)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


async def push(job: Job, frame: dict) -> None:
    await job.queue.put(frame)


async def push_status(job: Job, status: JobStatus, **extra) -> None:
    if "type" in extra or "status" in extra:
        raise ValueError("'type' and 'status' are reserved frame keys")
    job.status = status
    await push(job, {"type": "status", "status": status, **extra})


async def push_error(job: Job, message: str) -> None:
    job.status = "error"
    job.error = message
    await push(job, {"type": "error", "message": message})


async def push_token(job: Job, text: str) -> None:
    await push(job, {"type": "token", "text": text})


async def close(job: Job) -> None:
    await push(job, {"type": "close"})
    # Leave job in registry briefly so late connections see final status; in v1 we never GC.


async def run_websocket(job: Job, ws: WebSocket) -> None:
    await ws.accept()
    while True:
        frame = await job.queue.get()
        await ws.send_json(frame)
        if frame["type"] == "close":
            break
    await ws.close()
