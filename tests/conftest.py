import pytest
import os
import tempfile
from src import create_app, db, limiter
from src.models import User

@pytest.fixture(scope='session')
def app():
    """Crea una instancia de la aplicación Flask para pruebas (scope session)."""
    # Disable HTTPS for tests
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Crear un directorio temporal para uploads
    tmpdir = tempfile.mkdtemp()
    
    # Define test configuration BEFORE creating the app
    # Use StaticPool to persist in-memory DB across connections/threads
    from sqlalchemy.pool import StaticPool
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "UPLOAD_FOLDER": tmpdir,
        "MFA_ENABLED": False
    }
    
    # Create app with test configuration
    app = create_app(test_config=test_config)
    
    # This works even if the app was initialized with RATELIMIT_ENABLED=True
    limiter.enabled = False

    with app.app_context():
        # Ensure all models are imported before create_all()
        # This prevents "table not found" errors if models are lazily imported
        import src.models  # noqa
        db.create_all()
        yield app
        db.drop_all()
    
    import shutil
    try:
        shutil.rmtree(tmpdir)
    except:
        pass

@pytest.fixture(scope='function')
def init_database(app):
    """
    Fixture que limpia la base de datos para cada test.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Asegurar que el UPLOAD_FOLDER existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        yield db

@pytest.fixture(scope='function')
def client(app, init_database):
    """Un cliente de pruebas para la aplicación."""
    return app.test_client()

@pytest.fixture(scope='function')
def auth_client(client, app):
    """
    Un cliente de pruebas autenticado como administrador.
    """
    with app.app_context():
        admin = User(name='Admin', email='admin@test.com', role='admin')
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()

    client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'password'
    }, follow_redirects=True)
    
    yield client

@pytest.fixture(scope='function')
def user_client(client, app):
    """
    Un cliente de pruebas autenticado como usuario normal.
    """
    with app.app_context():
        # Necesitamos un admin también si la app lo requiere para algo, pero aquí creamos el user
        user = User(name='Test User', email='user@test.com', role='user')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={
        'email': 'user@test.com',
        'password': 'password'
    }, follow_redirects=True)
    
    yield client