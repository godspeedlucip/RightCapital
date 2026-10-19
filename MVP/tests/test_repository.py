from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from app.db import make_engine
from app.models import Base, Status, utcnow
from app.repository import NotificationRepository, IdempotencyConflict

def repo():
    engine=make_engine("sqlite+pysqlite:///:memory:");Base.metadata.create_all(engine);return NotificationRepository(sessionmaker(bind=engine,expire_on_commit=False))

def payload(url="https://vendor.test"):
    return {"provider":"crm","event_type":"paid","target":{"url":url,"method":"POST","headers":{},"body":{"id":"1"}},"idempotency_key":"payment-1"}

def test_idempotency_reuses_and_conflicts():
    r=repo();first=r.create(payload(),5);assert r.create(payload(),5).id==first.id
    try:r.create(payload("https://other.test"),5);assert False
    except IdempotencyConflict:pass

def test_claim_and_expired_lease_recovery():
    r=repo();n=r.create(payload(),5);now=utcnow();claimed=r.claim_next(now,now+timedelta(seconds=1));assert claimed.status==Status.DELIVERING
    assert r.recover_expired_leases(now+timedelta(seconds=2))==1
