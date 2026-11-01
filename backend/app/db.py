from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from .core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
options = {"pool_pre_ping": True}
if settings.database_url in ("sqlite://", "sqlite:///:memory:"):
    options["poolclass"] = StaticPool
engine = create_engine(settings.database_url, connect_args=connect_args, **options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase):
    pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
