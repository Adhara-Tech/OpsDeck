# Docker Compose Deployment Guide

This guide details how to deploy OpsDeck using Docker Compose, which simplifies running the application and its dependencies in containers.

## Prerequisites

- Docker
- Docker Compose

## Steps

### 1. Clone the Repository

```bash
git clone https://github.com/pixelotes/OpsDeck.git
cd OpsDeck
```

### 2. Configuration

Copy the example environment file. The `docker-compose.yml` file is configured to read environment variables from `.env`.

```bash
cp .env.example .env
```
Ensure you review `.env` and set values appropriate for production (especially `SECRET_KEY`).

### 3. Build and Run

Run the following command to build the Docker image and start the container in detached mode.

```bash
docker-compose up -d --build
```

### 4. Verify Deployment

Check the status of the container:

```bash
docker-compose ps
```

View the logs to ensure the application started correctly:

```bash
docker-compose logs -f web
```

The application is configured to automatically initialize the database on the first run (via `entrypoint.sh`).

### 5. Configure Admin Credentials (Optional)

By default, the application creates an admin user with email `admin@example.com` and password `admin123`. For production deployments, you should customize these credentials by adding the following to your `.env` file:

```bash
DEFAULT_ADMIN_EMAIL=your-admin@company.com
DEFAULT_ADMIN_INITIAL_PASSWORD=YourSecurePassword123!
```

The admin user is created automatically when the container starts for the first time. The application will prompt you to change the password on first login.

### 6. Access the Application

Open your browser and navigate to:
`http://localhost:5000`

**Default Login:**
- Email: Value of `DEFAULT_ADMIN_EMAIL` (default: `admin@example.com`)
- Password: Value of `DEFAULT_ADMIN_INITIAL_PASSWORD` (default: `admin123`)

## Data Persistence

The `docker-compose.yml` mounts a volume for data persistence:
- `./data` on host maps to `/app/data` in the container.

This ensures that your SQLite database (`renewals.db`) and other data files persist even if the container is stopped or removed.
