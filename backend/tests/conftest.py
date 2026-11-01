import os
os.environ["DATABASE_URL"]="sqlite://"
os.environ["LLM_MODEL"]=""
os.environ["AEGIS_API_KEY"]=""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base,engine
@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine);Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:yield c
