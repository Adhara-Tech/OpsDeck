# OpsDeck Architecture

This document provides an overview of OpsDeck's technical architecture and design principles.

## Design Philosophy

OpsDeck is built on several core principles:

**Compliance-First Design**
All features are designed with audit requirements in mind. The system maintains comprehensive logs, enforces data integrity, and provides clear audit trails for all operations.

**Integrated Data Model**
Rather than treating assets, users, services, and compliance as separate domains, OpsDeck uses an interconnected data model where entities can be linked across domains. This enables traceability and impact analysis.

**Extensibility Without Complexity**
The platform uses a modular blueprint architecture that allows features to be added or disabled without affecting core functionality. Configuration is environment-based rather than database-driven where possible.

## System Architecture

### Application Layer

**Flask Application**
- Blueprint-based modular design
- Each major feature area has its own blueprint (assets, compliance, services, etc.)
- Shared utilities and services layer for cross-cutting concerns

**Authentication & Authorization**
- Session-based authentication with secure cookie handling
- OAuth integration (Google) for SSO
- MFA support with TOTP
- Role-Based Access Control (RBAC) with granular permissions
- API authentication via bearer tokens

**Background Processing**
- APScheduler for scheduled tasks
- Jobs include: UAR execution, drift detection, renewal notifications, data retention
- Jobs run within the application context with full database access

### Data Layer

**ORM & Database**
- SQLAlchemy ORM for database abstraction
- Flask-Migrate for schema versioning
- Requires PostgreSQL (MySQL community-supported)
- Soft deletes and audit fields on all major entities

**Data Model Structure**
Core entities include:
- **Assets**: IT assets with lifecycle tracking
- **Users**: Internal users and their access
- **Services**: Business services with dependency graphs
- **Compliance**: Frameworks, controls, evidence links
- **Security**: Incidents, risks, activities
- **Vendors**: Suppliers, contacts, contracts
- **Audits**: Compliance snapshots and UAR findings

**Relationships**
Most entities support polymorphic linking:
- Assets can be linked to services, compliance controls, risks
- Policies can be acknowledged by users and linked to controls
- Security activities can be linked to multiple entity types

### Presentation Layer

**Templates**
- Server-side rendering with Jinja2
- Bootstrap 5 for responsive design
- Progressive enhancement for better UX without JavaScript dependencies

**Client-Side**
- Minimal JavaScript for interactive features (search, bulk operations)
- No heavy frontend framework required
- AJAX for API interactions without page reloads

### Integration Layer

**REST API**
- RESTful endpoints for all major entities
- OpenAPI/Swagger documentation at `/swagger-ui`
- Pagination, filtering, and sorting support
- JSON response format

**Import/Export**
- CSV import for bulk data loading
- CLI commands for data management
- Export capabilities for reporting and analysis

**Notifications**
- Email notifications via SMTP
- Webhook support for external integrations (Slack, Discord, etc.)
- Configurable notification rules

## Security Model

### Authentication Flow

1. User provides credentials (username/password or OAuth)
2. System validates credentials and checks account status
3. If MFA enabled, TOTP token is required
4. Session cookie issued with secure flags (HttpOnly, Secure, SameSite)
5. Session stored server-side with user identity and permissions

### Authorization Model

**Roles**
- **Admin**: Full system access, user management, configuration
- **Manager**: Read/write access to operational data, limited admin functions
- **User**: Read access to assigned data, limited write access
- **API**: Programmatic access via token (permissions tied to user)

**Permissions**
Fine-grained permissions checked at route level:
- `can_read(resource)`: View access
- `can_write(resource)`: Create/update access
- `can_delete(resource)`: Delete access

### Data Protection

**Sensitive Data**
- Credentials stored encrypted using Fernet symmetric encryption
- Passwords hashed using Werkzeug security (PBKDF2)
- API tokens hashed before storage

**Audit Logging**
- All modifications logged with user, timestamp, and change details
- Immutable audit records prevent tampering
- Centralized logging captures authentication events

## Deployment Architecture

### Single-Server Deployment
Suitable for small to medium installations:
- Application server (Gunicorn/uWSGI)
- PostgreSQL database
- Nginx reverse proxy for HTTPS termination
- All components on single host

### Containerized Deployment
Recommended for production:
- Docker container for application
- Separate container for database (PostgreSQL)
- Volume mounts for data persistence
- Environment-based configuration

### Kubernetes Deployment
For high availability and scale:
- Helm chart provided for deployment
- Horizontal pod autoscaling supported
- External PostgreSQL database recommended
- Ingress for load balancing and TLS

## Scalability Considerations

**Database**
- Most queries use indexes on foreign keys and date fields
- Pagination limits result set size
- Soft deletes prevent data accumulation (archival process recommended)

**Background Jobs**
- Scheduled jobs run serially to prevent resource contention
- Long-running jobs (UAR execution) include progress logging
- Failed jobs logged for troubleshooting

**File Storage**
- Attachments and uploads stored in filesystem by default
- S3-compatible storage can be configured for cloud deployments
- File metadata stored in database for search and access control

## Monitoring & Observability

**Application Logs**
- Structured logging with log levels (DEBUG, INFO, WARNING, ERROR)
- Logs include user context, request IDs, and timestamps
- Configurable log output (console, file, syslog)

**Health Checks**
- `/health` endpoint for monitoring
- Database connectivity check
- Scheduler status check

**Metrics**
Integration points for:
- Prometheus metrics export
- Application Performance Monitoring (APM) tools
- Log aggregation platforms (ELK, Splunk)

## Extensibility

### Plugin Architecture (Future)
OpsDeck is designed to support plugins for enterprise features:
- LDAP/Active Directory integration
- Advanced reporting and dashboards
- Custom compliance frameworks
- Third-party integrations

### API-First Extensions
Custom functionality can be added by:
- Using the REST API for data access
- Building external services that integrate via webhooks
- Creating custom reports using API data exports

### Database Extensions
New entity types can be added by:
- Creating new models in `src/models/`
- Adding blueprints in `src/routes/`
- Registering in application factory
- Running migrations to update schema
