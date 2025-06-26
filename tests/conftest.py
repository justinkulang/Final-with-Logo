import pytest
from app import app as flask_app, db as sqlalchemy_db

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Use in-memory SQLite for tests
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for easier testing of form submissions
        "LOGIN_DISABLED": False, # Ensure login is not globally disabled unless specifically tested
        "SERVER_NAME": "localhost.test" # Required for url_for to work without active request context
    })

    with flask_app.app_context():
        sqlalchemy_db.create_all() # Create all tables

    yield flask_app

    with flask_app.app_context():
        sqlalchemy_db.drop_all() # Clean up DB

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """Session-wide test database."""
    with app.app_context():
        yield sqlalchemy_db
        # Teardown: clean out the database after each test function
        sqlalchemy_db.session.remove()
        # sqlalchemy_db.drop_all() # This might be too slow if run after every test
        # sqlalchemy_db.create_all() # Recreate for next test; handled by app fixture for session
        # For function scope, usually clearing data is enough. Drop/Create is better per session.
        # Let's clear data from tables instead of dropping/creating each time for function scope.
        for table in reversed(sqlalchemy_db.metadata.sorted_tables):
            sqlalchemy_db.session.execute(table.delete())
        sqlalchemy_db.session.commit()

@pytest.fixture
def admin_user(db):
    """A fixture to create an admin user for testing protected routes."""
    from app import DashboardAdmin, config_loader as app_config_loader
    admin = DashboardAdmin(username='testadmin')
    admin.set_password('testpassword')
    db.session.add(admin)
    db.session.commit()
    return admin

@pytest.fixture
def config_loader_fixture():
    """Fixture to provide the app's config_loader instance."""
    from app import config_loader as app_config_loader
    return app_config_loader

@pytest.fixture
def logged_in_client(client, admin_user):
    """A test client that is logged in as the admin_user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id) # Ensure user_id is stored as string, as Flask-Login expects
        sess['_fresh'] = True # Simulate a fresh login
    # The above logs in the user by setting session variables directly.
    # An alternative is to post to the login route, but that's more of an integration test for login itself.
    # For testing other routes, directly manipulating session is often more straightforward.
    return client
