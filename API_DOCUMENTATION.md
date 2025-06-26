# Mikrotik Hotspot Manager API Documentation

This document provides details on the API endpoints available in the Mikrotik Hotspot Manager application.

## Base URL

All API endpoints are relative to the application's base URL. For example, if the application is running at `http://localhost:5000`, an endpoint like `/api/users` would be `http://localhost:5000/api/users`.

## Authentication

*   Most API endpoints require the user to be authenticated with the web application first. This is done by posting credentials to `/app-login`.
*   Authenticated sessions are managed using Flask-Login (cookies).
*   All `POST`, `PUT`, `DELETE` requests that modify state are protected by CSRF tokens. The client must include a valid `X-CSRFToken` header, obtained typically from a `meta` tag in the HTML: `<meta name="csrf-token" content="{{ csrf_token() }}">`.

## Rate Limiting

*   The `/app-login` endpoint is rate-limited to 5 attempts per minute per IP.
*   Global rate limits of 200 per day and 50 per hour per IP also apply.

## Common Responses

*   **Success:** Typically `200 OK` with a JSON body like:
    ```json
    {
        "success": true,
        "message": "Operation successful message.",
        // ... other data ...
    }
    ```
*   **Client Error (e.g., bad input):** Typically `400 Bad Request` or `401 Unauthorized` (for login failures), `404 Not Found`. JSON body:
    ```json
    {
        "success": false,
        "message": "Error message detailing the issue."
    }
    ```
*   **Server Error:** Typically `500 Internal Server Error`. JSON body might contain an error message.

---

## Endpoints

### 1. Application Login & Session

#### `POST /app-login`
Handles web application login for the dashboard administrator.
*   **Request Body:** `application/x-www-form-urlencoded`
    *   `app_username` (string, required): The admin username.
    *   `app_password` (string, required): The admin password.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Web app login successful."
    }
    ```
*   **Response (Failure - 400 Bad Request / 401 Unauthorized):**
    ```json
    {
        "success": false,
        "message": "Invalid web app username or password."
    }
    ```
    or
    ```json
    {
        "success": false,
        "message": "Username and password are required."
    }
    ```
*   **Notes:** This endpoint is rate-limited. CSRF protection applies.

#### `POST /api/logout`
Logs out the current admin user from the web application. Also resets the Mikrotik connection details in `config.json` to defaults and closes any active Mikrotik API session held by the server for the current request.
*   **Request Body:** None
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Logged out successfully from web app and Mikrotik."
    }
    ```
*   **Notes:** Requires active login session. CSRF protection applies.

### 2. Initial Mikrotik Connection Setup

#### `POST /api/initial-connect`
Attempts to connect to the Mikrotik router with the provided credentials. If successful, saves these credentials to `config.json` for subsequent use. This is typically used when the application is first set up or if the router details change.
*   **Request Body:** `application/json`
    ```json
    {
        "host": "192.168.88.1", // (string, required)
        "port": 8728,           // (integer, required, 1-65535)
        "username": "admin",    // (string, required)
        "password": ""          // (string, optional)
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Successfully connected and configuration saved."
    }
    ```
*   **Response (Failure - 400 Bad Request / 401 Unauthorized):**
    ```json
    {
        "success": false,
        "message": "Connection failed: <specific error from router or validation>."
    }
    ```
*   **Notes:** Requires active app login session. CSRF protection applies.

### 3. Configuration Management

#### `GET /api/config`
Retrieves the current server configuration (Mikrotik details, server settings, feature flags). Passwords and sensitive hashes are omitted.
*   **Response (Success - 200 OK):**
    ```json
    {
        "mikrotik": {
            "host": "192.168.88.1",
            "port": 8728,
            "username": "admin",
            // "password" is omitted
            "use_ssl": false,
            "hotspot_login_url": "http://hotspot.setup/login"
        },
        "server": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": false,
            "log_file": "mikrotik_dashboard.log",
            "audit_log_file": "audit.log",
            "log_level_console": "INFO",
            "log_level_file": "INFO"
        },
        "features": {
            "pdf_export": true,
            "qr_codes": true
        }
    }
    ```
*   **Notes:** Requires active login session.

#### `POST /api/config`
Updates parts of the server configuration. Only `mikrotik` and `server` sections can be updated via this endpoint. The `app_admin` section (for dashboard admin credentials) cannot be modified here as it's managed via the database and CLI.
*   **Request Body:** `application/json` (partial configuration allowed)
    ```json
    {
        "mikrotik": { // Optional
            "host": "192.168.1.1",
            "port": 8728,
            "username": "new_api_user",
            "password": "new_api_password", // Optional, send only if changing
            "hotspot_login_url": "http://new.hotspot/login"
        },
        "server": { // Optional
            "log_level_console": "DEBUG"
        }
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Configuration updated and saved."
    }
    ```
*   **Response (Failure - 400 Bad Request):** If validation fails for provided config values.
    ```json
    {
        "success": false,
        "message": "<Validation error message>"
    }
    ```
*   **Notes:** Requires active login session. CSRF protection applies.

### 4. Hotspot User Management

#### `GET /api/users`
Retrieves a list of all Hotspot users from the Mikrotik router.
*   **Response (Success - 200 OK):**
    ```json
    {
        "users": [
            {
                ".id": "*1",
                "name": "user1",
                "profile": "default",
                "disabled": "false", // "true" or "false"
                "limit-uptime": "1h", // RouterOS time format or null
                "limit-bytes-total": "104857600", // Bytes, or null
                "uptime": "0s",
                "bytes-in": "0",
                "bytes-out": "0",
                "comment": "Test user"
                // ... other fields from Mikrotik ...
            }
        ]
    }
    ```
*   **Notes:** Requires active login session.

#### `POST /api/users`
Creates a new Hotspot user.
*   **Request Body:** `application/json`
    ```json
    {
        "name": "newuser",         // (string, required, 1-63 chars, a-zA-Z0-9_@.-)
        "password": "password123", // (string, required, 3-63 chars)
        "profile": "default",      // (string, required, 1-63 chars)
        "limit-uptime": "2h30m",   // (string, optional, ROS time format)
        "limit-bytes-total": 52428800, // (integer, optional, bytes, e.g., 50MB)
        "comment": "New API user", // (string, optional, max 255 chars)
        "server": "hotspot1"       // (string, optional, hotspot server name)
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "User created successfully"
    }
    ```
*   **Response (Failure - 400 Bad Request):** For validation errors or if Mikrotik rejects creation.
    ```json
    {
        "success": false,
        "message": "<Error message from validation or Mikrotik>"
    }
    ```
*   **Notes:** Requires active login session. CSRF protection applies.

#### `PUT /api/users/<username>`
Updates an existing Hotspot user. `<username>` in the URL is the current name of the user to modify.
*   **Request Body:** `application/json` (send only fields to update)
    ```json
    {
        "password": "newpassword",           // (string, optional, 3-63 chars)
        "profile": "new_profile",            // (string, optional, 1-63 chars)
        "limit-uptime": "0s",                // (string, optional, ROS time format, "0s" or "" to remove limit)
        "limit-bytes-total": 0,              // (integer, optional, bytes, 0 to remove limit)
        "comment": "Updated comment",        // (string, optional, max 255 chars)
        "disabled": true                     // (boolean, optional)
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "User updated successfully"
    }
    ```
*   **Response (Failure - 400 Bad Request / 404 Not Found):** For validation errors, if user not found, or Mikrotik error.
*   **Notes:** Requires active login session. CSRF protection applies.

#### `DELETE /api/users/<username>`
Deletes a Hotspot user.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "User deleted successfully"
    }
    ```
*   **Response (Failure - 404 Not Found):** If user not found or Mikrotik error.
*   **Notes:** Requires active login session. CSRF protection applies.

#### `POST /api/bulk-create-users`
Creates a batch of Hotspot users (vouchers).
*   **Request Body:** `application/json`
    ```json
    {
        "number_of_users": 10,                  // (integer, required, 1-1000)
        "profile": "voucher_profile",           // (string, required)
        "username_length": 6,                   // (integer, optional, default 6, 1-63)
        "password_length": 8,                   // (integer, optional, default 8, 3-63)
        "username_prefix": "v-",                // (string, optional, max 30 chars)
        "username_charset": "alphanumeric",     // (string, optional, see app.py charsets dict for keys)
        "password_charset": "alphanumeric_symbols",// (string, optional, see app.py charsets dict for keys)
        "comment_prefix": "Batch May2024",      // (string, optional, comment for all users in batch)
        "limit-uptime": "7d",                   // (string, optional, ROS time format)
        "limit-bytes-total": 1073741824         // (integer, optional, bytes, e.g., 1GB)
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true, // true if all users created, can be true even if some failed if partial success is allowed by backend
        "message": "Created 10 users. Failed: 0.",
        "created_credentials": [
            {"username": "v-abc123", "password": "xyz789"},
            // ... more credentials ...
        ],
        "errors": [] // List of errors if any users failed
    }
    ```
*   **Notes:** Requires active login session. CSRF protection applies.

#### Bulk User Actions (Enable, Disable, Change Profile, Delete)
These endpoints operate on a list of usernames.
*   `POST /api/users/bulk-enable`
*   `POST /api/users/bulk-disable`
*   `POST /api/users/bulk-delete`
*   **Request Body (for enable, disable, delete):** `application/json`
    ```json
    {
        "usernames": ["user1", "user2", "user3"] // (list of strings, required)
    }
    ```
*   `POST /api/users/bulk-change-profile`
*   **Request Body (for change profile):** `application/json`
    ```json
    {
        "usernames": ["user1", "user2"], // (list of strings, required)
        "profile": "new_target_profile"  // (string, required)
    }
    ```
*   **Response (All Bulk Actions - 200 OK):**
    ```json
    {
        "success": true, // true if operation was successful for all specified users
        "message": "Enabled 3 users. Failed: 0.", // Example for bulk-enable
        "details": [] // List of errors if any individual operations failed
    }
    ```
*   **Notes:** Requires active login session. CSRF protection applies.

### 5. Hotspot Profile Management

#### `GET /api/profiles`
Retrieves a list of all Hotspot user profiles.
*   **Response (Success - 200 OK):**
    ```json
    {
        "profiles": [
            {
                ".id": "*A1",
                "name": "default",
                "rate-limit": "1M/5M", // Example
                "session-timeout": "1d 00:00:00",
                "shared-users": "1"
                // ... other fields ...
            }
        ]
    }
    ```

#### `POST /api/profiles`
Creates a new Hotspot user profile.
*   **Request Body:** `application/json`
    ```json
    {
        "name": "new_profile_name",        // (string, required, 1-63 chars)
        "rate-limit": "2M/10M",            // (string, optional, ROS rate format)
        "session-timeout": "3d",           // (string, optional, ROS time format)
        "shared-users": "5"                // (integer/string, optional, non-negative)
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Profile 'new_profile_name' created successfully."
    }
    ```

#### `PUT /api/profiles/<profile_id>`
Updates an existing Hotspot user profile. `<profile_id>` is the `.id` of the profile.
*   **Request Body:** `application/json` (send only fields to update)
    ```json
    {
        "rate-limit": "3M/15M",
        "session-timeout": "" // Send empty string or null to clear
    }
    ```
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Profile updated successfully."
    }
    ```

#### `DELETE /api/profiles/<profile_id>`
Deletes a Hotspot user profile.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Profile deleted successfully."
    }
    ```

### 6. Active Sessions & Maintenance

#### `GET /api/active-sessions`
Retrieves a list of currently active Hotspot user sessions.
*   **Response (Success - 200 OK):**
    ```json
    {
        "sessions": [
            {
                ".id": "*S1",
                "user": "user1",
                "address": "192.168.89.10",
                "mac-address": "AA:BB:CC:DD:EE:FF",
                "uptime": "00:15:30",
                "bytes-in": "1024000", // Bytes
                "bytes-out": "5120000", // Bytes
                "session-time-left": "00:44:30" // or null
            }
        ]
    }
    ```

#### `POST /api/disconnect-user/<active_id>`
Disconnects an active user session by its `.id`.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "User disconnected successfully"
    }
    ```

#### `POST /api/delete-expired-users`
Finds and deletes users who have exceeded their time or data limits.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Successfully deleted X expired user(s).",
        "deleted_count": 0 // Number of users deleted
    }
    ```

#### `DELETE /api/users/delete-by-profile/<profile_name>`
Deletes all users belonging to a specific profile.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Successfully deleted X user(s) from profile 'profile_name'.",
        "deleted_count": 0
    }
    ```

#### `DELETE /api/users/delete-by-active-status/<status>`
Deletes users based on their active/disabled status. `<status>` can be `active` or `disabled`.
*   **Response (Success - 200 OK):**
    ```json
    {
        "success": true,
        "message": "Successfully deleted X active/disabled user(s).",
        "deleted_count": 0
    }
    ```

### 7. Analytics & Stats

#### `GET /api/dashboard-stats`
Retrieves basic dashboard statistics (total users, active sessions).
*   **Response (Success - 200 OK):**
    ```json
    {
        "total_users": 150,
        "active_sessions": 25
    }
    ```

#### `GET /api/analytics/basic_summary`
Retrieves data for analytics charts (data usage by profile, top users by data).
*   **Response (Success - 200 OK):**
    ```json
    {
        "total_data_all_users": 12345678900, // Bytes
        "all_users_sorted_by_data": [
            {"name": "userX", "profile": "p1", "bytes_in": 0, "bytes_out": 0, "total_data": 500000000, "comment": null},
            // ... more users ...
        ],
        "data_usage_by_profile": {
            "profile1": 8000000000,
            "profile2": 4345678900
        }
    }
    ```

### 8. Voucher Export (HTML/PDF via Form POST)

These are not traditional JSON APIs but form submissions that result in file downloads or HTML views.

#### `POST /api/vouchers/view_batch_html`
Generates an HTML page to view a batch of vouchers.
*   **Request Body:** `application/x-www-form-urlencoded`
    *   `vouchers_json` (string, required): JSON string array of voucher objects `[{"username": "u1", "password": "p1"}, ...]`.
    *   `hotspot_login_url` (string, optional): URL for QR codes.
*   **Response:** `text/html` content.

#### `POST /api/vouchers/download_batch_pdf`
Generates a PDF file for a batch of vouchers.
*   **Request Body:** `application/x-www-form-urlencoded`
    *   `vouchers_json` (string, required): JSON string array of voucher objects.
    *   `hotspot_login_url` (string, optional): URL for QR codes.
*   **Response:** `application/pdf` file download.
*   **Notes:** Requires WeasyPrint to be available on the server.

### 9. Other

#### `GET /api/translations`
Retrieves a JSON object containing translated strings for the frontend UI.
*   **Response (Success - 200 OK):**
    ```json
    {
        "Loading...": "Loading...", // Key-value pairs of English text to current locale's translation
        "Save": "Sauvegarder" // Example for French
    }
    ```
*   **Notes:** No authentication required.

---

This documentation provides a starting point. Specific validation rules (e.g., regex for usernames, exact format for time limits) might need further detailing if stricter client-side validation is desired before API calls.Okay, the `API_DOCUMENTATION.md` file has been created with the initial content.

Next, I will create the `Dockerfile` and `docker-compose.yml`.
