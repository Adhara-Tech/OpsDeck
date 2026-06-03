# bcdr_export.py — BCDR Export (Disaster Recovery)

Standalone script that extracts **all data** from the OpsDeck database and generates a directory with one Excel file (`.xlsx`) per entity type. Intended for offline backups, audits, and data recovery in case of disaster.

## Requirements

```bash
pip install sqlalchemy psycopg2-binary openpyxl
```

## Usage

```bash
# Connection via DATABASE_URL (recommended)
python scripts/bcdr_export.py --database-url postgresql://opsdeck:opsdeck@localhost:5432/opsdeck

# Connection via individual parameters
python scripts/bcdr_export.py --host db.prod.internal --port 5432 --db opsdeck --user opsdeck --password opsdeck

# Custom output directory
python scripts/bcdr_export.py --database-url $DATABASE_URL --output /backups/opsdeck_20260224

# Use the DATABASE_URL environment variable directly
export DATABASE_URL=postgresql://opsdeck:opsdeck@localhost:5432/opsdeck
python scripts/bcdr_export.py
```

If `--output` is not specified, a `bcdr_opsdeck_YYYYMMDD_HHMM/` directory is created in the current directory.

## Running inside Docker

The DB port is usually not exposed to the host, so it is easier to run from inside the web container:

```bash
# Copy the script into the container and run it
docker cp scripts/bcdr_export.py opsdeck-web-1:/tmp/bcdr_export.py

# Install openpyxl if missing (sqlalchemy and psycopg2 are already in the image)
docker exec opsdeck-web-1 pip install openpyxl

# Run
docker exec opsdeck-web-1 python /tmp/bcdr_export.py \
  --database-url postgresql://opsdeck:opsdeck@db:5432/opsdeck \
  --output /tmp/bcdr_export

# Copy the result back to the host
docker cp opsdeck-web-1:/tmp/bcdr_export/. ./export/
```

## Output

A directory with **57 files** is generated:

| Category | Files |
|---|---|
| **Organization** | Users, Groups, Locations, Org_Settings |
| **Assets & Inventory** | Assets, Peripherals, Software, Licenses, Maintenance_Logs, Disposal_Records, Asset_Inventories |
| **Procurement & Vendors** | Suppliers, Contacts, Subscriptions, Contracts, Purchases, Budgets, Payment_Methods, Cost_Centers, Requirements, Opportunities |
| **Services & Credentials** | Business_Services, Service_Components, Configurations, Credentials, Credential_Secrets, Certificates, Certificate_Versions |
| **Security & Risks** | Risks, Threat_Types, Security_Activities, Activity_Executions, Security_Assessments, Risk_Assessments |
| **Incidents & Changes** | Incidents, Post-Incident_Reviews, Changes |
| **Compliance & Audits** | Frameworks, Framework_Controls, Compliance_Links, Compliance_Rules, Audits, Audit_Items, Policies, Policy_Versions |
| **BCDR & HR** | BCDR_Plans, BCDR_Tests, Onboarding, Offboarding, Onboarding_Packs |
| **Documentation & Comms** | Links, Documents, Tags, Attachments, Email_Templates, Campaigns |

Plus an `_Index.xlsx` file with the summary of all files and counts.

### Format of each file

- Title with entity name and export date
- Styled headers (dark blue, white text)
- Status columns with conditional colors (green/yellow/red)
- Long text columns with left alignment and wrap
- Auto-adjusted column widths
- IDs included so relationships between entities can be reconstructed

## Notes

- **Credential secrets** are exported masked (as stored in the DB, never the real value).
- **Attachments** are exported as metadata (name, type, ID). The physical files are stored separately in the uploads volume.
- Works with PostgreSQL (production) and with SQLite if a `sqlite:///` URL is passed.
- If a table does not exist (for example in an older version), the sheet is generated with an error message instead of failing.
