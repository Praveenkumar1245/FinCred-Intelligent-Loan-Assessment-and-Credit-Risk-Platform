import pytest
from app import create_app
from models import db, User

@pytest.fixture
def client():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False
    })
    with app.test_client() as client:
        yield client

def test_login_page_renders(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b"FinCred AI" in response.data
    assert b"Sign In" in response.data

def test_demo_user_authentication(client):
    # Test logging in as preloaded applicant
    response = client.post('/login', data={
        "username": "rajesh",
        "password": "Applicant@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Rajesh Sharma!" in response.data

def test_officer_queue_access_protection(client):
    # Without login, should redirect to login
    response = client.get('/officer/queue')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_admin_requirements_page(client):
    # Log in as admin
    client.post('/login', data={
        "username": "admin",
        "password": "Admin@123"
    }, follow_redirects=True)

    response = client.get('/admin/bank-requirements')
    assert response.status_code == 200
    assert b"Bank Requirements" in response.data
