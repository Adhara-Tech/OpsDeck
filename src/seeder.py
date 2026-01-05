from datetime import date, timedelta
from faker import Faker
from .models import (
    db, Supplier, User, Location, PaymentMethod, Tag, Budget, Purchase,
    Asset, Peripheral, Subscription, Risk, SecurityIncident,
    MaintenanceLog, DisposalRecord,
    BCDRPlan, BCDRTestLog, Course, CourseAssignment, Group, Policy, PolicyVersion, Opportunity,
    Documentation, Link, Software, License, Framework, FrameworkControl, ComplianceLink,
    BusinessService, ComplianceAudit, Contact, RiskAssessment
)
from . import create_app

fake = Faker()

def seed_data(app=None):
    """Seeds the database with a comprehensive set of demo data."""
    if app is None:
        app = create_app()
    with app.app_context():
        if Supplier.query.first():
            print("Database already contains data. Aborting seed.")
            return

        print("Seeding database with extensive demo data...")

        # 1. Create Core Entities
        print("Creating core entities...")
        suppliers = [
            Supplier(name='Adobe', email='sales@adobe.com', phone='800-833-6687', compliance_status='Compliant', gdpr_dpa_signed=date(2023, 5, 15)),
            Supplier(name='Microsoft', email='support@microsoft.com', phone='800-642-7676', compliance_status='Compliant', gdpr_dpa_signed=date(2023, 6, 1)),
            Supplier(name='Dell Technologies', email='sales@dell.com', phone='877-275-3355', compliance_status='Pending'),
            Supplier(name='Slack (Salesforce)', email='feedback@slack.com', phone='415-579-9122', compliance_status='Compliant', gdpr_dpa_signed=date(2024, 1, 10)),
            Supplier(name='Atlassian', email='sales@atlassian.com', phone='800-804-5281', compliance_status='Non-Compliant'),
            Supplier(name='Zoom', email='info@zoom.us', phone='888-799-9666'),
            Supplier(name='Apple', email='business@apple.com', phone='800-854-3680'),
            Supplier(name='Logitech', email='support@logi.com', phone='646-454-3200'),
            Supplier(name='Amazon Web Subscriptions', email='aws-sales@amazon.com', compliance_status='Compliant'),
            Supplier(name='Namecheap', email='support@namecheap.com'),
            Supplier(name='Figma', email='sales@figma.com'),
            Supplier(name='Herman Miller', email='info@hermanmiller.com'),
            Supplier(name='Okta', email='info@okta.com'),
            Supplier(name='Palo Alto Networks', email='sales@paloaltonetworks.com')
        ]
        db.session.add_all(suppliers)
        db.session.commit()
        
        # Add Contacts
        print("Creating contacts...")
        contacts = [
            Contact(name='John Adobe', email='john@adobe.com', phone='555-0101', role='Account Manager', supplier=suppliers[0]),
            Contact(name='Jane Microsoft', email='jane@microsoft.com', phone='555-0102', role='Sales Rep', supplier=suppliers[1]),
            Contact(name='Bob Dell', email='bob@dell.com', phone='555-0103', role='Support Lead', supplier=suppliers[2]),
            Contact(name='Alice Slack', email='alice@slack.com', phone='555-0104', role='CSM', supplier=suppliers[3])
        ]
        db.session.add_all(contacts)
        db.session.commit()

        locations = [
            Location(name='Headquarters - NYC'), 
            Location(name='London Office'), 
            Location(name='San Francisco Hub'), 
            Location(name='Tokyo Office'),
            Location(name='Sydney Office'),
            Location(name='Remote (Home Office)')
        ]
        payment_methods = [
            PaymentMethod(name='Corp AMEX - 1005', method_type='Credit Card', details='Ends in 1005'),
            PaymentMethod(name='IT Dept Visa - 4554', method_type='Credit Card', details='Ends in 4554'),
            PaymentMethod(name='Bank Transfer (ACH)', method_type='Bank Transfer')
        ]
        tags = [Tag(name='SaaS'), Tag(name='Hardware'), Tag(name='Marketing'), Tag(name='Development'), Tag(name='Office Supply'), Tag(name='Cloud Infrastructure'), Tag(name='Design'), Tag(name='Security')]
        
        db.session.add_all(locations)
        db.session.add_all(payment_methods)
        db.session.add_all(tags)
        db.session.commit()

        # 2. Create People, Groups
        print("Creating people and groups...")
        users = [
            # Executive / Leadership
            User(name='Alice Johnson', email='alice.j@example.com', department='Engineering', job_title='VP of Engineering'),
            User(name='Bob Williams', email='bob.w@example.com', department='Sales', job_title='VP of Sales'),
            
            # Management
            User(name='Charlie Brown', email='charlie.b@example.com', department='Engineering', job_title='Engineering Manager'),
            User(name='George Costanza', email='george.c@example.com', department='Sales', job_title='Sales Manager'),
            
            # Individual Contributors - Engineering
            User(name='Fiona Glenanne', email='fiona.g@example.com', department='Engineering', job_title='Senior Backend Developer'),
            User(name='Diana Prince', email='diana.p@example.com', department='Design', job_title='Senior Product Designer'),
            User(name='Heidi Klum', email='heidi.k@example.com', department='Design', job_title='UX Researcher'),
            
            # Individual Contributors - Sales
            User(name='Ethan Hunt', email='ethan.h@example.com', department='Sales', job_title='Account Executive'),
            
            # New Hires (for Onboarding/Buddy scenarios)
            User(name='Ian Malcolm', email='ian.m@example.com', department='Engineering', job_title='Junior DevOps Engineer'),
            User(name='Julia Roberts', email='julia.r@example.com', department='Sales', job_title='Sales  Development Rep')
        ]
        db.session.add_all(users)
        db.session.commit()

        group_engineering = Group(name="Engineering", description="All members of the engineering team.")
        group_engineering.users.extend([users[0], users[2], users[5]])
        
        group_sales = Group(name="Sales", description="The global sales team.")
        group_sales.users.extend([users[4], users[6]])

        group_design = Group(name="Design", description="The product and brand design team.")
        group_design.users.extend([users[3], users[7]])
        
        db.session.add_all([group_engineering, group_sales, group_design])
        
        db.session.commit()

        # 3. Create Budgets and Purchases (without cost)
        print("Creating budgets and purchases...")
        budgets = [
            Budget(name='IT Hardware 2025', category='IT', amount=75000, currency='EUR', period='Yearly'),
            Budget(name='Software & SaaS 2025', category='Software', amount=150000, currency='EUR', period='Yearly'),
        ]
        db.session.add_all(budgets)

        purchase1 = Purchase(description='Annual Adobe Creative Cloud Subscription', purchase_date=date(2024, 11, 1), supplier=suppliers[0], payment_method=payment_methods[0], budget=budgets[1])
        purchase2 = Purchase(description='New Developer Laptops Q4', purchase_date=date(2024, 10, 15), supplier=suppliers[2], payment_method=payment_methods[1], budget=budgets[0])
        purchase3 = Purchase(description='Jira & Confluence Cloud Annual', purchase_date=date(2025, 1, 5), supplier=suppliers[4], payment_method=payment_methods[2], budget=budgets[1])
        purchase4 = Purchase(description='New Macbooks for Design Team', purchase_date=date(2025, 2, 20), supplier=suppliers[6], payment_method=payment_methods[0], budget=budgets[0])
        purchase5 = Purchase(description='Firewall Upgrade for NYC Office', purchase_date=date(2025, 4, 1), supplier=suppliers[13], budget=budgets[0])
        
        db.session.add_all([purchase1, purchase2, purchase3, purchase4, purchase5])
        db.session.commit()
        
        # 4. Create Assets and Peripherals (with cost)
        print("Creating assets and peripherals...")
        assets = [
            Asset(name='DEV-LT-001', brand='Dell', model='XPS 15', serial_number=fake.uuid4(), status='In Use', purchase=purchase2, user=users[0], location=locations[0], supplier=suppliers[2], cost=2500, currency='EUR', warranty_length=36, purchase_date=purchase2.purchase_date),
            Asset(name='DEV-LT-002', brand='Dell', model='XPS 15', serial_number=fake.uuid4(), status='In Use', purchase=purchase2, user=users[2], location=locations[0], supplier=suppliers[2], cost=2500, currency='EUR', warranty_length=36, purchase_date=purchase2.purchase_date),
            Asset(name='DSN-LT-001', brand='Apple', model='MacBook Pro 16"', serial_number=fake.uuid4(), status='In Use', purchase=purchase4, user=users[3], location=locations[1], supplier=suppliers[6], cost=3200, currency='EUR', warranty_length=24, purchase_date=purchase4.purchase_date),
            Asset(name='DSN-LT-002', brand='Apple', model='MacBook Pro 16"', serial_number=fake.uuid4(), status='In Use', purchase=purchase4, user=users[7], location=locations[1], supplier=suppliers[6], cost=3200, currency='EUR', warranty_length=24, purchase_date=purchase4.purchase_date),
            Asset(name='SALES-LT-001', brand='Microsoft', model='Surface Laptop 5', serial_number=fake.uuid4(), status='In Storage', location=locations[0], supplier=suppliers[1], cost=1800, currency='USD', warranty_length=24, purchase_date=date(2024, 5, 5)),
            Asset(name='EOL-LT-001', brand='Apple', model='MacBook Pro 13"', serial_number=fake.uuid4(), status='Awaiting Disposal', location=locations[0], cost=1500, currency='USD', purchase_date=date(2021, 5, 5)),
            Asset(name='FW-NYC-01', brand='Palo Alto', model='PA-440', serial_number=fake.uuid4(), status='In Use', purchase=purchase5, location=locations[0], supplier=suppliers[13], cost=4000, currency='USD', warranty_length=60, purchase_date=purchase5.purchase_date)
        ]
        db.session.add_all(assets)
        db.session.commit()

        peripherals = [
            Peripheral(name='Keyboard-001', type='Keyboard', brand='Logitech', cost=100, currency='EUR', serial_number=fake.uuid4(), asset=assets[0], user=users[0], supplier=suppliers[7]),
            Peripheral(name='Mouse-001', type='Mouse', brand='Logitech', cost=80, currency='EUR', serial_number=fake.uuid4(), asset=assets[0], user=users[0], supplier=suppliers[7]),
            Peripheral(name='Monitor-001', type='Monitor', brand='Dell', cost=450, currency='EUR', serial_number=fake.uuid4(), asset=assets[0], user=users[0], supplier=suppliers[2]),
            Peripheral(name='Keyboard-003', type='Keyboard', brand='Apple', cost=150, currency='EUR', asset=assets[2], user=users[3]),
            Peripheral(name='Mouse-003', type='Mouse', brand='Apple', cost=90, currency='EUR', asset=assets[2], user=users[3]),
        ]
        db.session.add_all(peripherals)
        db.session.commit()
        
        # 5. Create Subscriptions and Opportunities
        print("Creating subscriptions and opportunities...")
        subscriptions_data = [
            {'name': 'Adobe Creative Cloud', 'type': 'Software', 'renewal': date(2025, 11, 1), 'cost': 15000, 'supplier': suppliers[0]},
            {'name': 'Microsoft 365 E5', 'type': 'SaaS', 'renewal': date(2026, 1, 1), 'cost': 35000, 'supplier': suppliers[1]},
            {'name': 'Okta Identity Provider', 'type': 'Security', 'renewal': date(2026, 6, 1), 'cost': 12000, 'supplier': suppliers[12]},
        ]
        for data in subscriptions_data:
            subscription = Subscription(name=data['name'], subscription_type=data['type'], renewal_date=data['renewal'], cost=data['cost'], supplier=data['supplier'], renewal_period_type='yearly')
            db.session.add(subscription)
        
        opportunities = [
            Opportunity(name="Company-wide SSO solution", status="Evaluating", potential_value=20000, supplier=suppliers[12]),
            Opportunity(name="Next-gen firewall refresh", status="Negotiating", potential_value=50000, supplier=suppliers[13], estimated_close_date=date(2025, 12, 1))
        ]
        db.session.add_all(opportunities)
        db.session.commit()
        
        # 6. Create Policies and Courses
        print("Creating policies and courses...")
        policy = Policy(title="Acceptable Use Policy", category="IT Security", description="Defines the acceptable use of company IT resources.")
        policy_v1 = PolicyVersion(
            policy=policy,
            version_number="1.0",
            content="## 1. Introduction\nThis policy outlines the acceptable use of company equipment and network resources...",
            status="Active",
            effective_date=date(2024, 1, 1)
        )
        policy_v1.groups_to_acknowledge.append(group_engineering)
        db.session.add_all([policy, policy_v1])

        course = Course(title="Cybersecurity Awareness Training 2025", description="Annual training for all employees on security best practices.", link="http://example.com/training")
        db.session.add(course)
        db.session.commit()

        assignment = CourseAssignment(course_id=course.id, user_id=users[1].id, due_date=date.today() + timedelta(days=30))
        db.session.add(assignment)
        
        # 7. Create Compliance & Governance Entities
        print("Creating compliance and governance entities...")
        risks = [
            Risk(
                risk_description="Unauthorized access to cloud infrastructure", 
                extended_description="Attackers or unauthorized users could gain access to cloud resources (AWS, Azure, GCP) due to weak passwords, stolen credentials, or lack of multi-factor authentication. This could result in data breaches, service disruption, and significant financial/reputational damage.",
                status="Assessed", 
                inherent_likelihood=4, inherent_impact=5, 
                residual_likelihood=2, residual_impact=5,
                treatment_strategy="Mitigate",
                owner=users[0], # Alice
                next_review_date=date.today() + timedelta(days=90),
                mitigation_plan="Enforce MFA and rotate keys quarterly."
            ),
            Risk(
                risk_description="Data loss from database hardware failure", 
                extended_description="The primary database server could experience a hardware failure (disk crash, power supply failure, etc.) leading to loss of critical business data. Without proper backups, this could cause significant operational disruption and potential regulatory non-compliance.",
                status="In Treatment", 
                inherent_likelihood=2, inherent_impact=4, 
                residual_likelihood=1, residual_impact=4,
                treatment_strategy="Mitigate",
                owner=users[5], # Fiona
                next_review_date=date.today() + timedelta(days=30),
                mitigation_plan="Implement daily backups to a secondary location."
            ),
            Risk(
                risk_description="Malware infection on endpoints", 
                extended_description="End-user devices (laptops, workstations) could become infected with malware through phishing emails, malicious downloads, or drive-by downloads. Malware could lead to data theft, ransomware attacks, or lateral movement within the network.",
                status="Identified", 
                inherent_likelihood=5, inherent_impact=3, 
                residual_likelihood=3, residual_impact=3,
                treatment_strategy="Mitigate",
                owner=users[0], # Alice
                next_review_date=date.today() + timedelta(days=60),
                mitigation_plan="Deploy EDR solution."
            ),
            Risk(
                risk_description="Third-party supplier security failure", 
                extended_description="Critical suppliers (SaaS vendors, cloud providers) may fail to meet security obligations, experience data breaches, or become unavailable. This creates supply chain risk that could impact our operations and expose our data.",
                status="Assessed", 
                inherent_likelihood=3, inherent_impact=5, 
                residual_likelihood=2, residual_impact=4,
                treatment_strategy="Transfer",
                owner=users[6], # George (Sales/Vendor Mgmt)
                next_review_date=date.today() + timedelta(days=180),
                mitigation_plan="Include strict SLAs and penalties in contracts."
            ),
            Risk(
                risk_description="Data leakage via email", 
                extended_description="Employees could accidentally or intentionally send sensitive data (customer PII, financial data, trade secrets) via email to unauthorized recipients. This could violate GDPR, contractual obligations, and cause reputational damage.",
                status="Identified", 
                inherent_likelihood=4, inherent_impact=4, 
                residual_likelihood=3, residual_impact=4,
                treatment_strategy="Mitigate",
                owner=users[1], # Bob
                next_review_date=date.today() + timedelta(days=45),
                mitigation_plan="Implement DLP rules for email."
            ),
            Risk(
                risk_description="Inadequate access control reviews", 
                extended_description="User access rights may accumulate over time (privilege creep) or remain active for terminated employees. Without regular reviews, this creates excessive permissions and potential for unauthorized access to sensitive systems and data.",
                status="In Treatment", 
                inherent_likelihood=3, inherent_impact=3, 
                residual_likelihood=1, residual_impact=3,
                treatment_strategy="Mitigate",
                owner=users[0], # Alice
                next_review_date=date.today() + timedelta(days=90),
                mitigation_plan="Quarterly access reviews."
            ),
            # New Risks for Dashboard Variety
            Risk(
                risk_description="Legacy system vulnerabilities", 
                extended_description="Legacy systems that are no longer supported may contain known vulnerabilities that cannot be patched. These systems are attractive targets for attackers and may be difficult to monitor.",
                status="Accepted", 
                inherent_likelihood=2, inherent_impact=3, 
                residual_likelihood=2, residual_impact=3,
                treatment_strategy="Accept",
                owner=users[0], # Alice
                next_review_date=date.today() + timedelta(days=180),
                mitigation_plan="System is air-gapped; risk accepted until decommissioning in 2026."
            ),
            Risk(
                risk_description="Insider threat from employees", 
                extended_description="Disgruntled, negligent, or compromised employees could misuse their authorized access to steal data, sabotage systems, or facilitate external attacks. Insider threats are difficult to detect and can cause significant damage.",
                status="Assessed", 
                inherent_likelihood=2, inherent_impact=5, 
                residual_likelihood=1, residual_impact=5,
                treatment_strategy="Mitigate",
                owner=users[2], # Charlie
                next_review_date=date.today() + timedelta(days=120),
                mitigation_plan="Background checks and least privilege access."
            ),
            Risk(
                risk_description="DDoS attack on public website", 
                extended_description="Our public-facing website and APIs could be targeted by distributed denial-of-service attacks, making services unavailable to legitimate users. This impacts revenue, customer trust, and operational efficiency.",
                status="Mitigated", 
                inherent_likelihood=4, inherent_impact=4, 
                residual_likelihood=1, residual_impact=2,
                treatment_strategy="Transfer",
                owner=users[5], # Fiona
                next_review_date=date.today() + timedelta(days=365),
                mitigation_plan="Use Cloudflare DDoS protection."
            ),
            Risk(
                risk_description="GDPR regulatory non-compliance", 
                extended_description="Failure to comply with GDPR requirements for processing EU citizen data could result in significant fines (up to 4% of global revenue), legal action, and reputational damage. This includes consent management, data subject rights, and breach notification.",
                status="Assessed", 
                inherent_likelihood=3, inherent_impact=5, 
                residual_likelihood=2, residual_impact=5,
                treatment_strategy="Avoid",
                owner=users[1], # Bob
                next_review_date=date.today() + timedelta(days=60),
                mitigation_plan="Do not process data of EU citizens until compliant."
            ),
             Risk(
                risk_description="API key exposure in code repositories", 
                extended_description="API keys, database credentials, or other secrets may be accidentally committed to source code repositories (public or private). Exposed credentials can be harvested by attackers and used to access systems, exfiltrate data, or incur costs.",
                status="Assessed", 
                inherent_likelihood=5, inherent_impact=5, 
                residual_likelihood=5, residual_impact=5,
                treatment_strategy="Mitigate",
                owner=users[0], # Alice
                next_review_date=date.today() + timedelta(days=1),
                mitigation_plan="Immediate rotation and secrets management implementation."
            )
        ]
        db.session.add_all(risks)

        incident = SecurityIncident(title="Phishing Email Reported by Bob Williams", description="User Bob Williams reported a suspicious email with a link to a fake login page.", severity="SEV-2", impact="Minor", owner=users[0], reported_by=users[1])
        incident.affected_users.append(users[1])
        db.session.add(incident)
        
        bcdr_plan = BCDRPlan(name="Primary Database Failure Plan", description="Steps to restore the main application database from backups.")
        bcdr_plan.subscriptions.append(Subscription.query.first())
        db.session.add(bcdr_plan)
        db.session.commit()
        
        bcdr_test = BCDRTestLog(plan_id=bcdr_plan.id, status="Passed", notes="Successfully restored backup to a staging environment in under 30 minutes.")
        db.session.add(bcdr_test)
        
        # 8. Create Lifecycle Events
        print("Creating lifecycle events (maintenance, disposal)...")
        maintenance_log = MaintenanceLog(event_type="Repair", description="Replaced faulty RAM module.", status="Completed", asset=assets[0], assigned_to=users[0])
        db.session.add(maintenance_log)
        
        erasure_log = MaintenanceLog(event_type="Data Erasure", description="NIST 800-88 3-pass wipe performed.", status="Completed", asset=assets[5], assigned_to=users[0])
        db.session.add(erasure_log)

        disposal = DisposalRecord(disposal_method="Recycled", disposal_partner="eWaste Inc.", asset=assets[5])
        db.session.add(disposal)

        db.session.commit()

        # 9. Create Documentation, Links, Software, Licenses
        print("Creating documentation, links, software, and licenses...")
        
        docs = [
            Documentation(name="Employee Handbook 2025", description="General company policies and guidelines.", external_link="https://docs.example.com/handbook", owner_id=users[1].id, owner_type='User'),
            Documentation(name="IT Security Policy", description="Comprehensive security policy for all staff.", external_link="https://docs.example.com/security", owner_id=users[0].id, owner_type='User'),
            Documentation(name="Onboarding Guide", description="Guide for new hires.", external_link="https://docs.example.com/onboarding", owner_id=users[7].id, owner_type='User')
        ]
        db.session.add_all(docs)

        links = [
            Link(name="Jira", url="https://jira.example.com", description="Issue tracking", owner_id=group_engineering.id, owner_type='Group'),
            Link(name="Confluence", url="https://confluence.example.com", description="Knowledge base", owner_id=group_engineering.id, owner_type='Group'),
            Link(name="Figma", url="https://figma.com/files/team/example", description="Design files", owner_id=group_design.id, owner_type='Group'),
            Link(name="Salesforce", url="https://salesforce.com", description="CRM", owner_id=group_sales.id, owner_type='Group')
        ]
        db.session.add_all(links)

        software_list = [
            Software(name="Visual Studio Code 1.85", description="Code editor by Microsoft", category="Development"),
            Software(name="Slack 4.36", description="Communication tool by Slack Technologies", category="Communication"),
            Software(name="Zoom 5.17", description="Video conferencing by Zoom Video Communications", category="Communication"),
            Software(name="Adobe Photoshop 2024", description="Image editing by Adobe", category="Design")
        ]
        db.session.add_all(software_list)
        db.session.commit() # Commit to get IDs

        licenses = [
            License(name="VS Code Enterprise", license_key="FREE-LICENSE", expiry_date=date(2099, 12, 31), software_id=software_list[0].id, user_id=users[0].id),
            License(name="Slack Business Plus", license_key="SLACK-KEY-123", expiry_date=date(2025, 1, 10), software_id=software_list[1].id, user_id=users[1].id),
            License(name="Adobe Creative Cloud All Apps", license_key="ADOBE-KEY-456", expiry_date=date(2025, 11, 1), software_id=software_list[3].id, user_id=users[3].id)
        ]
        db.session.add_all(licenses)
        db.session.commit()

        # 10. Create Fake Framework & Compliance Links
        print("Creating fake framework and compliance links...")
        
        fake_framework = Framework(name="Galactic Security Standard (GSS)", description="Standard for security across the galaxy.", is_active=True, is_custom=True)
        db.session.add(fake_framework)
        db.session.commit()

        fake_controls = [
            FrameworkControl(framework_id=fake_framework.id, control_id="GSS.1.1", name="Planetary Defense", description="Ensure planetary shields are active."),
            FrameworkControl(framework_id=fake_framework.id, control_id="GSS.1.2", name="Droid Security", description="Prevent unauthorized droid hacking."),
            FrameworkControl(framework_id=fake_framework.id, control_id="GSS.2.1", name="Hologram Encryption", description="Encrypt all holographic communications."),
            FrameworkControl(framework_id=fake_framework.id, control_id="GSS.3.1", name="Warp Drive Safety", description="Regular maintenance of warp cores.")
        ]
        db.session.add_all(fake_controls)
        db.session.commit()

        # Link controls to assets/docs
        compliance_links = [
            ComplianceLink(framework_control_id=fake_controls[0].id, linkable_id=assets[6].id, linkable_type='Asset', description="Firewall protects the planetary network."),
            ComplianceLink(framework_control_id=fake_controls[1].id, linkable_id=docs[1].id, linkable_type='Documentation', description="Policy outlines droid security protocols."),
            ComplianceLink(framework_control_id=fake_controls[2].id, linkable_id=software_list[1].id, linkable_type='Software', description="Slack used for encrypted comms (close enough)."),
            ComplianceLink(framework_control_id=fake_controls[3].id, linkable_id=maintenance_log.id, linkable_type='MaintenanceLog', description="Regular maintenance performed on core systems.")
        ]
        db.session.add_all(compliance_links)
        
        # 11. User Hierarchy (Managers)
        # 11. User Hierarchy (Managers & Buddies)
        print("Assigning managers and buddies...")
        
        # Mapping for clarity:
        # Alice (VP Eng) -> manages Charlie (Eng Mgr)
        # Charlie (Eng Mgr) -> manages Fiona, Ian, Diana, Heidi (Design sits under Eng for this demo)
        # Bob (VP Sales) -> manages George (Sales Mgr)
        # George (Sales Mgr) -> manages Ethan, Julia

        # Set Managers
        users[2].manager = users[0]  # Charlie -> Alice
        users[4].manager = users[0]  # Fiona -> Charlie (Wait, Index 4 is Fiona in new list? Let's check indices)
        # Re-fetching to be safe or using variable names would be better, but utilizing list indices for now based on above order:
        # 0: Alice, 1: Bob, 2: Charlie, 3: George, 4: Fiona, 5: Diana, 6: Heidi, 7: Ethan, 8: Ian, 9: Julia

        # Engineering Tree
        users[2].manager = users[0] # Charlie manages under Alice
        users[4].manager = users[2] # Fiona manages under Charlie
        users[5].manager = users[2] # Diana manages under Charlie
        users[6].manager = users[2] # Heidi manages under Charlie
        users[8].manager = users[2] # Ian manages under Charlie

        # Sales Tree
        users[3].manager = users[1] # George manages under Bob
        users[7].manager = users[3] # Ethan manages under George
        users[9].manager = users[3] # Julia manages under George

        # Buddies (Mentors)
        # Fiona mentors Ian (New Hire Eng)
        users[8].buddy = users[4]
        # Ethan mentors Julia (New Hire Sales)
        users[9].buddy = users[7]

        db.session.commit()

        # 12. Business Services
        # 12. Business Services
        print("Creating business services...")
        services = [
            BusinessService(name="E-Commerce Platform", description="Main customer facing store.", owner=users[2], criticality="Tier 1 - Critical", status="Operational"),
            BusinessService(name="Inventory System", description="Warehouse management and stock control.", owner=users[4], criticality="Tier 1 - Critical", status="Operational"),
            BusinessService(name="Payment Gateway", description="External payment processing integration.", owner=users[2], criticality="Tier 1 - Critical", status="Operational"),
            BusinessService(name="Internal HR Portal", description="Employee self-service and records.", owner=users[0], criticality="Tier 3 - Standard", status="Operational"),
            BusinessService(name="Customer Support Portal", description="Ticket management for end-users.", owner=users[6], criticality="Tier 2 - High", status="Operational"),
            BusinessService(name="Data Warehouse", description="Centralized analytics and reporting data.", owner=users[4], criticality="Tier 2 - High", status="Operational"),
            BusinessService(name="Identity Provider (IdP)", description="Centralized authentication (SSO).", owner=users[0], criticality="Tier 1 - Critical", status="Operational"),
            BusinessService(name="Logistics API", description="Integration with shipping providers.", owner=users[4], criticality="Tier 2 - High", status="Pipeline")
        ]
        db.session.add_all(services)
        db.session.commit()

        # Dependencies
        # Architecture:
        # E-Commerce -> Depends on: Inventory, Payment Gateway, Identity Provider
        services[0].upstream_dependencies.append(services[1]) # Inventory
        services[0].upstream_dependencies.append(services[2]) # Payment
        services[0].upstream_dependencies.append(services[6]) # IdP

        # Customer Support -> Depends on: Identity Provider, Inventory (to check order status)
        services[4].upstream_dependencies.append(services[6]) # IdP
        services[4].upstream_dependencies.append(services[1]) # Inventory

        # Data Warehouse -> Depends on: E-Commerce (source), Inventory (source)
        services[5].upstream_dependencies.append(services[0])
        services[5].upstream_dependencies.append(services[1])

        # Logistics API -> Depends on: Inventory
        services[7].upstream_dependencies.append(services[1])

        db.session.commit()

        # 13. Compliance Audit (Defense Room)
        print("Creating compliance audit...")
        # Create a snapshot audit for GSS
        audit = ComplianceAudit.create_snapshot(
            framework_id=fake_framework.id, 
            name="GSS Audit 2025", 
            auditor_contact_id=None, 
            internal_lead_id=users[2].id, # Charlie (Eng Mgr)
            copy_links=True # Populate evidence from live links
        )
        audit.status = "Prep"
        db.session.commit()

        # 14. Historical Risk Assessments with Items
        print("Creating historical risk assessments with items...")
        from .models import RiskAssessmentItem, RiskAssessmentEvidence
        from datetime import datetime as dt
        
        # Q3 2024 Assessment - Higher initial residual scores
        q3_assessment = RiskAssessment(
            name="Q3 2024 Security Assessment",
            status="Locked",
            created_at=dt(2024, 9, 30),
            locked_at=dt(2024, 10, 1)
        )
        db.session.add(q3_assessment)
        db.session.flush()  # Get ID
        
        # Create items for Q3 - snapshot of risks at that time (higher residual)
        q3_items_data = [
            # (risk_index, inherent_i, inherent_l, residual_i, residual_l, notes)
            (0, 5, 4, 5, 3, "Initial controls in place but MFA adoption only at 60%."),
            (1, 4, 2, 4, 2, "Backup system operational but recovery time untested."),
            (2, 3, 5, 3, 4, "EDR deployment in progress, 50% coverage."),
            (3, 5, 3, 4, 3, "Supplier assessments pending for 2 vendors."),
            (4, 4, 4, 4, 4, "DLP solution not yet deployed."),
            (5, 3, 3, 3, 2, "Manual access reviews ongoing.")
        ]
        
        for risk_idx, inh_i, inh_l, res_i, res_l, notes in q3_items_data:
            risk = risks[risk_idx]
            item = RiskAssessmentItem(
                assessment_id=q3_assessment.id,
                original_risk_id=risk.id,
                risk_description=risk.risk_description,
                threat_type_name=risk.threat_type.name if risk.threat_type else None,
                category_list=",".join([c.category for c in risk.categories]) if risk.categories else "",
                inherent_impact=inh_i,
                inherent_likelihood=inh_l,
                residual_impact=res_i,
                residual_likelihood=res_l,
                treatment_strategy=risk.treatment_strategy,
                mitigation_notes=notes
            )
            db.session.add(item)
        
        q3_assessment.calculate_total_risk()
        
        # Q4 2024 Assessment - Lower residual scores (improvement!)
        q4_assessment = RiskAssessment(
            name="Q4 2024 Security Assessment",
            status="Locked",
            created_at=dt(2024, 12, 31),
            locked_at=dt(2025, 1, 2)
        )
        db.session.add(q4_assessment)
        db.session.flush()
        
        # Create items for Q4 - shows improvement from controls
        q4_items_data = [
            # (risk_index, inherent_i, inherent_l, residual_i, residual_l, notes)
            (0, 5, 4, 5, 2, "MFA enforced company-wide. Key rotation automated."),
            (1, 4, 2, 4, 1, "Disaster recovery test successful. RTO < 30 min achieved."),
            (2, 3, 5, 3, 3, "EDR deployed to 95% of endpoints."),
            (3, 5, 3, 4, 2, "All critical vendors assessed. DPAs signed."),
            (4, 4, 4, 4, 3, "DLP rules deployed for email. Monitoring active."),
            (5, 3, 3, 3, 1, "Automated quarterly access reviews implemented."),
            (8, 4, 4, 2, 1, "Cloudflare fully operational. DDoS mitigated."),  # DDoS risk
        ]
        
        for risk_idx, inh_i, inh_l, res_i, res_l, notes in q4_items_data:
            risk = risks[risk_idx]
            item = RiskAssessmentItem(
                assessment_id=q4_assessment.id,
                original_risk_id=risk.id,
                risk_description=risk.risk_description,
                threat_type_name=risk.threat_type.name if risk.threat_type else None,
                category_list=",".join([c.category for c in risk.categories]) if risk.categories else "",
                inherent_impact=inh_i,
                inherent_likelihood=inh_l,
                residual_impact=res_i,
                residual_likelihood=res_l,
                treatment_strategy=risk.treatment_strategy,
                mitigation_notes=notes
            )
            db.session.add(item)
            db.session.flush()
            
            # Add evidence links to some items (policies, docs)
            if risk_idx == 0:  # MFA risk - link to security policy
                ev = RiskAssessmentEvidence(item_id=item.id, linkable_type='Policy', linkable_id=policy.id, notes='MFA mandated in policy')
                db.session.add(ev)
            if risk_idx == 1:  # Backup risk - link to BCDR plan
                ev = RiskAssessmentEvidence(item_id=item.id, linkable_type='BCDRPlan', linkable_id=bcdr_plan.id, notes='DR plan tested successfully')
                db.session.add(ev)
        
        q4_assessment.calculate_total_risk()
        db.session.commit()

        print("Database seeding complete!")