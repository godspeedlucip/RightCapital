from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.api import create_app
from app.config import Settings
from app.db import make_engine
from app.models import Base
from app.repository import NotificationRepository

def client():
    e=make_engine("sqlite+pysqlite:///:memory:");Base.metadata.create_all(e);r=NotificationRepository(sessionmaker(bind=e,expire_on_commit=False));s=Settings(DATABASE_URL="sqlite://",INTERNAL_AUTH_TOKEN="secret");return TestClient(create_app(r,s))

def body(url="https://vendor.test",idem=None):
    p={"provider":"crm","event_type":"paid","target":{"url":url,"method":"POST","headers":{},"body":{"id":"1"}}}
    if idem:p["idempotency_key"]=idem
    return p

def test_create_returns_202_and_status():
    c=client();r=c.post("/v1/notifications",json=body(),headers={"Authorization":"Bearer secret"});assert r.status_code==202;assert r.json()["status"]=="PENDING"

def test_rejects_header_override():
    c=client();p=body();p["target"]["headers"]={"Idempotency-Key":"bad"};assert c.post("/v1/notifications",json=p,headers={"Authorization":"Bearer secret"}).status_code==422

def test_idempotency_conflict_is_409():
    c=client();h={"Authorization":"Bearer secret"};assert c.post("/v1/notifications",json=body("https://a.test","x"),headers=h).status_code==202;assert c.post("/v1/notifications",json=body("https://b.test","x"),headers=h).status_code==409
