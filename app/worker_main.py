import asyncio
from app.config import Settings
from app.db import create_schema, make_session_factory
from app.repository import NotificationRepository
from app.worker import Worker

async def main():
    settings=Settings();create_schema(settings.database_url);await Worker(NotificationRepository(make_session_factory(settings.database_url)),settings).run_forever()

if __name__ == "__main__": asyncio.run(main())
