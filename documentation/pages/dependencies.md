# Dependencies

Complete list of Python dependencies used by OpsDeck, what they do, and where they are used.

## Production Dependencies (`requirements.txt`)

| Package | Version | Purpose | Used in |
|---------|---------|---------|---------|
| APScheduler | 3.11.0 | Background task scheduler | `src/__init__.py` — schedules 7 recurring jobs: renewal checks, credential/certificate expiry, exchange rate updates, communications queue, UAR comparisons, compliance drift detection |
| boto3 | >=1.34.0 | AWS SDK | Enterprise plugin only (`opsdeck-enterprise/connectors/aws.py`) — fetches IAM users/roles, S3 buckets, Secrets Manager metadata |
| cryptography | >=41.0.0 | Cryptographic primitives | Transitive dependency of PyJWT (RS256 algorithm support) and Flask-Dance (OAuth token handling). No direct imports in core |
| deepdiff | — | Deep comparison of objects | `src/utils/differ.py` — semantic diff for configuration/audit change tracking |
| ecs-logging | — | ECS structured logging | `src/__init__.py` — formats application logs to Elasticsearch Common Schema (JSON) with rotation (10 MB, 5 backups) |
| Flask | 3.1.2 | Web framework | Core of the application — routing, templates, sessions, blueprints, error handling |
| Flask-Dance | — | OAuth integration | `src/__init__.py` — Google OAuth SSO via `make_google_blueprint` |
| Flask-Login | — | User session management | `src/extensions.py` — `LoginManager` initialization, `current_user` proxy |
| Flask-Migrate | 4.1.0 | Database migrations | `src/extensions.py`, `migrations/env.py` — Alembic wrapper for `flask db migrate` / `flask db upgrade` |
| Flask-SQLAlchemy | 3.1.1 | ORM integration | `src/extensions.py` — the `db` object used across all models and routes |
| flask-limiter | — | Rate limiting | `src/__init__.py` — global limits (200/day, 50/hour), login endpoint (5/min), logs breaches to audit log |
| flask-smorest | — | REST API + OpenAPI docs | `src/__init__.py`, `src/api.py` — `/api/v1` endpoints with auto-generated Swagger UI at `/swagger-ui` |
| flask-talisman | — | HTTP security headers | `src/__init__.py` — forces HTTPS in production, Content Security Policy headers |
| Flask-WTF | — | CSRF protection | `src/__init__.py` — global `CSRFProtect()` for all forms |
| gunicorn | 23.0.0 | WSGI HTTP server | `entrypoint.sh` — production application server. No Python imports, used as CLI |
| Markdown | >=3.0 | Markdown to HTML | `src/__init__.py` — Jinja2 `\|markdown` template filter with extensions (tables, code highlighting, TOC) |
| MarkupSafe | 3.0.3 | Safe HTML strings | `src/__init__.py`, `src/routes/main.py` — wraps rendered Markdown with `Markup()`, also powers the `nl2br` filter |
| marshmallow-sqlalchemy | — | Model serialization | `src/schemas.py` — auto-generates API schemas for User, Asset, Peripheral, License, Subscription, Service |
| psycopg2-binary | — | PostgreSQL adapter | Database driver. No direct imports — SQLAlchemy uses it when connecting to `postgresql://` URIs |
| PyJWT | >=2.8.0 | JSON Web Tokens | Enterprise plugin (`opsdeck-enterprise/connectors/google.py`) — signs service account JWTs for Google API auth |
| python-dateutil | 2.9.0.post0 | Date arithmetic | `relativedelta` used extensively in procurement models, reports, subscriptions, compliance, and asset warranty calculations |
| python-dotenv | 1.1.1 | .env file loading | Auto-detected by Flask — when installed, Flask CLI automatically loads `.env` and `.flaskenv` files. No explicit `load_dotenv()` call needed |
| pytz | 2024.2 | Timezone support | `src/utils/timezone_helper.py` — powers `now()`, `today()`, `to_local()` functions with DST-aware calculations (default: Europe/Madrid) |
| requests | 2.32.5 | HTTP client | `src/services/finance_service.py` (Frankfurter API for exchange rates), `src/notifications.py` (webhook delivery). Also used by enterprise connectors |
| slack_sdk | — | Slack integration | `src/services/slack_service.py` — sends notifications to Slack channels, resolves email-to-user-ID with caching |
| weasyprint | 68.0 | HTML to PDF | PDF export across multiple modules: audit reports, compliance matrices, risk assessments, org charts, financial reports |

## Development Dependencies (`requirements-dev.txt`)

| Package | Version | Purpose | Used in |
|---------|---------|---------|---------|
| Faker | 19.13.0 | Fake data generation | `src/seeder.py` — generates realistic demo data (suppliers, users, subscriptions) for `flask seed` CLI command |
| pytest | 9.0.1 | Testing framework | `tests/` — test fixtures, assertions, parametrization across 30+ test files |

## Notes

- **boto3**, **PyJWT**, and **cryptography** are primarily used by the enterprise plugin but are included in core `requirements.txt` because the plugin is installed at runtime (via `pip install -e` in `entrypoint.sh`) and these packages require compiled C extensions that benefit from being pre-built in the Docker image.
- **Faker** is in `requirements-dev.txt` but is imported by `src/seeder.py` which ships in the production image. The `flask seed` command will fail in production if Faker is not installed — this is intentional, as demo seeding should not be run in production. The `flask seed-prod` command (in `src/seeder_prod.py`) does not use Faker.
- **python-dotenv** has no explicit import — Flask auto-detects it at startup. See [Flask docs on environment variables](https://flask.palletsprojects.com/en/latest/cli/#environment-variables-from-dotenv).
- **psycopg2-binary** is the pre-compiled variant for convenience. For production deployments requiring maximum performance, consider switching to `psycopg2` (requires `libpq-dev` build dependency).
