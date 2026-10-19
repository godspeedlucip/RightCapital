import asyncio
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from app.config import Settings
from app.db import make_engine
from app.models import Base, Status, utcnow
from app.repository import NotificationRepository
from app.worker import Worker

class FakeClient:
    def __init__(self, statuses): self.statuses=list(statuses);self.calls=0
    async def send(self,row): self.calls+=1;return self.statuses.pop(0),None

def setup_repo():
    e=make_engine("sqlite+pysqlite:///:memory:");Base.metadata.create_all(e);return NotificationRepository(sessionmaker(bind=e,expire_on_commit=False))
def settings(): return Settings(DATABASE_URL="sqlite://",INTERNAL_AUTH_TOKEN="secret",RETRY_DELAY="1s",POLL_INTERVAL="1s")

def test_worker_delivers_after_retry():
    r=setup_repo();row=r.create({"provider":"crm","event_type":"paid","target":{"url":"https://vendor.test","method":"POST","headers":{},"body":{}}},5);w=Worker(r,settings(),FakeClient([503,503,200]))
    async def run():
        await w.run_once();
        # Make retry immediately runnable for the deterministic test.
        current=r.get(row.id);current.next_attempt_at=utcnow()-timedelta(seconds=1)
        with r.session_factory() as s:s.merge(current);s.commit()
        await w.run_once();current=r.get(row.id);current.next_attempt_at=utcnow()-timedelta(seconds=1)
        with r.session_factory() as s:s.merge(current);s.commit()
        await w.run_once()
    asyncio.run(run());assert r.get(row.id).status==Status.DELIVERED;assert r.get(row.id).attempt_count==3
