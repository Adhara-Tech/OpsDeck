# Frequently Asked Questions

## General

**What is OpsDeck?**
OpsDeck is an integrated IT operations and governance platform that consolidates asset management, compliance monitoring, service catalog, risk management, and vendor tracking into a single system.

**Who should use OpsDeck?**
Mid-market IT teams (50-500 employees) in regulated industries that need operational rigor without enterprise complexity. Typical users include IT teams pursuing SOC 2 or ISO 27001 certification, financial services companies with SOX requirements, or healthcare organizations managing HIPAA compliance.

**How does OpsDeck differ from ServiceNow?**
OpsDeck focuses on core IT operations and compliance for mid-market teams. It provides essential governance capabilities without the complexity, cost, and implementation overhead of enterprise platforms. ServiceNow is better suited for large enterprises with dedicated IT operations teams and complex ITSM requirements.

**Is OpsDeck open source?**
OpsDeck is released under the Elastic License, which allows free use, modification, and distribution but restricts offering OpsDeck as a managed service to third parties.

**What does OpsDeck cost?**
The core OpsDeck platform is free under the Elastic License. Enterprise features (LDAP integration, SAML SSO, multi-tenancy) are available under a separate commercial license.

## Technical

**What are the system requirements?**
Minimum:
- 2 CPU cores
- 4GB RAM
- 20GB disk space
- Python 3.8+
- SQLite or PostgreSQL

Recommended for production:
- 4 CPU cores
- 8GB RAM
- 100GB disk space (depending on attachment storage)
- PostgreSQL 12+

**Can OpsDeck run on Windows?**
Yes, but Linux is recommended for production deployments. Windows can be used for development or evaluation.

**Does OpsDeck support high availability?**
Not natively in the core platform. For high availability:
- Deploy multiple application instances behind a load balancer
- Use PostgreSQL with replication
- Consider Kubernetes deployment with pod autoscaling

**What databases are supported?**
- SQLite (development and small deployments)
- PostgreSQL (recommended for production)
- MySQL (community-supported, not officially tested)

**How does OpsDeck handle upgrades?**
Database migrations are managed via Flask-Migrate (Alembic):
```bash
flask db upgrade
```
Always backup your database before upgrading.

**Can I customize the interface?**
The platform uses Jinja2 templates that can be modified. Custom branding (logos, colors) requires modifying templates and CSS. Enterprise plugin will provide UI customization options.

## Security

**How are passwords stored?**
User passwords are hashed using Werkzeug's security module (PBKDF2 with salt). Credentials stored in the vault are encrypted using Fernet symmetric encryption.

**Does OpsDeck support SSO?**
OAuth (Google) is supported in the core platform. SAML 2.0 SSO and LDAP/Active Directory integration are available in the Enterprise plugin.

**Is multi-factor authentication (MFA) supported?**
Yes, TOTP-based MFA can be enabled. Users configure MFA using authenticator apps (Google Authenticator, Authy, etc.).

**How are API tokens secured?**
API tokens are hashed before storage. The plain token is only shown once during generation. Tokens can be revoked at any time.

**Does OpsDeck have audit logging?**
Yes, comprehensive audit logs track user actions, authentication events, and data modifications. Logs include user identity, timestamp, action, and affected resources.

**Can OpsDeck integrate with SIEM systems?**
Application logs can be sent to syslog or log aggregation platforms. Integration with SIEM systems (Splunk, ELK) is achieved by ingesting OpsDeck logs.

## Deployment

**Should I use Docker?**
Yes, Docker deployment is recommended. It simplifies installation, ensures consistent environment, and makes upgrades easier.

**Can OpsDeck run in AWS/Azure/GCP?**
Yes, OpsDeck can run on any cloud platform:
- Deploy Docker container on compute instances (EC2, Azure VM, GCE)
- Use managed database services (RDS, Azure Database, Cloud SQL)
- Store attachments in object storage (S3, Azure Blob, GCS)

**What's the recommended production architecture?**
- Application: Docker container with Gunicorn running 4-8 workers
- Database: PostgreSQL with automated backups
- Reverse Proxy: Nginx with TLS termination
- Monitoring: Application logs to centralized logging, health check endpoint

**How do I backup OpsDeck?**
Backup requirements:
- Database: pg_dump for PostgreSQL or file copy for SQLite
- File storage: Backup data directory containing uploads
- Configuration: Backup .env file (store securely)

Recommended frequency: Daily automated backups with 30-day retention.

**Can OpsDeck scale horizontally?**
Application layer can scale by running multiple containers behind a load balancer. Database scaling depends on PostgreSQL configuration (read replicas, connection pooling).

## Compliance

**Which compliance frameworks are supported?**
Out of the box:
- SOC 2 Type II
- ISO 27001:2013 / 2022
- Custom frameworks can be imported

Additional frameworks can be added by creating framework and control definitions.

**Does OpsDeck help with audit preparation?**
Yes, OpsDeck is specifically designed for audit defense:
- Continuous evidence collection through compliance links
- Audit snapshots create immutable records
- Gap analysis identifies controls without evidence
- Export capabilities for auditor review

**Can OpsDeck replace a GRC platform?**
OpsDeck provides core GRC capabilities (compliance frameworks, risk management, audit trails) but is not a pure-play GRC platform. It excels when compliance needs are tied to IT operations (asset management, access reviews, security activities).

For organizations needing only GRC without IT operations, dedicated GRC platforms (Vanta, Drata, LogicGate) may be more appropriate.

**What is UAR (User Access Review)?**
UAR automates the comparison of user access across systems to detect orphaned accounts, mismatches, or unauthorized access. OpsDeck supports scheduled comparisons with configurable data sources (CSV, database, API).

**How does compliance drift detection work?**
OpsDeck captures daily snapshots of compliance status for all controls. It compares consecutive snapshots to identify when control status changes (regressions or improvements). Drift detection provides early warning when compliance posture degrades.

## Data Management

**Can I import existing data?**
Yes, OpsDeck supports bulk import via CSV for:
- Users
- Assets
- Suppliers and contacts
- Peripherals

See [Data Import Guide](data_import.md) for CSV formats and procedures.

**Can I export data?**
API provides programmatic access to all data. Additionally:
- Compliance matrices can be exported for auditors
- Asset lists can be exported to CSV
- UAR findings can be exported for analysis

**How long is data retained?**
By default, data is retained indefinitely. Soft deletes are used for most entities, preserving history while hiding from normal views. Implement data retention policies based on your organization's requirements.

**Can I delete data permanently?**
Administrators can permanently delete soft-deleted records via database operations. This is not exposed in the UI to prevent accidental data loss.

**Does OpsDeck support attachments?**
Yes, attachments can be uploaded and linked to various entities (assets, incidents, policies, etc.). Attachments are stored on the filesystem by default. S3-compatible storage can be configured for cloud deployments.

## Integration

**Does OpsDeck have an API?**
Yes, comprehensive REST API provides access to all core entities. API documentation is available at `/swagger-ui` in your OpsDeck instance.

**Can OpsDeck integrate with Active Directory?**
LDAP/Active Directory integration is planned for the Enterprise plugin. Currently, users must be created in OpsDeck or via OAuth (Google).

**Does OpsDeck support webhooks?**
Outbound webhooks are supported for notifications (Slack, Discord, custom endpoints). Inbound webhooks for triggering actions are not currently supported.

**Can OpsDeck integrate with ticketing systems?**
Not directly, but the API can be used to create integrations. For example:
- Create Jira issues from OpsDeck incidents via API
- Sync asset data to external CMDB
- Push compliance status to dashboards

**Does OpsDeck support SCIM provisioning?**
Not currently. SCIM support is planned for future releases to enable automated user provisioning from identity providers.

## Support

**Where can I get help?**
- Documentation: Comprehensive guides in `/documentation` directory
- GitHub Issues: Report bugs and request features
- GitHub Discussions: Ask questions and share configurations
- Commercial Support: Available for enterprise deployments

**How do I report a bug?**
Open an issue on GitHub with:
- OpsDeck version
- Deployment method (Docker, manual, etc.)
- Steps to reproduce
- Expected vs. actual behavior
- Relevant log excerpts

**How do I request a feature?**
Open a feature request issue on GitHub with:
- Use case description
- Expected functionality
- Priority and impact on your operations

**Is there a community?**
GitHub Discussions serves as the primary community forum. Active users share configurations, deployment tips, and integration examples.

**What if I need priority support?**
Commercial support packages are available for organizations requiring:
- Guaranteed response times
- Implementation assistance
- Custom feature development
- Training and onboarding

## Troubleshooting

**Application won't start**
Check:
- Database connectivity (verify DATABASE_URL)
- Port availability (default 5000)
- File permissions on data directory
- Application logs for specific error

**Database migration fails**
Common causes:
- Database schema out of sync
- Concurrent migration attempts
- Database permissions insufficient

Solution: Review migration logs, ensure database user has DDL permissions, retry migration.

**Authentication errors**
Verify:
- SECRET_KEY is set and consistent across restarts
- Session cookie settings appropriate for environment
- If OAuth: client ID and secret are correct
- If MFA: time synchronization (TOTP requires accurate clock)

**Performance issues**
Investigate:
- Database query performance (enable SQLALCHEMY_ECHO for query logging)
- Resource utilization (CPU, memory, disk I/O)
- Number of application workers (increase if CPU underutilized)
- Database connection pool size

**Search not working**
Verify:
- Database indexes exist (run migrations if upgraded)
- Search service initialized (check application logs)
- Sufficient permissions to view searched entities
