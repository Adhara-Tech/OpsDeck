# jira-sync.py — Jira to OpsDeck Sync

Script que lee tickets de un proyecto Jira (filtrados por fecha y label) y los sincroniza a OpsDeck vía su API REST. Usa el campo `external_ref` (set al Jira issue key) para evitar duplicados.

## Requisitos

```bash
pip install requests
```

## Variables de entorno

### Obligatorias

| Variable | Descripción | Ejemplo |
|---|---|---|
| `JIRA_BASE_URL` | URL base de tu instancia Jira | `https://tuorg.atlassian.net` |
| `JIRA_EMAIL` | Email del usuario Jira | `user@example.com` |
| `JIRA_API_TOKEN` | API token de Jira (no password) | `ATATT3x...` |
| `OPSDECK_BASE_URL` | URL base de OpsDeck | `http://localhost:5000` |
| `OPSDECK_API_TOKEN` | Bearer token de OpsDeck (perfil de usuario) | `abc123...` |

### Opcionales

| Variable | Default | Descripción |
|---|---|---|
| `JIRA_PROJECT` | `HELP` | Clave del proyecto Jira |
| `JIRA_LABEL` | `opsdeck-sync` | Label para filtrar tickets |
| `JIRA_DAYS` | `90` | Días de lookback |

## Uso

```bash
# Configurar variables
export JIRA_BASE_URL=https://tuorg.atlassian.net
export JIRA_EMAIL=user@example.com
export JIRA_API_TOKEN=tu-token-jira
export OPSDECK_BASE_URL=http://localhost:5000
export OPSDECK_API_TOKEN=tu-token-opsdeck

# Preview (no escribe nada en OpsDeck)
python scripts/jira-sync.py --dry-run

# Sync real
python scripts/jira-sync.py
```

## Mapeo de tipos

El script clasifica los tickets Jira por su tipo de issue y los envía al endpoint correspondiente de OpsDeck:

| Jira Issue Type | OpsDeck Tipo | Endpoint |
|---|---|---|
| `[System] Change` | Change | `POST /api/v1/changes` |
| `[System] Incident` | Incident | `POST /api/v1/incidents` |
| `Onboarding` | Onboarding | `POST /api/v1/onboardings` |

Los tickets con tipos no reconocidos se marcan como **skipped** en el report.

## Mapeo de campos

### Changes
- `summary` → `title`
- `description` → `description`
- `priority` → `priority` (Highest→Critical, High→High, Medium→Medium, Low/Lowest→Low)
- `reporter` → `requester` (por email)
- `assignee` → `assignee` (por email)
- Jira key → `external_ref`

### Incidents
- `summary` → `title`
- `description` → `description`
- `priority` → `severity` (Highest→SEV-0, High→SEV-1, Medium→SEV-2, Low/Lowest→SEV-3)
- `reporter` → `reported_by` (por email)
- `assignee` → `assignee` (por email)
- Jira key → `external_ref`

### Onboardings
- `summary` → `new_hire_name`
- `created` date → `start_date`
- `reporter` → `manager` (por email)
- Jira key → `external_ref`

## Notas

- El `external_ref` previene duplicados: si un ticket ya existe en OpsDeck con esa referencia, se actualiza en lugar de crear uno nuevo.
- El modo `--dry-run` muestra los payloads completos que se enviarían.
- Los campos custom de Jira para onboarding (start_date, manager, buddy) están comentados en el código. Ajusta los IDs de custom fields a tu instancia.
