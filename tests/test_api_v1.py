from src.models import User

def test_api_security(client, app):
    """
    Test API security and functionality.
    """
    # 1. Access without token -> 401
    response = client.get('/api/v1/users')
    assert response.status_code == 401
    assert b'Missing' in response.data or b'missing' in response.data

    # Setup User with Token
    api_token = "test-token-123"
    with app.app_context():
        # Create user manually to avoid auth_client dependency logic if any
        # Assuming existing users or creating new one
        db = app.extensions['sqlalchemy']
        user = User(name="API User", email="api@test.com")
        user.api_token = api_token 
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # 2. Access with Invalid Token -> 401
    response = client.get('/api/v1/users', headers={'Authorization': 'Bearer invalid-token'})
    assert response.status_code == 401

    # 3. Access with Valid Token -> 200
    headers = {'Authorization': f'Bearer {api_token}'}
    response = client.get('/api/v1/users', headers=headers)
    assert response.status_code == 200
    # Check if we get a list (pagination format usually has 'items' or directly list depending on config)
    # Flask-Smorest typically returns list if many=True? Or paginated object?
    # Helper uses @blueprint.paginate(Page)
    # default Page pagination returns:
    # { "items": [...], "meta": {...} } or list?
    # Inspect response structure
    data = response.get_json()
    # It seems flask-smorest pagination defaults might wrap it. 
    # But let's check basic success first.

    # 4. Detail Endpoint
    response = client.get(f'/api/v1/users/{user_id}', headers=headers)
    assert response.status_code == 200
    assert response.json['name'] == "API User"
