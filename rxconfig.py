from typing import Optional
import reflex as rx


class AsyncDBConfig(rx.Config):
    async_db_url: Optional[str] = "sqlite+aiosqlite:///reflex.db"


config = AsyncDBConfig(
    app_name="repro_db_async",
)
