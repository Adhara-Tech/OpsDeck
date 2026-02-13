# Manual Deployment Guide

This guide details how to manually deploy the OpsDeck application on a standard Linux environment.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- git

## Steps

### 1. Clone the Repository

```bash
git clone https://github.com/pixelotes/OpsDeck.git
cd OpsDeck
```

### 2. Set Up a Virtual Environment

It is best practice to run Python applications in an isolated virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies

Install the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Configuration

Copy the example environment file and configure it according to your needs.

```bash
cp .env.example .env
```

Edit `.env` and set the necessary variables (e.g., `SECRET_KEY`, database paths, etc.).

### 5. Database Initialization

Initialize the database, apply migrations, and seed initial data.

```bash
# Initialize the database migration repository
flask db init

# Create the initial migration
flask db migrate -m "Initial migration"

# Apply migrations to the database
flask db upgrade

# Create the default admin user and initial setup
flask init-db

# Seed the database with production data (frameworks, controls)
flask seed-db-prod
```

### 6. Run the Application

#### For Development
```bash
flask run --host=0.0.0.0 --port=5000
```

#### For Production
Use a production WSGI server like Gunicorn.

```bash
gunicorn --bind 0.0.0.0:5000 run:app
```

The application should now be accessible at `http://localhost:5000`.
