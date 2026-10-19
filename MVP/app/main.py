from app.config import Settings
from app.db import create_schema, make_session_factory
from app.api import create_app
from app.repository import NotificationRepository

settings=Settings()
create_schema(settings.database_url)
repo=NotificationRepository(make_session_factory(settings.database_url))
app=create_app(repo,settings)
