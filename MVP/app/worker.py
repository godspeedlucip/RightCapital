import asyncio
from datetime import timedelta
from app.config import Settings
from app.delivery import DeliveryClient, classify
from app.models import Status, utcnow
from app.repository import NotificationRepository

class Worker:
    def __init__(self,repo:NotificationRepository,settings:Settings,client:DeliveryClient|None=None):self.repo=repo;self.settings=settings;self.client=client or DeliveryClient(settings.request_timeout.total_seconds())
    async def run_once(self)->bool:
        now=utcnow();self.repo.recover_expired_leases(now);row=self.repo.claim_next(now,now+self.settings.lease_duration)
        if not row:return False
        attempt=row.attempt_count+1;status,error=await self.client.send(row);outcome=classify(status,error)
        if outcome.success:self.repo.mark_delivered(row.id,attempt,utcnow())
        elif outcome.retry and attempt < row.max_attempts:self.repo.mark_retry(row.id,attempt,utcnow()+self.settings.retry_delay,outcome.code,outcome.message)
        else:self.repo.mark_failed(row.id,attempt,outcome.code,outcome.message)
        return True
    async def run_forever(self):
        while True:
            await self.run_once();await asyncio.sleep(self.settings.poll_interval.total_seconds())
