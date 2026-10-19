from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from app.models import Base

def make_engine(url: str):
    if url.startswith("sqlite") and ":memory:" in url:
        return create_engine(url, future=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, future=True)
def make_session_factory(url: str): return sessionmaker(bind=make_engine(url), expire_on_commit=False)
def create_schema(url: str): Base.metadata.create_all(make_engine(url))

if __name__ == "__main__":
    from app.config import Settings
    create_schema(Settings().database_url)
