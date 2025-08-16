import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from weezy_cbs.main import app
from weezy_cbs.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_create_customer():
    response = client.post(
        "/api/v1/customer-identity/customers",
        json={"first_name": "test", "last_name": "user", "phone_number": "1234567890"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["first_name"] == "test"
    assert data["last_name"] == "user"
    assert data["phone_number"] == "1234567890"
    assert "id" in data
    customer_id = data["id"]

    response = client.get(f"/api/v1/customer-identity/customers/{customer_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["first_name"] == "test"
    assert data["last_name"] == "user"
    assert data["phone_number"] == "1234567890"
    assert data["id"] == customer_id
