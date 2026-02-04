# Getting Started with OpsDeck

This guide helps new users understand how to configure and use OpsDeck effectively.

## Initial Setup

### 1. First Login

After deployment, log in with the admin credentials configured during installation:
- Default email: `admin@example.com`
- Default password: `admin123`

You'll be prompted to change the default password immediately.

### 2. User Management

**Create Users**
1. Navigate to User Management > Users
2. Click "Add User"
3. Provide name, email, and assign initial role
4. User receives email with temporary password
5. User must change password on first login

**Configure Roles**
- **Admin**: For IT leadership and security team
- **Manager**: For team leads who need operational access
- **User**: For general staff who need view access

### 3. Organizational Structure

**Locations**
Define physical locations where assets are deployed:
1. Navigate to Administration > Locations
2. Add locations (HQ Office, Data Center, Remote Office, etc.)
3. Locations are used for asset tracking and compliance scoping

**Cost Centers**
Set up departments or cost centers for budget tracking:
1. Navigate to Administration > Cost Centers
2. Add cost centers matching your organization
3. Used for asset assignment and budget allocation

## Core Workflows

### Asset Management

**Adding Assets**
1. Navigate to Assets > Asset List
2. Click "Add Asset"
3. Provide: name, model, serial number, cost, purchase date
4. Assign location and optionally assign to a user
5. Upload photos or documentation

**Asset Lifecycle**
- **In Stock**: Asset received but not yet deployed
- **In Use**: Asset assigned to user or deployed
- **In Repair**: Asset under maintenance
- **Awaiting Disposal**: Asset ready for retirement
- **Disposed**: Asset retired (archived record)

**Maintenance Tracking**
1. From asset detail page, click "Log Maintenance"
2. Record issue, resolution, cost, and time spent
3. Maintenance history visible on asset detail page

### Vendor Management

**Adding Suppliers**
1. Navigate to Vendors > Suppliers
2. Click "Add Supplier"
3. Provide company name, contact info, website
4. Set compliance status (Approved, Pending, Rejected)

**Supplier Contacts**
1. From supplier detail page, add contacts
2. Provide name, email, phone, and role
3. Contacts used for communication and contract management

**Contracts**
1. Link contracts to suppliers
2. Set contract start and end dates
3. Upload contract documents
4. Receive notifications before contract expiration

### Compliance Management

**Setting Up Frameworks**
1. Navigate to Compliance > Frameworks
2. Click "Add Framework"
3. Choose from templates (SOC 2, ISO 27001) or create custom
4. Framework includes predefined controls

**Linking Evidence**
1. Navigate to any resource (asset, policy, service, etc.)
2. Find "Compliance Links" section
3. Click "Link to Control"
4. Select framework and specific control
5. Add context/notes explaining how this provides evidence

**Running Audits**
1. Navigate to Compliance > Audits > Create Audit
2. Choose "Fresh Start" or "Renewal" (copies previous audit scope)
3. System creates snapshot of current compliance state
4. Review controls, identify gaps, collect additional evidence
5. Lock audit when complete to create immutable record

### User Access Review (UAR)

**Setting Up UAR Comparison**
1. Navigate to Compliance > User Access Reviews
2. Click "Create Comparison"
3. Define Dataset A (e.g., HRIS CSV export)
4. Define Dataset B (e.g., Google Workspace users)
5. Map fields for comparison (email, employee_id, etc.)
6. Set schedule (daily, weekly, monthly)

**Managing Findings**
1. Navigate to UAR execution detail page
2. Review findings by severity
3. Mark false positives if needed
4. Use bulk operations to assign, resolve, or create incidents
5. Add comments to document resolution

**Visual Diff Viewer**
For mismatch findings:
1. Click "View Details" on a mismatch finding
2. Side-by-side comparison shows field differences
3. Highlighted changes make discrepancies clear

### Service Catalog

**Defining Business Services**
1. Navigate to Services > Business Services
2. Click "Add Service"
3. Provide name, description, criticality
4. Services represent business capabilities (e.g., "Customer Portal", "Payment Processing")

**Mapping Dependencies**
1. From service detail page, click "Add Component"
2. Link assets (servers, databases)
3. Link software subscriptions
4. Link other services (dependencies)
5. Topology view shows complete dependency graph

**Compliance Context**
1. Link policies that govern the service
2. Link compliance controls the service must satisfy
3. Link security activities that protect the service
4. Provides unified view of service compliance posture

### Risk Management

**Creating Risk Assessments**
1. Navigate to Security > Risks
2. Click "Add Risk"
3. Define threat, impact, likelihood
4. Categorize by CIA triad (Confidentiality, Integrity, Availability)
5. Link affected assets and services

**Mitigation Planning**
1. From risk detail page, link mitigating security activities
2. Define residual risk after controls applied
3. Set review dates for periodic reassessment
4. Track status (Open, Mitigated, Accepted, Closed)

### Security Incidents

**Logging Incidents**
1. Navigate to Security > Incidents
2. Click "Report Incident"
3. Provide description, severity, affected systems
4. Assign to investigator

**Investigation**
1. Update incident with findings
2. Link affected assets, users, or services
3. Document root cause
4. Link related risks or compliance controls

**Resolution**
1. Document remediation steps
2. Update status to "Resolved"
3. Conduct post-incident review
4. Create follow-up risks or policy updates

## Advanced Features

### Universal Search

Access via search icon in navigation:
1. Enter query (searches names, descriptions, serial numbers, etc.)
2. Filter by entity type (assets, users, incidents, etc.)
3. Refine using faceted filters (date range, status, severity)
4. Save frequently-used searches for quick access

### Policy Management

**Creating Policies**
1. Navigate to Compliance > Policies
2. Click "Add Policy"
3. Upload policy document (PDF)
4. Set effective date and review schedule
5. Assign to users or groups for acknowledgment

**Acknowledgment Tracking**
1. Users see pending policies on their dashboard
2. Policy must be read and acknowledged
3. Tracking report shows compliance rate
4. Policies can be linked to compliance controls

### Training Tracking

**Assigning Training**
1. Navigate to People > Training
2. Click "Assign Training"
3. Select users and training module
4. Set due date
5. Users notified of assignment

**Completion Tracking**
1. Users mark training as complete
2. Upload certificates or evidence
3. Manager reviews and approves
4. Training records link to compliance controls

### API Access

**Generating API Token**
1. Navigate to User Management > Users
2. Click on your user profile
3. Scroll to "Developer Settings (API)"
4. Click "Generate New Token"
5. Copy token (shown only once)
6. Use token in Authorization header: `Bearer <token>`

**API Documentation**
Navigate to `/swagger-ui` to explore available endpoints and test requests.

## Best Practices

**Asset Management**
- Tag assets upon receipt before deployment
- Take photos and record serial numbers
- Link purchase records for warranty tracking
- Regular audits to verify physical location matches system

**Compliance**
- Link evidence continuously, not just during audits
- Use compliance links liberally (assets, policies, activities)
- Schedule UAR comparisons to run automatically
- Enable drift detection to catch regressions early

**Security**
- Rotate credentials in vault regularly
- Log all security activities with detailed notes
- Link incidents to affected assets and services
- Conduct regular risk assessments (quarterly minimum)

**Data Quality**
- Use consistent naming conventions
- Keep supplier and contact information current
- Archive old data rather than deleting
- Use bulk import for initial data loading

## Getting Help

**Documentation**
- README.md: Overview and installation
- documentation/: Detailed guides and references
- Swagger UI: Interactive API documentation

**Logging**
- Application logs provide detailed troubleshooting information
- Check logs when operations fail or behave unexpectedly
- Log location configured in deployment

**Community**
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share configurations
