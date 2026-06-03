# google-import.py — Google Workspace to OpsDeck User Import

Script that reads users from Google Workspace and imports the ones that do **not** yet exist in OpsDeck, via its REST API. You can scope the import to a specific organizational unit (and its sub-OUs). Existing users are matched by email and left untouched. This is the reverse direction of `google-provision.py` (which provisions Google users from OpsDeck onboardings).

## Requirements

```bash
pip install requests google-auth google-api-python-client
```

## Environment variables

### Required

| Variable | Description | Example |
|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to the service account JSON | `/etc/opsdeck/sa.json` |
| `GOOGLE_DELEGATED_USER` | Admin email for domain-wide delegation | `admin@yourdomain.com` |
| `OPSDECK_URL` | OpsDeck base URL | `https://opsdeck.internal` |
| `OPSDECK_API_TOKEN` | Bearer token (requires admin role) | `abc123...` |

### Optional

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_DOMAIN` | *(empty)* | Only import users whose email ends with `@this-domain` |
| `OPSDECK_DEFAULT_ROLE` | `user` | Role assigned to imported users |

## Usage

```bash
# Configure variables
export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
export GOOGLE_DELEGATED_USER=admin@yourdomain.com
export OPSDECK_URL=https://opsdeck.internal
export OPSDECK_API_TOKEN=your-opsdeck-token

# Preview all missing users (creates nothing)
python scripts/google-import.py --dry-run

# Import all missing users
python scripts/google-import.py --execute

# Scope to an org unit and its sub-OUs
python scripts/google-import.py --org-unit /Employees --dry-run
python scripts/google-import.py --org-unit /Employees --execute

# Also import suspended Google accounts (skipped by default)
python scripts/google-import.py --execute --include-suspended
```

`--dry-run` or `--execute` is always required to avoid accidental runs.

## Options

| Option | Description |
|---|---|
| `--org-unit /PATH` | Only import users in this OU and its sub-OUs. Omit to import all users. |
| `--include-suspended` | Also import suspended Google users (default: skip them). |
| `--dry-run` / `--execute` | Preview vs. apply. One is required. |

## Flow

1. Lists all existing OpsDeck users via `GET /api/v1/users` (paginated) and builds a set of known emails.
2. Lists Google Workspace users via the Admin Directory API (paginated, `customer=my_customer`).
3. Filters Google users:
   - Skips suspended accounts (unless `--include-suspended`).
   - Skips emails outside `GOOGLE_DOMAIN` (if configured).
   - If `--org-unit` is set, keeps only users whose `orgUnitPath` matches the OU exactly or is a sub-OU of it. This prefix filter is applied client-side so the "exact OU + sub-OUs" behavior is deterministic.
4. For each Google user not already in OpsDeck, creates it via `POST /api/v1/users` with: email, full name, role (`OPSDECK_DEFAULT_ROLE`), and department/job title if present in Google.

## Field mapping

| Google | OpsDeck |
|---|---|
| `primaryEmail` | `email` (unique key, used for dedup) |
| `name.fullName` | `name` |
| `organizations[0].department` | `department` |
| `organizations[0].title` | `job_title` |
| *(constant)* | `role` = `OPSDECK_DEFAULT_ROLE` |

## Google Cloud configuration

For the script to work you need:

1. **Service Account** with domain-wide delegation enabled (the same one used by `google-provision.py` works).
2. **Scope** authorized in the Google admin console: `https://www.googleapis.com/auth/admin.directory.user.readonly` (read-only — this script never writes to Google).
3. **JSON key** of the service account downloaded and referenced in `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Notes

- Both `--dry-run` and `--execute` read from Google **and** OpsDeck (the source is Google, so it must be queried to know what would be imported). Only the user creation is skipped in `--dry-run`.
- The `POST /api/v1/users` endpoint upserts by email, so re-running is idempotent: users that already exist are detected up front and skipped, and any race is harmless.
- Imported users have no password set (`password_hash` is nullable). They sign in via your configured login method; set or reset credentials separately if needed.
- Designed to run unattended (e.g. a periodic Kubernetes CronJob): it only needs the OpsDeck service URL + API token and the Google service account, with no direct database access.
