#!/usr/bin/env python3
"""
Google Workspace → OpsDeck User Import

Reads users from Google Workspace (optionally scoped to an organizational unit
and its sub-OUs) and imports the ones that do not yet exist in OpsDeck, via the
OpsDeck REST API. Existing users (matched by email) are left untouched.

Usage:
    python google-import.py --dry-run                       # Preview what would be imported
    python google-import.py --execute                       # Import missing users
    python google-import.py --org-unit /Employees --dry-run # Scope to an OU (and its sub-OUs)
    python google-import.py --org-unit /Employees --execute

Environment variables (required):
    GOOGLE_SERVICE_ACCOUNT_JSON   Path to service account JSON file
    GOOGLE_DELEGATED_USER         Admin email for domain-wide delegation
    OPSDECK_URL                   OpsDeck base URL (e.g. https://opsdeck.internal)
    OPSDECK_API_TOKEN             Bearer token (admin role required)

Environment variables (optional):
    GOOGLE_DOMAIN                 Only import users whose email ends with @this-domain
    OPSDECK_DEFAULT_ROLE          Role assigned to imported users (default: user)
"""

import argparse
import os
import sys

import requests

# ─── Configuration ──────────────────────────────────────────────────────────

GOOGLE_SA_JSON_PATH = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_DELEGATED_USER = os.environ.get("GOOGLE_DELEGATED_USER", "")
GOOGLE_DOMAIN = os.environ.get("GOOGLE_DOMAIN", "")

OPSDECK_URL = os.environ.get("OPSDECK_URL", "").rstrip("/")
OPSDECK_API_TOKEN = os.environ.get("OPSDECK_API_TOKEN", "")
OPSDECK_DEFAULT_ROLE = os.environ.get("OPSDECK_DEFAULT_ROLE", "user")

# Read-only scope: this script never writes to Google. Make sure this scope is
# authorized for the service account in the Google admin console (domain-wide
# delegation), alongside any scopes used by google-provision.py.
GOOGLE_SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"

# Page size when listing Google users (max allowed by the Directory API is 500).
GOOGLE_PAGE_SIZE = 500
# Page size when listing existing OpsDeck users.
OPSDECK_PAGE_SIZE = 200


# ─── Google Admin SDK Client ───────────────────────────────────────────────

def get_google_service():
    """Build an authenticated Google Admin SDK service using a service account."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print("Error: google-auth and google-api-python-client are required.")
        print("Install with: pip install google-auth google-api-python-client")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_SA_JSON_PATH,
        scopes=[GOOGLE_SCOPE],
        subject=GOOGLE_DELEGATED_USER,
    )
    return build("admin", "directory_v1", credentials=credentials)


def list_google_users(service, org_unit=None, include_suspended=False):
    """
    List active Google Workspace users, optionally scoped to an org unit and
    its sub-OUs. Filtering by OU is done client-side (prefix match on
    orgUnitPath) so that the "exact OU + sub-OUs" semantics are deterministic
    regardless of server-side search behavior.
    """
    ou_prefix = org_unit.rstrip("/") if org_unit and org_unit != "/" else None
    users = []
    page_token = None

    while True:
        resp = service.users().list(
            customer="my_customer",
            maxResults=GOOGLE_PAGE_SIZE,
            orderBy="email",
            pageToken=page_token,
            projection="full",  # needed for organizations[].department/title
        ).execute()

        for guser in resp.get("users", []):
            if guser.get("suspended") and not include_suspended:
                continue

            email = guser.get("primaryEmail", "")
            if GOOGLE_DOMAIN and not email.endswith(f"@{GOOGLE_DOMAIN}"):
                continue

            if ou_prefix is not None:
                path = guser.get("orgUnitPath", "")
                if not (path == ou_prefix or path.startswith(ou_prefix + "/")):
                    continue

            users.append(guser)

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return users


def map_google_user(guser):
    """Map a Google user object to an OpsDeck user payload."""
    name = guser.get("name", {}).get("fullName") or guser["primaryEmail"]
    payload = {
        "email": guser["primaryEmail"],
        "name": name,
        "role": OPSDECK_DEFAULT_ROLE,
    }
    orgs = guser.get("organizations") or []
    if orgs:
        if orgs[0].get("department"):
            payload["department"] = orgs[0]["department"]
        if orgs[0].get("title"):
            payload["job_title"] = orgs[0]["title"]
    return payload


# ─── OpsDeck API Client ───────────────────────────────────────────────────

def opsdeck_headers():
    return {
        "Authorization": f"Bearer {OPSDECK_API_TOKEN}",
        "Content-Type": "application/json",
    }


def opsdeck_existing_emails():
    """Return a set of lowercased emails of all users already in OpsDeck."""
    emails = set()
    offset = 0
    while True:
        url = f"{OPSDECK_URL}/api/v1/users"
        resp = requests.get(
            url,
            headers=opsdeck_headers(),
            params={"limit": OPSDECK_PAGE_SIZE, "offset": offset},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        for u in batch:
            if u.get("email"):
                emails.add(u["email"].lower())
        if len(batch) < OPSDECK_PAGE_SIZE:
            break
        offset += OPSDECK_PAGE_SIZE
    return emails


def opsdeck_create_user(payload):
    """Create (upsert by email) a user in OpsDeck."""
    url = f"{OPSDECK_URL}/api/v1/users"
    resp = requests.post(url, json=payload, headers=opsdeck_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─── Import (Google → OpsDeck) ──────────────────────────────────────────────

def import_users(dry_run=True, org_unit=None, include_suspended=False):
    """Import Google Workspace users that don't yet exist in OpsDeck."""
    print("\n── Import: Google → OpsDeck ────────────────────────────")
    print(f"  Mode:      {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"  Org unit:  {org_unit or '(all)'}{' + sub-OUs' if org_unit and org_unit != '/' else ''}")
    print(f"  Role:      {OPSDECK_DEFAULT_ROLE}")
    print(f"  Suspended: {'included' if include_suspended else 'skipped'}")
    print()

    existing = opsdeck_existing_emails()
    print(f"  OpsDeck currently has {len(existing)} user(s).")

    service = get_google_service()
    google_users = list_google_users(service, org_unit, include_suspended)
    print(f"  Google returned {len(google_users)} user(s) in scope.\n")

    stats = {"imported": 0, "skipped": 0, "errors": 0}

    for guser in google_users:
        email = guser["primaryEmail"]
        if email.lower() in existing:
            stats["skipped"] += 1
            continue

        payload = map_google_user(guser)

        if dry_run:
            print(f"  Would IMPORT: {email} ({payload['name']})")
            print(f"    dept: {payload.get('department', '')}, title: {payload.get('job_title', '')}")
            stats["imported"] += 1
            continue

        try:
            opsdeck_create_user(payload)
            print(f"  IMPORTED: {email}")
            existing.add(email.lower())
            stats["imported"] += 1
        except Exception as e:
            print(f"  ERROR: {email} — {e}")
            stats["errors"] += 1

    verb = "would be imported" if dry_run else "imported"
    print(f"\n  Summary: {stats['imported']} {verb}, "
          f"{stats['skipped']} already existed, {stats['errors']} errors")
    return stats


# ─── CLI ────────────────────────────────────────────────────────────────────

def validate_env():
    """Check that required environment variables are set."""
    missing = [
        var for var in (
            "GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_DELEGATED_USER",
            "OPSDECK_URL", "OPSDECK_API_TOKEN",
        ) if not os.environ.get(var)
    ]
    if missing:
        print(f"Error: missing required environment variables:\n  {', '.join(missing)}")
        print("\nSet them before running this script. See --help for details.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Import Google Workspace users into OpsDeck (Google → OpsDeck)",
    )
    parser.add_argument(
        "--org-unit",
        default=None,
        metavar="/PATH",
        help="Only import users in this org unit and its sub-OUs (default: all users)",
    )
    parser.add_argument(
        "--include-suspended",
        action="store_true",
        help="Also import suspended Google users (default: skip them)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be imported without making changes",
    )
    group.add_argument(
        "--execute",
        action="store_true",
        help="Actually create the missing users in OpsDeck",
    )
    args = parser.parse_args()

    validate_env()

    print("\n══ Google Workspace → OpsDeck User Import ══════════════")
    print(f"  OpsDeck: {OPSDECK_URL}")
    print(f"  Google:  delegated as {GOOGLE_DELEGATED_USER}")
    print(f"  Mode:    {'DRY RUN' if args.dry_run else 'EXECUTE'}")

    import_users(
        dry_run=args.dry_run,
        org_unit=args.org_unit,
        include_suspended=args.include_suspended,
    )

    print("\n══ Done ════════════════════════════════════════════════\n")


if __name__ == "__main__":
    main()
