#!/usr/bin/env python3
"""
Jira → OpsDeck Sync Script

Reads tickets from a Jira project (filtered by date range and label) and
syncs them to OpsDeck via its REST API. Uses the external_ref field
(set to the Jira issue key) to avoid creating duplicates.

Usage:
    python jira-sync.py                 # Sync tickets to OpsDeck
    python jira-sync.py --dry-run       # Preview only, no writes

Environment variables (required):
    JIRA_BASE_URL       https://yourorg.atlassian.net
    JIRA_EMAIL          user@example.com
    JIRA_API_TOKEN      Jira API token (not password)
    OPSDECK_BASE_URL    http://localhost:5000  (or your VPN address)
    OPSDECK_API_TOKEN   Bearer token from OpsDeck user profile

Environment variables (optional):
    JIRA_PROJECT        Project key (default: HELP)
    JIRA_LABEL          Label filter  (default: opsdeck-sync)
    JIRA_DAYS           Lookback days (default: 90)
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

import requests

# ─── Configuration ──────────────────────────────────────────────────────────

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

OPSDECK_BASE_URL = os.environ.get("OPSDECK_BASE_URL", "").rstrip("/")
OPSDECK_API_TOKEN = os.environ.get("OPSDECK_API_TOKEN", "")

JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "HELP")
JIRA_LABEL = os.environ.get("JIRA_LABEL", "opsdeck-sync")
JIRA_DAYS = int(os.environ.get("JIRA_DAYS", "90"))

# Jira issue type names → OpsDeck resource type
# Jira default types use "[System] Change", "[System] Incident", etc.
# "Onboarding" is a custom type.
ISSUE_TYPE_MAP = {
    "[system] change": "change",
    "[system] incident": "incident",
    "onboarding": "onboarding",
}

# Jira priority → OpsDeck change priority
CHANGE_PRIORITY_MAP = {
    "Highest": "Critical",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Lowest": "Low",
}

# Jira priority → OpsDeck incident severity
INCIDENT_SEVERITY_MAP = {
    "Highest": "SEV-0",
    "High": "SEV-1",
    "Medium": "SEV-2",
    "Low": "SEV-3",
    "Lowest": "SEV-3",
}


# ─── Jira Client ────────────────────────────────────────────────────────────

def jira_get(path, params=None):
    """Make an authenticated GET request to Jira REST API v2."""
    url = f"{JIRA_BASE_URL}/rest/api/2/{path}"
    resp = requests.get(
        url,
        params=params,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_jira_issues():
    """Fetch all matching issues from Jira using pagination."""
    since = (datetime.utcnow() - timedelta(days=JIRA_DAYS)).strftime("%Y-%m-%d")
    jql = (
        f'project = "{JIRA_PROJECT}" '
        f'AND labels = "{JIRA_LABEL}" '
        f'AND created >= "{since}" '
        f"ORDER BY created ASC"
    )

    fields = ",".join([
        "summary", "description", "issuetype", "priority", "status",
        "assignee", "reporter", "created", "labels",
        # Onboarding-specific custom fields (adjust IDs to your Jira instance)
        # "customfield_10100",  # start_date
        # "customfield_10101",  # manager
        # "customfield_10102",  # buddy
    ])

    all_issues = []
    start_at = 0
    max_results = 100

    print(f"  JQL: {jql}")

    while True:
        data = jira_get("search", params={
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields,
        })
        issues = data.get("issues", [])
        all_issues.extend(issues)

        total = data.get("total", 0)
        start_at += len(issues)
        if start_at >= total or not issues:
            break

    print(f"  Found {len(all_issues)} issues in Jira (total: {total})")
    return all_issues


# ─── OpsDeck Client ─────────────────────────────────────────────────────────

def opsdeck_headers():
    return {
        "Authorization": f"Bearer {OPSDECK_API_TOKEN}",
        "Content-Type": "application/json",
    }


def opsdeck_post(endpoint, payload):
    """POST to OpsDeck API. Returns (response_json, status_code)."""
    url = f"{OPSDECK_BASE_URL}/api/v1/{endpoint}"
    resp = requests.post(url, json=payload, headers=opsdeck_headers(), timeout=30)
    return resp.json(), resp.status_code


def opsdeck_get(endpoint, params=None):
    """GET from OpsDeck API. Returns (response_json, status_code)."""
    url = f"{OPSDECK_BASE_URL}/api/v1/{endpoint}"
    resp = requests.get(url, params=params, headers=opsdeck_headers(), timeout=30)
    return resp.json(), resp.status_code


# ─── Field Mapping ──────────────────────────────────────────────────────────

def get_email(user_field):
    """Extract email from a Jira user field (may be None)."""
    if not user_field:
        return None
    return user_field.get("emailAddress")


def map_change(issue):
    """Map a Jira issue to an OpsDeck Change payload."""
    f = issue["fields"]
    priority_name = (f.get("priority") or {}).get("name", "Medium")
    return {
        "title": f["summary"],
        "description": f.get("description") or "",
        "priority": CHANGE_PRIORITY_MAP.get(priority_name, "Medium"),
        "status": "Draft",
        "requester": get_email(f.get("reporter")),
        "assignee": get_email(f.get("assignee")),
        "external_ref": issue["key"],
    }


def map_incident(issue):
    """Map a Jira issue to an OpsDeck Incident payload."""
    f = issue["fields"]
    priority_name = (f.get("priority") or {}).get("name", "Medium")
    return {
        "title": f["summary"],
        "description": f.get("description") or "No description provided",
        "severity": INCIDENT_SEVERITY_MAP.get(priority_name, "SEV-3"),
        "status": "Investigating",
        "reported_by": get_email(f.get("reporter")),
        "assignee": get_email(f.get("assignee")),
        "external_ref": issue["key"],
    }


def map_onboarding(issue):
    """Map a Jira issue to an OpsDeck Onboarding payload."""
    f = issue["fields"]
    # Extract start_date from the issue created date as fallback
    created = f.get("created", "")[:10]  # "2026-01-15T10:00:00..." → "2026-01-15"
    return {
        "new_hire_name": f["summary"],
        "start_date": created,
        "status": "Provisioning",
        "manager": get_email(f.get("reporter")),
        "external_ref": issue["key"],
    }


MAPPERS = {
    "change": ("changes", map_change),
    "incident": ("incidents", map_incident),
    "onboarding": ("onboardings", map_onboarding),
}


# ─── Classification ─────────────────────────────────────────────────────────

def classify_issue(issue):
    """Determine the OpsDeck resource type from the Jira issue type name."""
    type_name = issue["fields"]["issuetype"]["name"].lower().strip()
    # Exact match first, then substring fallback
    if type_name in ISSUE_TYPE_MAP:
        return ISSUE_TYPE_MAP[type_name]
    for keyword, resource_type in ISSUE_TYPE_MAP.items():
        if keyword in type_name:
            return resource_type
    return None


# ─── Sync Logic ─────────────────────────────────────────────────────────────

def sync(dry_run=False):
    """Main sync logic."""
    print("\n── Jira → OpsDeck Sync ──────────────────────────────────")
    print(f"  Jira:    {JIRA_BASE_URL} (project: {JIRA_PROJECT})")
    print(f"  OpsDeck: {OPSDECK_BASE_URL}")
    print(f"  Label:   {JIRA_LABEL}")
    print(f"  Window:  last {JIRA_DAYS} days")
    print(f"  Mode:    {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    issues = fetch_jira_issues()
    if not issues:
        print("\n  No issues found. Nothing to do.")
        return

    # Classify issues
    classified = {"change": [], "incident": [], "onboarding": [], "skipped": []}
    for issue in issues:
        rtype = classify_issue(issue)
        if rtype:
            classified[rtype].append(issue)
        else:
            classified["skipped"].append(issue)

    print(f"\n  Classified: "
          f"{len(classified['change'])} changes, "
          f"{len(classified['incident'])} incidents, "
          f"{len(classified['onboarding'])} onboardings, "
          f"{len(classified['skipped'])} skipped")

    if classified["skipped"]:
        print("\n  Skipped issues (unrecognized type):")
        for issue in classified["skipped"]:
            itype = issue["fields"]["issuetype"]["name"]
            print(f"    {issue['key']} [{itype}] {issue['fields']['summary']}")

    # Process each type
    stats = {"created": 0, "updated": 0, "errors": 0, "skipped_type": len(classified["skipped"])}
    results = []

    for rtype in ("change", "incident", "onboarding"):
        group = classified[rtype]
        if not group:
            continue

        endpoint, mapper = MAPPERS[rtype]
        print(f"\n  Processing {len(group)} {rtype}(s)...")

        for issue in group:
            key = issue["key"]
            summary = issue["fields"]["summary"]
            payload = mapper(issue)

            if dry_run:
                # In dry-run mode, just report what would happen
                results.append({
                    "key": key,
                    "type": rtype,
                    "summary": summary,
                    "action": "would sync",
                    "payload": payload,
                })
                continue

            try:
                resp_data, status_code = opsdeck_post(endpoint, payload)
                if status_code == 201:
                    action = "CREATED"
                    stats["created"] += 1
                elif status_code == 200:
                    action = "UPDATED"
                    stats["updated"] += 1
                else:
                    action = f"ERROR ({status_code})"
                    stats["errors"] += 1

                results.append({
                    "key": key,
                    "type": rtype,
                    "summary": summary,
                    "action": action,
                    "status_code": status_code,
                })
                print(f"    {action}: {key} — {summary}")
            except requests.RequestException as e:
                stats["errors"] += 1
                results.append({
                    "key": key,
                    "type": rtype,
                    "summary": summary,
                    "action": f"ERROR: {e}",
                })
                print(f"    ERROR: {key} — {e}")

    # ─── Report ─────────────────────────────────────────────────────────

    print("\n── Report ──────────────────────────────────────────────")

    if dry_run:
        print(f"\n  DRY RUN — no tickets were created or updated in OpsDeck.\n")
        print(f"  {'Key':<16} {'Type':<12} {'Summary'}")
        print(f"  {'─' * 15} {'─' * 11} {'─' * 50}")
        for r in results:
            print(f"  {r['key']:<16} {r['type']:<12} {r['summary'][:50]}")

        print(f"\n  Would sync {len(results)} ticket(s):")
        by_type = {}
        for r in results:
            by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        for t, count in sorted(by_type.items()):
            print(f"    {t}: {count}")

        if classified["skipped"]:
            print(f"    skipped (unknown type): {len(classified['skipped'])}")

        print(f"\n  Payloads that would be sent:")
        for r in results:
            print(f"\n    {r['key']} ({r['type']}):")
            for k, v in r["payload"].items():
                val = str(v)[:80] if v else "—"
                print(f"      {k}: {val}")
    else:
        print(f"\n  Created:  {stats['created']}")
        print(f"  Updated:  {stats['updated']}")
        print(f"  Errors:   {stats['errors']}")
        print(f"  Skipped:  {stats['skipped_type']} (unknown type)")
        print(f"  Total:    {stats['created'] + stats['updated'] + stats['errors']}")

    print("\n── Done ────────────────────────────────────────────────\n")


# ─── CLI ────────────────────────────────────────────────────────────────────

def validate_env():
    """Check that required environment variables are set."""
    missing = []
    for var in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN",
                "OPSDECK_BASE_URL", "OPSDECK_API_TOKEN"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        print(f"Error: missing required environment variables:\n  {', '.join(missing)}")
        print("\nSet them before running this script. Example:")
        print("  export JIRA_BASE_URL=https://yourorg.atlassian.net")
        print("  export JIRA_EMAIL=you@example.com")
        print("  export JIRA_API_TOKEN=your-jira-token")
        print("  export OPSDECK_BASE_URL=http://localhost:5000")
        print("  export OPSDECK_API_TOKEN=your-opsdeck-token")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Jira tickets to OpsDeck (changes, incidents, onboardings)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch from Jira and report what would be synced, without writing to OpsDeck",
    )
    args = parser.parse_args()

    validate_env()
    sync(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
