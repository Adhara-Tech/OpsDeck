#!/bin/sh

# This is the path inside the container where the database will live
DB_FILE="/app/data/renewals.db"

# Wait for the database file to be created if it's being mounted
sleep 1

# Check if the database file does NOT exist

# Initialize the migrations folder (idempotent, skips if exists)
flask db init 2>/dev/null || true

# Create/Stamp migration (handling cases where migrations might already exist in image)
flask db migrate -m "Initial migration" 2>/dev/null || true

# Apply the migration to create all tables
flask db upgrade

# Create the default admin user
flask init-db

# Add initial frameworks and controls (Production Data)
flask seed-db-prod


# Add demo data (Users, Assets, Risks, etc.) - Only if SEED_DEMO_DATA is True
if [ "$SEED_DEMO_DATA" = "True" ]; then
    echo "Seeding demo data..."
    flask seed-db-demodata
else
    echo "Skipping demo data seeding (SEED_DEMO_DATA not set to True)"
fi


echo "Database initialized."


# Start the application using gunicorn
echo "Starting application..."
exec gunicorn --bind 0.0.0.0:5000 run:app
