# Environment Variables

The OpsDeck application is configured using environment variables. These can be set in your operating system, or in a `.env` file in the project root (which is automatically loaded).

## General Configuration

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | A long, random string used for cryptographic signing (sessions, CSRF, etc.). **Change this in production.** | `'your-secret-key-change-this'` | Yes (for security) |
| `FLASK_APP` | Entry point for the Flask application. | `run:app` | Yes |
| `FLASK_DEBUG` | Enables debug mode (auto-reload, debugger). Set to `1` for development, `0` for production. | `0` | No |

## Database

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | The database connection URI (e.g., `postgresql://user:pass@host/db`). Defaults to a local SQLite file. | `sqlite:///../data/renewals.db` | No |

## Email & Notifications

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `SMTP_SERVER` | SMTP server hostname for sending emails. | `'smtp.gmail.com'` | No |
| `SMTP_PORT` | SMTP server port. | `587` | No |
| `EMAIL_USERNAME` | Username (email address) for SMTP authentication. | `''` | If SMTP used |
| `EMAIL_PASSWORD` | Password or App Password for SMTP authentication. | `''` | If SMTP used |
| `WEBHOOK_URL` | URL for external webhook notifications (e.g., Slack, Discord). | `''` | No |

## Authentication & Security

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID for Google OAuth login. | `''` | No |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Client Secret for Google OAuth login. | `''` | No |
| `OAUTHLIB_INSECURE_TRANSPORT` | Set to `1` to allow OAuth over HTTP (dev only). Do NOT set in production. | `None` | No |
| `MFA_ENABLED` | Set to `True` to enable Multi-Factor Authentication checks. | `False` | No |

## Session & Cookies

These variables control the security of the session cookie.
*Note: These behave according to standard Flask configuration.*

| Variable | Description | Default | Recommended (Prod) |
| :--- | :--- | :--- | :--- |
| `SESSION_COOKIE_SECURE` | If `True`, the cookie is only sent over HTTPS. | `False` | `True` |
| `SESSION_COOKIE_HTTPONLY` | If `True`, prevents JavaScript access to the cookie. | `True` | `True` |
| `SESSION_COOKIE_SAMESITE` | Restricts how cookies are sent with cross-site requests (`'Lax'`, `'Strict'`, or `'None'`). | `'Lax'` | `'Lax'` or `'Strict'` |

## Admin User Initialization

These variables control the credentials for the initial administrator user created on first deployment.

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `DEFAULT_ADMIN_EMAIL` | Email address for the default admin user created on first run. | `'admin@example.com'` | No |
| `DEFAULT_ADMIN_INITIAL_PASSWORD` | Initial password for the default admin user. **Change this in production.** | `'admin123'` | No |

> **Security Note:** These credentials are only used when creating the admin user for the first time. If a user with the specified email already exists, no action is taken. The application will prompt you to change the default password upon first login. Always use strong, unique credentials in production environments.
