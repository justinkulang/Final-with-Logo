import pytest
from flask import url_for, session
from app import DashboardAdmin # For creating user directly in DB for tests

def test_login_page_loads(client):
    """Test that the login page loads."""
    response = client.get('/') # Direct path for login_page
    assert response.status_code == 200
    assert b"Hotspot Manager Login" in response.data

def test_dashboard_redirects_if_not_logged_in(client):
    """Test that accessing dashboard redirects to login if not authenticated."""
    response = client.get('/dashboard', follow_redirects=False) # Direct path for index/dashboard
    assert response.status_code == 302 # Expecting a redirect
    assert response.location == '/' # login_page is at '/'

    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200 # After redirect
    assert b"Hotspot Manager Login" in response.data # Should land on login page

def test_successful_login_and_dashboard_access(client, db, app):
    """Test successful login and access to the dashboard."""
    # Create an admin user directly in the database for this test
    admin = DashboardAdmin(username="testadmin_login")
    admin.set_password("password123")
    db.session.add(admin)
    db.session.commit()

    # Attempt login
    # We need to get CSRF token if forms are used, but for direct POST to /app-login
    # The CSRF protection is handled by Flask-WTF. For test_client, if forms are not rendered,
    # CSRF token might not be available. Temporarily disabling CSRF in tests is common.
    # (WTF_CSRF_ENABLED=False is set in conftest.py app fixture)

    login_response = client.post(url_for('app_login_route'), data={
        'app_username': 'testadmin_login',
        'app_password': 'password123'
    }, content_type='application/x-www-form-urlencoded') # Use form content type

    assert login_response.status_code == 200
    json_data = login_response.get_json()
    assert json_data['success'] is True
    assert "Web app login successful." in json_data['message']

    # Check if session is set (basic check)
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is not None
        admin_db_user = DashboardAdmin.query.filter_by(username="testadmin_login").first()
        assert sess.get('_user_id') == str(admin_db_user.id) # Flask-Login stores user_id as string in session


    # Try accessing the dashboard - this part is tricky due to the two-stage login.
    # After app login, the UI shows the Mikrotik connect form.
    # The dashboard itself (/dashboard) would only be fully accessible after Mikrotik connect.
    # The login_response for /app-login does not redirect to /dashboard.
    # It returns JSON, and JS handles showing the next form.

    # Let's test that a protected API endpoint (like /api/config) is now accessible.
    # This requires the user to be logged in via Flask-Login.
    config_response = client.get(url_for('get_config_route'))
    assert config_response.status_code == 200
    assert b"mikrotik" in config_response.data # Check for some expected content

    # To test the /dashboard route itself, we would need to simulate the Mikrotik connection part too,
    # or mock the get_mikrotik_api() to return a successful connection.
    # For now, this test confirms app login and access to a protected API.

def test_failed_login(client, db):
    """Test failed login attempt."""
    # Ensure no such user or wrong password
    login_response = client.post(url_for('app_login_route'), data={
        'app_username': 'wronguser',
        'app_password': 'wrongpassword'
    }, content_type='application/x-www-form-urlencoded')

    assert login_response.status_code == 401 # Unauthorized
    json_data = login_response.get_json()
    assert json_data['success'] is False
    assert "Invalid web app username or password." in json_data['message']

    # Check session is not set
    with client.session_transaction() as sess:
        assert sess.get('_user_id') is None

def test_logout(logged_in_client, client): # Use logged_in_client for setup, then client for checking
    """Test logout functionality."""
    # First, ensure we are logged in (using logged_in_client implicitly does this)
    # Make a request to a protected route to confirm login state if needed
    response = logged_in_client.get(url_for('get_config_route'))
    assert response.status_code == 200

    # Perform logout
    logout_response = logged_in_client.post(url_for('logout'))
    assert logout_response.status_code == 200
    json_data = logout_response.get_json()
    assert json_data['success'] is True

    # Check session is cleared
    # After logout, the session is cleared. If we use 'logged_in_client' again,
    # it will still have the old session cookie from its initial setup.
    # We need to use a 'fresh' client or check the response from the logout_response client instance.
    # A better way: check that a protected route is no longer accessible.

    response_after_logout = client.get(url_for('get_config_route'), follow_redirects=False)
    assert response_after_logout.status_code == 302 # Should redirect to login
    assert url_for('login_page') in response_after_logout.location


# Test for CLI commands
def test_init_db_command(runner, app):
    """Test flask init-db command."""
    result = runner.invoke(args=['init-db'])
    assert 'Initialized the database.' in result.output
    # Further checks could involve inspecting the database schema if possible/needed.

def test_create_admin_command_new(runner, db, app):
    """Test flask create-admin command for a new admin."""
    result = runner.invoke(args=['create-admin'], input='testcliadmin\npassword123\npassword123\n')
    assert 'Admin user \'testcliadmin\' created.' in result.output
    admin = DashboardAdmin.query.filter_by(username='testcliadmin').first()
    assert admin is not None
    assert admin.check_password('password123')

def test_create_admin_command_update_existing_yes(runner, db, app, admin_user): # uses admin_user fixture
    """Test flask create-admin for existing admin, choosing to update password."""
    # admin_user fixture already created 'testadmin' with 'testpassword'
    # Try to "create" testadmin again but update password
    result = runner.invoke(args=['create-admin'], input=f"{admin_user.username}\nnewpass\nnewpass\ny\n")

    assert f"Admin user '{admin_user.username}' password updated." in result.output
    updated_admin = DashboardAdmin.query.filter_by(username=admin_user.username).first()
    assert updated_admin.check_password('newpass')
    assert not updated_admin.check_password('testpassword') # Old password should not work

def test_create_admin_command_update_existing_no(runner, db, app, admin_user):
    """Test flask create-admin for existing admin, choosing NOT to update password."""
    result = runner.invoke(args=['create-admin'], input=f"{admin_user.username}\nnewpass\nnewpass\nn\n")

    assert "Admin user password not updated." in result.output
    existing_admin = DashboardAdmin.query.filter_by(username=admin_user.username).first()
    assert existing_admin.check_password('testpassword') # Original password should still work

# TODO: Add tests for API endpoints (users, profiles, config, etc.)
# These tests would typically use the `logged_in_client` fixture.
# Example structure for an API test:
# def test_get_users_api(logged_in_client, mocker):
#     # Mock the RouterOSService to avoid actual Mikrotik calls
#     mock_get_users = mocker.patch('app.router_os_service.get_hotspot_users')
#     mock_get_users.return_value = [{'name': 'api_user1', 'profile': 'default'}]
#
#     response = logged_in_client.get(url_for('get_users'))
#     assert response.status_code == 200
#     json_data = response.get_json()
#     assert 'users' in json_data
#     assert len(json_data['users']) == 1
#     assert json_data['users'][0]['name'] == 'api_user1'
#     mock_get_users.assert_called_once()


# Test for initial-connect (requires login, but is itself exempt from Mikrotik connection check)
def test_initial_connect_success(logged_in_client, mocker, app, config_loader_fixture): # Renamed fixture
    """Test successful initial Mikrotik connection and config save."""

    # Mock librouteros.connect to simulate successful connection
    mock_connect = mocker.patch('librouteros.connect')
    mock_conn_instance = mocker.MagicMock()
    mock_connect.return_value = mock_conn_instance

    # Ensure config_loader.update_config is also traceable
    mocker.spy(config_loader_fixture, 'update_config') # Use the correct fixture name

    payload = {
        'host': '1.2.3.4',
        'port': 8729,
        'username': 'testconnectuser',
        'password': 'connectpassword'
    }
    response = logged_in_client.post(url_for('initial_connect'), json=payload)

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert "Successfully connected and configuration saved." in json_data['message']

    mock_connect.assert_called_once_with(
        host='1.2.3.4',
        username='testconnectuser',
        password='connectpassword',
        port=8729,
        ssl=False # Assuming default SSL is false from app_config
    )
    mock_conn_instance.close.assert_called_once()

    # Check if config_loader.update_config was called with the correct data
    expected_mikrotik_config = {
        "host": "1.2.3.4",
        "port": 8729,
        "username": "testconnectuser",
        "password": "connectpassword",
        "use_ssl": False,
        "hotspot_login_url": app.config.get('MIKROTIK_HOTSPOT_LOGIN_URL', '') or \
                             flask_app.config.get('mikrotik', {}).get('hotspot_login_url', '') or \
                             config_loader.get_config()['mikrotik'].get('hotspot_login_url', '') # Get current default
    }
    # config_loader.update_config.assert_called_once() - this is harder to check args with spy
    # Instead, check the effect:
    updated_app_config = config_loader.get_config()
    assert updated_app_config['mikrotik']['host'] == '1.2.3.4'
    assert updated_app_config['mikrotik']['username'] == 'testconnectuser'


def test_initial_connect_auth_failure(logged_in_client, mocker):
    """Test initial Mikrotik connection with authentication failure."""
    mocker.patch('librouteros.connect', side_effect=Exception("authentication failed"))

    payload = {'host': '1.2.3.4', 'port': 8728, 'username': 'user', 'password': 'wrong'}
    response = logged_in_client.post(url_for('initial_connect'), json=payload)

    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Authentication failed" in json_data['message']

def test_initial_connect_connection_refused(logged_in_client, mocker):
    """Test initial Mikrotik connection with connection refused."""
    mocker.patch('librouteros.connect', side_effect=ConnectionRefusedError("connection refused"))

    payload = {'host': '1.2.3.4', 'port': 8728, 'username': 'user', 'password': 'password'}
    response = logged_in_client.post(url_for('initial_connect'), json=payload)

    assert response.status_code == 400 # Or whatever status code is set for this
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Connection refused or timed out" in json_data['message']

def test_initial_connect_missing_fields(logged_in_client):
    """Test initial_connect with missing fields."""
    response = logged_in_client.post(url_for('initial_connect'), json={'host': '1.2.3.4'})
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Port is required" in json_data['message'] or "Username is required" in json_data['message']

def test_initial_connect_invalid_port(logged_in_client):
    """Test initial_connect with an invalid port number."""
    payload = {'host': '1.2.3.4', 'port': 99999, 'username': 'user', 'password': 'password'}
    response = logged_in_client.post(url_for('initial_connect'), json=payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Invalid port number" in json_data['message']

# More tests for other API endpoints should follow, mocking RouterOSService calls.
# For example, testing POST /api/users (create_user):
# - Mock router_os_service.create_hotspot_user
# - Call client.post with valid data, check for 200 and success message.
# - Call client.post with invalid data (as per new validation rules), check for 400 and error messages.
# - Check audit log calls if possible (might require more advanced mocking or log capture).

def test_create_user_api_success(logged_in_client, mocker):
    """Test successful user creation via API."""
    mock_create = mocker.patch('app.router_os_service.create_hotspot_user')
    mock_create.return_value = (True, "User testapiuser created successfully")

    payload = {
        "name": "testapiuser",
        "password": "password123",
        "profile": "default",
        "limit-uptime": "1h",
        "limit-bytes-total": 1024 * 1024 * 100, # 100MB in bytes
        "comment": "API test user"
    }
    response = logged_in_client.post(url_for('create_user'), json=payload)

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert "User testapiuser created successfully" in json_data['message']

    expected_payload_to_service = payload.copy()
    # The service receives limit-bytes-total as an int (bytes)
    mock_create.assert_called_once_with(expected_payload_to_service)


def test_create_user_api_validation_failure(logged_in_client):
    """Test user creation API with missing required fields."""
    payload = { # Missing name and password
        "profile": "default"
    }
    response = logged_in_client.post(url_for('create_user'), json=payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Username is required" in json_data['message']
    assert "Password is required" in json_data['message']

def test_create_user_api_service_failure(logged_in_client, mocker):
    """Test user creation API when the RouterOSService fails."""
    mock_create = mocker.patch('app.router_os_service.create_hotspot_user')
    mock_create.return_value = (False, "Mikrotik Error: User already exists")

    payload = {"name": "existinguser", "password": "password", "profile": "default"}
    response = logged_in_client.post(url_for('create_user'), json=payload)

    assert response.status_code == 200 # The API route itself doesn't fail with 500 for service errors
    json_data = response.get_json()
    assert json_data['success'] is False
    assert "Mikrotik Error: User already exists" in json_data['message']
