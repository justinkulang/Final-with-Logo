# Mikrotik Hotspot User Management Dashboard

This project provides a web-based dashboard for managing Mikrotik Hotspot users, including features for user creation, batch generation, profile management, and activity monitoring. It incorporates security best practices like session management, CSRF protection, and guidance for production deployment.

## Features

*   **User Management:** Create, edit, delete, and view hotspot users.
*   **Batch User Creation:** Generate multiple voucher-style users at once.
*   **Profile Management:** Manage hotspot user profiles from the Mikrotik router.
*   **Active Sessions:** View and disconnect active hotspot users.
*   **Voucher Generation:** Export user batches as printable HTML or PDF vouchers with QR codes.
*   **Analytics:** Basic analytics on data usage by profile and top users.
*   **Secure Access:**
    *   Web application login system using Flask-Login (session-based).
    *   CSRF protection for all state-changing operations using Flask-WTF.
    *   Rate limiting for login attempts using Flask-Limiter.
*   **Internationalization (i18n):** Support for multiple languages (English, Arabic, French).
*   **Configurable:** Key settings managed via `config.json`.
*   **Production Ready:** Includes Gunicorn configuration and guidance for HTTPS setup.

## Prerequisites

*   Python 3.7+
*   pip (Python package installer)
*   A Mikrotik router with the API service enabled.
*   Network connectivity between the server running this application and the Mikrotik router.
*   (Optional, for PDF export) System dependencies for WeasyPrint (see WeasyPrint documentation for your OS).

## Setup and Installation

1.  **Clone Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file contains pinned versions for stable builds. You can update these or generate your own environment's specific versions using `pip freeze > requirements.txt` after testing.

4.  **Initial Configuration (`config.json`):**
    *   Upon first run, or if `config.json` is missing, a default configuration file will be created.
    *   **Web Application Admin:**
        *   A default admin user for the web dashboard is created with credentials:
            *   Username: `admin`
            *   Password: `changeme`
        *   **IMPORTANT:** Change this default password immediately after the first login! You can generate a new password hash using Python and Werkzeug security:
            ```python
            from werkzeug.security import generate_password_hash
            new_hash = generate_password_hash('your_new_strong_password')
            print(new_hash)
            ```
            Then, update the `password_hash` value in the `app_admin` section of `config.json` with this new hash.
    *   **Mikrotik Connection:**
        *   Configure your Mikrotik router details (host, API username, API password, port) either by:
            1.  Manually editing `config.json` before the first run.
            2.  Using the web application's "Settings" page after logging in. The application will not be able to manage the router until these details are correctly configured.
    *   **Log File Location:** The default log file is `mikrotik_dashboard.log`. You can change this in `config.json` under `server.log_file`. An `audit.log` is also created.

4.  **Initialize Database and Create Admin User:**
    The application now uses a SQLite database to store admin user credentials.
    *   **Initialize the database:**
        ```bash
        flask init-db
        ```
        This command creates the `mikrotik_dashboard_users.db` file (or the path specified by `DATABASE_URL` env var).
    *   **Create an admin user:**
        ```bash
        flask create-admin
        ```
        You will be prompted to enter a username and password for the dashboard admin.

## Running the Application

### Development

For development purposes, you can use the Flask development server:
```bash
python app.py
```
This server is convenient but not suitable for production. The debug mode is sourced from `config.json` (`server.debug`), which now defaults to `false`.

### Production (Recommended)

For production, it is highly recommended to use a production-grade WSGI server like Gunicorn, and to run the application behind a reverse proxy like Nginx for HTTPS termination and serving static files.

1.  **Using Gunicorn:**
    A `gunicorn_config.py` file is provided. It attempts to load server host and port from `config.json`.
    Run Gunicorn with:
    ```bash
    gunicorn --config gunicorn_config.py app:app
    ```
    Ensure Gunicorn is installed (`pip install gunicorn`).

2.  **Further Production Setup:**
    Refer to the "Production Deployment" section below for crucial details on HTTPS, environment variables, etc.

## Docker Deployment (Recommended for Ease of Use)

This application can be easily deployed using Docker and Docker Compose.

1.  **Prerequisites:**
    *   Docker installed: [Get Docker](https://docs.docker.com/get-docker/)
    *   Docker Compose installed (usually comes with Docker Desktop).

2.  **Configuration:**
    *   A `docker-compose.yml` file is provided.
    *   **Important:** Edit `docker-compose.yml` and set a strong `FLASK_SECRET_KEY`.
    *   (Optional) Create a `config.json` in the project root if you want to pre-configure Mikrotik details or logging paths. If you do, ensure paths for logs/DB in `config.json` match volume mounts or are relative to `/app/data` if you want them in the persistent volume. E.g.:
        ```json
        "server": {
            "log_file": "data/mikrotik_dashboard.log", // To store in the 'app_data' volume
            "audit_log_file": "data/audit.log"      // To store in the 'app_data' volume
        }
        ```
        If `config.json` is not provided, a default one will be created inside the container (less ideal for production config persistence if the container is ephemeral without mounted config). The `docker-compose.yml` example mounts `./config.json` and `./app_data`.

3.  **Build and Run:**
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs it in detached mode.

4.  **Initialize Database and Create Admin (First Run):**
    After the container is running:
    ```bash
    docker-compose exec web flask init-db
    docker-compose exec web flask create-admin
    ```
    Follow the prompts to create your admin user.

5.  **Accessing the Application:**
    The application should be available at `http://localhost:5000` (or the port you mapped in `docker-compose.yml`).

6.  **Stopping:**
    ```bash
    docker-compose down
    ```

## API Documentation

For details on the available API endpoints, please refer to [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Rate Limiting
*   The application uses `Flask-Limiter` to protect against brute-force login attacks.
*   Default limits are `5 per minute` for the login route and global defaults of `200 per day, 50 per hour`.
*   For multi-process deployments (e.g., multiple Gunicorn workers), the default `memory://` storage for Flask-Limiter will not work correctly across processes. You should configure a central store like Redis or Memcached.
    Example for `config.json` (if you were to extend it, though typically limiter config is in `app.py` or env vars):
    ```json
    "RATELIMIT_STORAGE_URL": "redis://localhost:6379/1"
    ```
    And in `app.py`, you would initialize `Limiter` with `app.config.from_json('config.json')` or similar, or directly use environment variables for `RATELIMIT_STORAGE_URL`.

## Production Deployment

When deploying this application to a production environment, several considerations should be taken into account for security, reliability, and performance.

### Admin User
*   The dashboard admin user is now managed in a database (SQLite by default). Ensure you have created an admin user using `flask create-admin` after `flask init-db`.
*   The `app_admin` section in `config.json` is no longer used for admin credentials.

### `SECRET_KEY` Configuration
For session security, Flask uses a `SECRET_KEY`.
*   **Action Required:** Set the `FLASK_SECRET_KEY` environment variable to a strong, unique, and random string. Do not use the default fallback key in production.
*   The application will use the environment variable if set, otherwise, it falls back to a hardcoded development key and issues a warning.

### Database Configuration
*   By default, a SQLite database named `mikrotik_dashboard_users.db` is created in the application directory.
*   For production, you might consider using a more robust database. You can configure the database URI using the `DATABASE_URL` environment variable (e.g., `DATABASE_URL="postgresql://user:pass@host:port/dbname"`).
*   Ensure the database file (if SQLite) or the database service is properly backed up.

### Debug Mode
*   **Action Required:** Ensure that `debug` is set to `false` in the `server` section of your `config.json` for production. The application now defaults this to `false` if the key is missing or a new config is generated.

### WSGI Server (Gunicorn)
*   The provided `gunicorn_config.py` sets up Gunicorn to bind to the host and port specified in `config.json` (defaulting to `0.0.0.0:5000`).
*   It also sets a recommended number of worker processes.
*   You can customize `gunicorn_config.py` further for advanced Gunicorn settings (e.g., logging, timeouts).

### HTTPS Setup (Recommended)
For production, it is strongly recommended to serve the application over HTTPS. The typical setup involves running Gunicorn locally and using a reverse proxy like Nginx or Apache in front of it to handle HTTPS termination.

**Why HTTPS is Crucial:**
*   **Security:** Encrypts data between the user's browser and the server.
*   **Data Integrity:** Ensures data is not tampered with during transit.
*   **User Trust:** Browsers mark HTTP sites as "not secure."

**Example Nginx Configuration:**
(This example assumes Gunicorn is listening on `127.0.0.1:5000`)

```nginx
server {
    listen 80;
    server_name your_domain.com; # Replace with your actual domain

    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your_domain.com; # Replace with your actual domain

    # SSL Certificate paths
    ssl_certificate /etc/letsencrypt/live/your_domain.com/fullchain.pem; # Adjust path (e.g., from Let's Encrypt)
    ssl_certificate_key /etc/letsencrypt/live/your_domain.com/privkey.pem; # Adjust path
    
    # Recommended SSL settings (consult current best practices)
    # ssl_protocols TLSv1.2 TLSv1.3;
    # ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
    # ssl_prefer_server_ciphers off;
    # Add HSTS header (optional, but recommended)
    # add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # (Optional) Serve static files directly with Nginx for better performance
    # location /static {
    #     alias /path/to/your/project/static; # Adjust to your app's static folder
    #     expires 7d;
    #     access_log off;
    # }

    location / {
        proxy_pass http://127.0.0.1:5000; # Must match Gunicorn's bind address
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
**Notes for Nginx:**
*   Replace `your_domain.com` with your domain.
*   Adjust SSL certificate paths. Consider using Certbot from Let's Encrypt for free certificates.
*   Ensure Gunicorn (via `gunicorn_config.py` and `config.json`) binds to `127.0.0.1:5000` if Nginx is on the same machine. If Gunicorn binds to `0.0.0.0`, ensure your firewall is configured appropriately.

### Logging
*   The application is configured to log to both the console and a file.
*   The default log file is `mikrotik_dashboard.log` (configurable in `config.json` via `server.log_file`).
*   An `audit.log` file (configurable via `server.audit_log_file` in `config.json`) is generated to record significant security-related events such as logins, user management actions, and configuration changes.
*   Console and file log levels are also configurable in `config.json` (`server.log_level_console`, `server.log_level_file`).
*   When using Gunicorn, its own logging mechanisms (e.g., `accesslog`, `errorlog` in `gunicorn_config.py`) can also be used to capture stdout/stderr from the application.

### Pinned Dependencies
*   `requirements.txt` includes pinned versions for all dependencies to ensure stable and reproducible builds.
*   If you modify your environment or update packages, it's good practice to regenerate this file with your current working set: `pip freeze > requirements.txt`.

### Other Production Considerations (from previous README section)
*   **Database:** For more robust data storage than `config.json` (especially for user credentials if not using a fixed admin user), consider using a proper database system.
*   **Backups:** Implement regular backups of your application data and configurations.
*   **Monitoring:** Set up monitoring for your application and server to track performance and errors.
*   **Firewall:** Configure a firewall to only allow necessary traffic to your server (e.g., ports 80 and 443).

## Translations (i18n)

This application uses Flask-Babel for internationalization.
*   Supported languages: English (default), Arabic, French.
*   Translations are stored in the `translations` directory.
*   To add or update translations:
    1.  Extract messages: `pybabel extract -F babel.cfg -o messages.pot .`
    2.  Initialize a new language (e.g., for Spanish 'es'): `pybabel init -i messages.pot -d translations -l es`
    3.  Update existing languages: `pybabel update -i messages.pot -d translations`
    4.  Compile translations: `pybabel compile -d translations`
    (Ensure you have Babel installed and `babel.cfg` correctly configured if you modify translatable files.)

*(License section would go here if applicable)*
*(Contributing guidelines would go here if applicable)*
