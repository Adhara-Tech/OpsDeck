#!/bin/sh

# This is the path inside the container where the database will live
DB_FILE="/app/data/renewals.db"

# Ensure the data directory exists (required for SQLite)
mkdir -p /app/data/attachments

# Wait for the database file to be created if it's being mounted
sleep 1

# Check if Enterprise mode is enabled and install plugin BEFORE migrations
if [ "$ENTERPRISE_ENABLED" = "True" ]; then
    echo "Enterprise mode enabled. Installing enterprise plugin..."
    if [ -d "/app/opsdeck-enterprise" ]; then
        # Install the enterprise plugin in editable mode
        pip install -e /app/opsdeck-enterprise
        if [ $? -eq 0 ]; then
             echo "✓ Enterprise plugin installed successfully"
        else
             echo "✗ Failed to install enterprise plugin"
             exit 1
        fi
    else
        echo "⚠ Enterprise mode enabled but opsdeck-enterprise folder not found"
    fi
fi

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


# Seed Enterprise plugin data - Only if ENTERPRISE_ENABLED is True
if [ "$ENTERPRISE_ENABLED" = "True" ]; then
    if [ -d "/app/opsdeck-enterprise" ]; then
        echo "Seeding enterprise data..."
        # We assume plugin was installed at the beginning of the script
        flask seed-connectors
        flask seed-ai-profiles
        echo "✓ Enterprise plugin configured and seeded"
    fi
else
    echo "Enterprise mode disabled (ENTERPRISE_ENABLED not set to True)"
fi


echo "Database initialized."


# Start the application using gunicorn
echo "Starting application..."
exec gunicorn --bind 0.0.0.0:5000 run:app
