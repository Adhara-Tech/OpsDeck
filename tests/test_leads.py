import pytest
from src.models import User
from src import db

@pytest.fixture(scope='function')
def auth_user(app):
    with app.app_context():
        # Check if user exists to avoid unique constraint error if DB isn't cleaned
        user = User.query.filter_by(email='test_leads@example.com').first()
        if not user:
            user = User(name='Test User', email='test_leads@example.com', role='admin')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
        return user

def test_render_new_lead_form(client, auth_user):
    # Log in
    client.post('/login', data={'email': 'test_leads@example.com', 'password': 'password'})
    
    # This should trigger the TemplateSyntaxError
    # We expect 500 or exception depending on how flask handles it in test mode.
    # But for reproduction, we just want to see it fail or error out.
    response = client.get('/leads/new')
    assert response.status_code == 200
    assert b'New Requirement' in response.data
