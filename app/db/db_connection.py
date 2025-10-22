from app.utils.logger import logger
from sqlalchemy import event
import time
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator
from dotenv import load_dotenv
import os
from app.utils.logger import COLORS

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
SQLALCHEMY_ECHO = os.getenv(
    "SQLALCHEMY_ECHO", "False").lower() in ("1", "true", "yes")


DB_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_async_engine(url=DB_URL, echo=False)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as async_session:
        yield async_session


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_s = time.perf_counter() - context._query_start_time
    total_ms = total_s * 1000
    # Green <100ms, red otherwise
    color = "\033[92m" if total_ms < 100 else "\033[91m"
    logger.info(
        f"{color}[DB EXECUTION TIME: {total_ms:.3f} ms]{COLORS['RESET']}\n{statement}\n")
