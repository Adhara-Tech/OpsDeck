# jira-sync.py — Jira to OpsDeck Sync

Script that reads tickets from a Jira project (filtered by date and label) and syncs them to OpsDeck via its REST API. It uses the `external_ref` field (set to the Jira issue key) to avoid duplicates.

## Requirements

```bash
pip install requests
```

## Environment variables

### Required

| Variable | Description | Example |
|---|---|---|
| `JIRA_BASE_URL` | Base URL of your Jira instance | `https://yourorg.atlassian.net` |
| `JIRA_EMAIL` | Jira user email | `user@example.com` |
| `JIRA_API_TOKEN` | Jira API token (not password) | `ATATT3x...` |
| `OPSDECK_BASE_URL` | OpsDeck base URL | `http://localhost:5000` |
| `OPSDECK_API_TOKEN` | OpsDeck Bearer token (user profile) | `abc123...` |

### Optional

| Variable | Default | Description |
|---|---|---|
| `JIRA_PROJECT` | `HELP` | Jira project key |
| `JIRA_LABEL` | `opsdeck-sync` | Label to filter tickets |
| `JIRA_DAYS` | `90` | Lookback days |

## Usage

```bash
# Configure variables
export JIRA_BASE_URL=https://yourorg.atlassian.net
export JIRA_EMAIL=user@example.com
export JIRA_API_TOKEN=your-jira-token
export OPSDECK_BASE_URL=http://localhost:5000
export OPSDECK_API_TOKEN=your-opsdeck-token

# Preview (writes nothing to OpsDeck)
python scripts/jira-sync.py --dry-run

# Real sync
python scripts/jira-sync.py
```

## Type mapping

The script classifies Jira tickets by their issue type and sends them to the corresponding OpsDeck endpoint:

| Jira Issue Type | OpsDeck Type | Endpoint |
|---|---|---|
| `[System] Change` | Change | `POST /api/v1/changes` |
| `[System] Incident` | Incident | `POST /api/v1/incidents` |
| `Onboarding` | Onboarding | `POST /api/v1/onboardings` |

Tickets with unrecognized types are marked as **skipped** in the report.

## Field mapping

### Changes
- `summary` → `title`
- `description` → `description`
- `priority` → `priority` (Highest→Critical, High→High, Medium→Medium, Low/Lowest→Low)
- `reporter` → `requester` (by email)
- `assignee` → `assignee` (by email)
- Jira key → `external_ref`

### Incidents
- `summary` → `title`
- `description` → `description`
- `priority` → `severity` (Highest→SEV-0, High→SEV-1, Medium→SEV-2, Low/Lowest→SEV-3)
- `reporter` → `reported_by` (by email)
- `assignee` → `assignee` (by email)
- Jira key → `external_ref`

### Onboardings
- `summary` → `new_hire_name`
- `created` date → `start_date`
- `reporter` → `manager` (by email)
- Jira key → `external_ref`

## Notes

- The `external_ref` prevents duplicates: if a ticket already exists in OpsDeck with that reference, it is updated instead of creating a new one.
- `--dry-run` mode shows the full payloads that would be sent.
- The Jira custom fields for onboarding (start_date, manager, buddy) are commented out in the code. Adjust the custom field IDs to your instance.
