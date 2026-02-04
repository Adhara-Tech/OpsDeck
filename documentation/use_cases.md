# OpsDeck Use Cases

This document describes scenarios where OpsDeck provides value and organizations that benefit from adopting it.

## Target Organizations

### Industry Segments

**Financial Services**
Banks, fintech companies, payment processors, and investment firms that need:
- Comprehensive audit trails for regulatory compliance
- Automated user access reviews for SOX requirements
- Risk management aligned with operational activities
- Asset tracking for compliance reporting

**Healthcare & Life Sciences**
Healthcare providers, medical device companies, and health IT vendors requiring:
- HIPAA compliance documentation and evidence collection
- Service dependency mapping for critical patient systems
- Incident tracking for breach notification requirements
- Vendor risk management for business associates

**SaaS & Technology Companies**
Software companies pursuing SOC 2 or ISO 27001 certification needing:
- Continuous compliance monitoring between audits
- Evidence repository for control attestation
- Change management workflows
- Automated drift detection to prevent regressions

**Professional Services**
Consulting firms, managed service providers, and agencies managing:
- Multi-client asset inventory
- Security incidents across customer environments
- Training and certification tracking
- Policy acknowledgment workflows

### Organization Size

**Mid-Market IT Teams (50-500 employees)**
OpsDeck is purpose-built for this segment:
- Need mature governance without enterprise complexity
- Limited IT security staff (1-5 people)
- Budget-conscious but compliance-driven
- Require audit readiness without full-time compliance team

**Growing Startups**
Companies scaling toward enterprise customers:
- First SOC 2 or ISO 27001 certification
- Establishing formal IT operations processes
- Building evidence base before audit engagement
- Creating documentation for sales security reviews

**Regulated Environments**
Any organization subject to:
- SOC 2 Type II requirements
- ISO 27001 / ISO 27002 compliance
- PCI DSS (merchant level 3-4)
- NIST Cybersecurity Framework
- State privacy regulations (CCPA, GDPR data processor obligations)

## Common Use Cases

### 1. Audit Preparation & Defense

**Scenario**
Company needs to prepare for annual SOC 2 Type II audit with 3-month preparation window.

**OpsDeck Solution**
- Import existing compliance framework (SOC 2 Type II controls)
- Link existing documentation, policies, and assets to relevant controls
- Use gap analysis to identify controls lacking evidence
- Collect additional evidence through security activity logs
- Lock audit snapshot to create immutable record for auditors
- Export compliance matrix for auditor review

**Outcome**
Audit completed in 4 weeks instead of 8-12 weeks with clear evidence presentation.

### 2. Continuous Compliance Monitoring

**Scenario**
Company maintains SOC 2 certification and needs to demonstrate continuous compliance between annual audits.

**OpsDeck Solution**
- Schedule automated UAR comparisons (weekly HRIS vs. Google Workspace)
- Enable compliance drift detection to alert on control status changes
- Log all security activities (vulnerability scans, access reviews, training)
- Link activities to relevant controls automatically
- Generate quarterly compliance reports for leadership

**Outcome**
Real-time visibility into compliance posture, early detection of issues before they become audit findings.

### 3. Access Governance & SOX Compliance

**Scenario**
Public company needs quarterly user access reviews to demonstrate SOX compliance for financial systems.

**OpsDeck Solution**
- Configure UAR comparison: ERP users vs. HR system employees
- Schedule quarterly execution with notifications to IT manager
- Findings automatically created for orphaned accounts, mismatches
- Bulk resolution workflow for false positives and remediation
- Complete audit trail of reviews and decisions
- Export reports for SOX auditors

**Outcome**
Quarterly UAR completed in 2 days instead of 2 weeks with comprehensive documentation.

### 4. Vendor Risk Management

**Scenario**
Company works with 50+ vendors and needs to track compliance status, contracts, and security posture.

**OpsDeck Solution**
- Maintain supplier directory with compliance status
- Track contract renewal dates with automated notifications
- Link vendor security assessments to supplier records
- Associate vendors with business services they support
- Track security incidents related to vendor systems
- Run vendor risk reports for quarterly review

**Outcome**
Centralized vendor governance with clear visibility into third-party risk.

### 5. IT Asset Lifecycle & Compliance

**Scenario**
Company needs to track 500+ assets from procurement through disposal with audit trail.

**OpsDeck Solution**
- Record purchases with warranty and cost details
- Track asset assignments to users with history
- Log maintenance activities and costs
- Link assets to business services they support
- Link assets to compliance controls (e.g., encryption, patching)
- Manage disposal process with documentation
- Generate asset reports for financial and compliance audits

**Outcome**
Complete asset traceability supporting financial reconciliation and security compliance.

### 6. Service Dependency & Business Impact

**Scenario**
Company experiences outages but lacks clear understanding of business service dependencies.

**OpsDeck Solution**
- Define business services (Customer Portal, Payment API, etc.)
- Map technical dependencies (servers, databases, SaaS tools)
- Identify single points of failure in dependency graph
- Link services to compliance controls and policies
- Track incidents by affected service
- Generate business impact reports for stakeholders

**Outcome**
Clear understanding of service architecture enabling better incident response and capacity planning.

### 7. Security Incident Management

**Scenario**
Company needs structured incident response process with documentation for compliance.

**OpsDeck Solution**
- Log incidents with severity, affected systems, and timeline
- Track investigation progress and findings
- Link affected assets, users, and services
- Document root cause and remediation steps
- Generate post-incident review reports
- Link incidents to risk register for follow-up
- Maintain complete incident history for trend analysis

**Outcome**
Structured incident response with comprehensive documentation for audits and process improvement.

### 8. Policy & Training Compliance

**Scenario**
Company needs to ensure 200+ employees acknowledge security policies annually.

**OpsDeck Solution**
- Upload security policies with effective dates
- Assign policies to all employees or specific groups
- Users acknowledge policies from dashboard
- Track acknowledgment status and send reminders
- Generate compliance reports showing acknowledgment rates
- Link policies to compliance controls for audit evidence

**Outcome**
100% policy acknowledgment within 2 weeks with clear audit trail.

### 9. Risk-Based Compliance

**Scenario**
Company wants to prioritize compliance efforts based on actual risk to business operations.

**OpsDeck Solution**
- Conduct risk assessments for identified threats
- Link risks to affected assets and business services
- Define mitigating security activities and controls
- Calculate residual risk after controls applied
- Prioritize compliance controls based on risk severity
- Track risk mitigation progress over time

**Outcome**
Risk-informed compliance program focusing resources on highest-impact areas.

### 10. Audit Evidence Collection

**Scenario**
Company preparing for first ISO 27001 certification needs to collect evidence for 100+ controls.

**OpsDeck Solution**
- Import ISO 27001 framework with all controls
- Link existing assets, policies, and activities to controls
- Identify gaps where evidence is missing
- Conduct security activities (reviews, tests) and log results
- Link activity logs to applicable controls
- Export comprehensive evidence package for auditors

**Outcome**
Systematic evidence collection reducing preparation time from 6 months to 3 months.

## When NOT to Use OpsDeck

OpsDeck may not be the right fit if:

**Enterprise Scale**
- 5,000+ employees requiring complex workflow automation
- Multi-tenant requirements with complete data isolation
- Highly customized approval chains and ITSM processes
- Consider: ServiceNow, BMC Remedy

**ITIL-Heavy Organizations**
- Mature ITIL v4 implementation with complex change management
- Service desk with SLA tracking and escalation rules
- Configuration management database (CMDB) with deep integration
- Consider: Jira Service Management, Freshservice

**Simple Asset Tracking**
- Basic inventory needs without compliance requirements
- No governance or audit requirements
- Pure hardware lifecycle management
- Consider: Snipe-IT, Ralph

**Pure GRC Focus**
- No IT operations management needed
- Exclusively focused on risk and compliance workflows
- Multiple frameworks with complex control mappings
- Consider: LogicGate, Vanta, Drata

## Migration Scenarios

### From Spreadsheets

**Common Pattern**
Organization tracking assets, vendors, and compliance in Excel/Google Sheets.

**Migration Path**
1. Export existing spreadsheets to CSV
2. Use OpsDeck bulk import to load data
3. Establish relationships (assets to users, suppliers to contracts)
4. Begin using OpsDeck for ongoing operations
5. Maintain spreadsheets as backup for 1-2 quarters

**Timeline**: 1-2 weeks for data migration and validation

### From Point Solutions

**Common Pattern**
Organization using separate tools: asset tracker, compliance tool, vendor database.

**Migration Path**
1. Identify primary data source for each entity type
2. Export data from existing tools to CSV
3. Import into OpsDeck using staging approach
4. Validate data completeness and relationships
5. Run parallel systems for 1 month during transition
6. Decommission old tools after validation

**Timeline**: 1-2 months for full migration with validation

### From Enterprise Platforms

**Common Pattern**
Organization downsizing from ServiceNow or similar due to cost or complexity.

**Migration Path**
1. Identify core OpsDeck features replacing enterprise tool
2. Extract data from enterprise platform via API or export
3. Transform data to OpsDeck import format
4. Import in phases (users, assets, compliance, etc.)
5. Establish new workflows in OpsDeck
6. Train team on OpsDeck interfaces
7. Maintain enterprise platform read-only for historical reference

**Timeline**: 2-3 months for transition with training

## Getting Started

The recommended approach for new deployments:

**Week 1: Foundation**
- Deploy OpsDeck instance
- Configure organizational structure (locations, cost centers)
- Import users
- Import vendors and suppliers

**Week 2: Asset Management**
- Import existing asset inventory
- Assign assets to users
- Begin logging maintenance activities

**Week 3: Compliance Framework**
- Import relevant framework (SOC 2, ISO 27001, etc.)
- Link existing policies to controls
- Begin evidence collection

**Week 4: Ongoing Operations**
- Enable notifications
- Schedule UAR comparisons
- Enable drift detection
- Train team on daily workflows

**Month 2+**
- Expand to additional modules (services, risk, training)
- Refine workflows based on team feedback
- Build reporting cadence
