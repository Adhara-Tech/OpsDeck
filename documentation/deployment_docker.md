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

### 5. Access the Application

Open your browser and navigate to:
`http://localhost:5000`

## Data Persistence

The `docker-compose.yml` mounts a volume for data persistence:
- `./data` on host maps to `/app/data` in the container.

This ensures that your SQLite database (`renewals.db`) and other data files persist even if the container is stopped or removed.
