![OpsDeck Logo](images/opsdeck-logo.png)

# OpsDeck

OpsDeck is the definitive Enterprise Resource Planning (ERP) system designed specifically for modern IT departments. Moving beyond simple inventory tracking, it serves as a unified command center that orchestrates people, processes, technology, and compliance within a single, integrated platform. OpsDeck eliminates tool fragmentation and provides IT leaders with total visibility and control over their entire ecosystem.

## Overview

At its core, OpsDeck is engineered to manage the **complete lifecycle of IT assets**, ensuring absolute traceability from procurement and assignment to maintenance and final disposal. However, it distinguishes itself from traditional tools by integrating a robust **Service Catalog** that allows departments to standardize and control their technological offerings. 

Designed with a "Compliance-First" approach, OpsDeck excels in Governance, Risk, and Compliance (GRC). It features a specialized module for managing **Security Activities** with detailed execution logs, specifically built to facilitate **Audit Defense** and demonstrate regulatory adherence effortlessly. The platform is fortified with enterprise-grade capabilities, including modern **OAuth authentication** and comprehensive **centralized logging** for security auditing. 

By unifying vendor management, budget forecasting, policy enforcement, and operational workflows, OpsDeck provides the professional infrastructure required to scale IT operations securely and efficiently.

## Tech Stack
* **Backend:** Python 3, Flask
* **Database:** SQLAlchemy ORM, Flask-Migrate (defaults to SQLite, compatible with PostgreSQL/MySQL)
* **Frontend:** Jinja2 Templates, Bootstrap 5
* **Scheduling:** APScheduler

## Setup and Installation
Follow these steps to get the application running locally.

### 1. Prerequisites
* Python 3.10+
* A virtual environment tool (venv)

### 2. Installation
```bash
# Clone the repository
# git clone [https://github.com/pixelotes/opsdeck.git](https://github.com/pixelotes/opsdeck.git)
# cd opsdeck

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required Python packages
pip install -r requirements.txt

```

### 3. Configuration

The application is configured using environment variables. Create a file named `.env` in the root of the project.

Example `.env`:

```bash
# Flask Configuration
SECRET_KEY='a-very-strong-and-random-secret-key'
FLASK_APP=run:app

# Database URL (optional, defaults to a local SQLite file)
# DATABASE_URL='sqlite:///opsdeck.db'

# SMTP Email Notification Settings (optional)
SMTP_SERVER='smtp.gmail.com'
SMTP_PORT=587
EMAIL_USERNAME='your-email@gmail.com'
EMAIL_PASSWORD='your-gmail-app-password'

```

### 4. Initialize the Database

The first time you run the app, you need to create the database schema and the initial admin user.

```bash
# Initialize migrations and apply schema
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create the default admin user (admin/admin123)
flask init-db

```

## Usage

To run the application, use the Flask CLI:

```bash
flask run

```

The application will be available at http://127.0.0.1:5000.

* **Default Login:**
* Username: `admin@example.com`
* Password: `admin123` (Please change this immediately after login)

## License

OpsDeck is released under the [Elastic License](./LICENSE).