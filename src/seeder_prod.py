# En src/seeder_prod.py

from src.extensions import db
from src.models import Framework, FrameworkControl
from src.models.security import ThreatType

# Lista de amenazas comunes (Category, Name, Description)
common_threats = [
    # Ciberataques / Adversarial
    ("Adversarial", "Malware / Ransomware", "Malicious software designed to disrupt, damage, or gain unauthorized access."),
    ("Adversarial", "Phishing / Social Engineering", "Psychological manipulation of people into performing actions or divulging confidential information."),
    ("Adversarial", "DDoS Attack", "Malicious attempt to disrupt the normal traffic of a targeted server, service or network."),
    ("Adversarial", "Insider Threat (Malicious)", "Employee or contractor who intentionally uses their authorized access to harm the organization."),
    ("Adversarial", "Credential Theft", "Compromise of passwords or access keys."),
    ("Adversarial", "SQL Injection / Web Exploit", "Exploitation of vulnerabilities in web applications."),
    
    # Accidental / Human Error
    ("Accidental", "Configuration Error", "Incorrect configuration of security systems or servers."),
    ("Accidental", "Accidental Data Disclosure", "Sending sensitive information to wrong recipients or unintended public publishing."),
    ("Accidental", "Device Loss/Theft", "Physical loss of laptops, mobiles, or storage media."),
    ("Accidental", "Patching Failure", "Failure to apply critical security updates."),

    # Structural / Technical Failure
    ("Structural", "Hardware Failure", "Physical breakdown of servers, hard drives, or network equipment."),
    ("Structural", "Software Failure / Bug", "Errors in code causing interruptions or unexpected behavior."),
    ("Structural", "Service Outage (ISP/Power)", "Interruption of critical third-party services (internet, power)."),

    # Environmental
    ("Environmental", "Fire", "Physical damage due to fire in the facility."),
    ("Environmental", "Flood / Water Damage", "Damage caused by leaks, heavy rains, or flooding."),
    ("Environmental", "Natural Disaster", "Earthquakes, severe storms, or other natural phenomena.")
]

# --- ENS (Esquema Nacional de Seguridad) ---
ens_controls = [
    ("op.acc.1", "Identificación", "El sistema debe asegurar la identificación inequívoca de los usuarios."),
    ("op.acc.2", "Autenticación", "Se debe verificar la identidad de los usuarios antes de permitir el acceso."),
    ("op.acc.3", "Gestión de privilegios", "Los derechos de acceso se asignarán según el principio de mínimo privilegio."),
    ("op.exp.1", "Gestión de incidentes", "Debe existir un procedimiento para la notificación y gestión de incidentes de seguridad."),
    ("op.exp.2", "Gestión de la configuración", "Se mantendrá un inventario actualizado de los componentes del sistema."),
    ("op.exp.3", "Gestión de cambios", "Todos los cambios en el sistema deben ser planificados y probados."),
    ("mp.s.1", "Protección de las instalaciones", "Las instalaciones estarán protegidas contra acceso físico no autorizado."),
    ("mp.info.1", "Protección de la información", "La información almacenada y en tránsito estará protegida criptográficamente."),
    ("mp.serv.1", "Continuidad del servicio", "Se establecerán planes para recuperar el servicio en caso de desastre.")
]

def seed_threats():
    print("Seeding threat types...")
    for category, name, description in common_threats:
        if not ThreatType.query.filter_by(name=name).first():
            threat = ThreatType(name=name, category=category, description=description)
            db.session.add(threat)
    
    try:
        db.session.commit()
        print("Threat types seeded successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding threats: {e}")

# --- ISO 27001:2022 (English) ---
iso_27001_controls = [
    # A.5 Organizational Controls (37)
    ("A.5.1", "Policies for information security", "Policies for information security and topic-specific policies shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel and relevant interested parties."),
    ("A.5.2", "Information security roles and responsibilities", "Information security roles and responsibilities shall be defined and allocated according to the organization needs."),
    ("A.5.3", "Segregation of duties", "Conflicting duties and conflicting areas of responsibility shall be segregated."),
    ("A.5.4", "Management responsibilities", "Management shall require all personnel to apply information security in accordance with the established information security policy, topic-specific policies and procedures of the organization."),
    ("A.5.5", "Contact with authorities", "The organization shall establish and maintain contact with relevant authorities."),
    ("A.5.6", "Contact with special interest groups", "The organization shall establish and maintain contact with special interest groups or other specialist security forums and professional associations."),
    ("A.5.7", "Threat intelligence", "Information relating to information security threats shall be collected and analysed to produce threat intelligence."),
    ("A.5.8", "Information security in project management", "Information security shall be integrated into project management."),
    ("A.5.9", "Inventory of information and other associated assets", "An inventory of information and other associated assets, including owners, shall be developed and maintained."),
    ("A.5.10", "Acceptable use of information and other associated assets", "Rules for the acceptable use of information and other associated assets shall be identified, documented and implemented."),
    ("A.5.11", "Return of assets", "Personnel and other interested parties as appropriate shall return all the organization assets in their possession upon change or termination of their employment, contract or agreement."),
    ("A.5.12", "Classification of information", "Information shall be classified in terms of legal requirements, value, criticality and sensitivity to unauthorised disclosure or modification."),
    ("A.5.13", "Labelling of information", "An appropriate set of procedures for information labelling shall be developed and implemented in accordance with the information classification scheme adopted by the organization."),
    ("A.5.14", "Information transfer", "Information transfer rules, procedures and agreements shall be in place for all types of transfer facilities within the organization and between the organization and other parties."),
    ("A.5.15", "Access control", "Rules to control physical and logical access to information and other associated assets shall be established and implemented based on business and information security requirements."),
    ("A.5.16", "Identity management", "The full life cycle of identities shall be managed."),
    ("A.5.17", "Authentication information", "Allocation and management of authentication information shall be controlled by a management process, including advising personnel on the appropriate handling of authentication information."),
    ("A.5.18", "Access rights", "Access rights to information and other associated assets shall be provisioned, reviewed, modified and removed in accordance with the organization’s topic-specific policy on and rules for access control."),
    ("A.5.19", "Information security in supplier relationships", "Processes and procedures shall be defined and implemented to manage the information security risks associated with the use of supplier’s products or services."),
    ("A.5.20", "Addressing information security within supplier agreements", "Relevant information security requirements shall be established and agreed with each supplier based on the type of supplier relationship."),
    ("A.5.21", "Managing information security in the ICT supply chain", "Processes and procedures shall be defined and implemented to manage the information security risks associated with the ICT products and services supply chain."),
    ("A.5.22", "Monitoring, review and change management of supplier services", "The organization shall regularly monitor, review, evaluate and manage change in supplier information security practices and service delivery."),
    ("A.5.23", "Information security for use of cloud services", "Processes for acquisition, use, management and exit from cloud services shall be established in accordance with the organization’s information security requirements."),
    ("A.5.24", "Information security incident management planning and preparation", "The organization shall plan and prepare for managing information security incidents by defining, establishing and communicating information security incident management processes, roles and responsibilities."),
    ("A.5.25", "Assessment and decision on information security events", "The organization shall assess information security events and decide if they are to be categorized as information security incidents."),
    ("A.5.26", "Response to information security incidents", "Information security incidents shall be responded to in accordance with the documented procedures."),
    ("A.5.27", "Learning from information security incidents", "Knowledge gained from information security incidents shall be used to strengthen and improve the information security controls."),
    ("A.5.28", "Collection of evidence", "The organization shall establish and implement procedures for the identification, collection, acquisition and preservation of evidence related to information security events."),
    ("A.5.29", "Information security during disruption", "The organization shall plan how to maintain information security at an appropriate level during disruption."),
    ("A.5.30", "ICT readiness for business continuity", "ICT readiness shall be planned, implemented, maintained and tested based on business continuity objectives and ICT continuity requirements."),
    ("A.5.31", "Legal, statutory, regulatory and contractual requirements", "Legal, statutory, regulatory and contractual requirements relevant to information security and the organization’s approach to meet these requirements shall be identified, documented and kept up to date."),
    ("A.5.32", "Intellectual property rights", "The organization shall implement appropriate procedures to protect intellectual property rights."),
    ("A.5.33", "Protection of records", "Records shall be protected from loss, destruction, falsification, unauthorized access and unauthorized release."),
    ("A.5.34", "Privacy and protection of PII", "The organization shall identify and meet the requirements regarding the preservation of privacy and protection of PII according to applicable laws and regulations and contractual requirements."),
    ("A.5.35", "Independent review of information security", "The organization’s approach to managing information security and its implementation including people, processes and technologies shall be reviewed independently at planned intervals, or when significant changes occur."),
    ("A.5.36", "Compliance with policies, rules and standards for information security", "Compliance with the organization’s information security policy, topic-specific policies, rules and standards shall be regularly reviewed."),
    ("A.5.37", "Documented operating procedures", "Operating procedures for information processing facilities shall be documented and made available to personnel who need them."),

    # A.6 People Controls (8)
    ("A.6.1", "Screening", "Background verification checks on all candidates to become personnel shall be carried out prior to joining the organization and on an ongoing basis taking into consideration applicable laws, regulations and ethics and be proportional to the business requirements, the classification of the information to be accessed and the perceived risks."),
    ("A.6.2", "Terms and conditions of employment", "The employment contractual agreements shall state the personnel’s and the organization’s responsibilities for information security."),
    ("A.6.3", "Information security awareness, education and training", "Personnel of the organization and relevant interested parties shall receive appropriate information security awareness, education and training and regular updates of the organization’s information security policy, topic-specific policies and procedures, as relevant for their job function."),
    ("A.6.4", "Disciplinary process", "A disciplinary process shall be formalized and communicated to take action against personnel and other relevant interested parties who have committed an information security policy violation."),
    ("A.6.5", "Responsibilities after termination or change of employment", "Information security responsibilities and duties that remain valid after termination or change of employment shall be defined, enforced and communicated to relevant personnel and other interested parties."),
    ("A.6.6", "Confidentiality or non-disclosure agreements", "Confidentiality or non-disclosure agreements reflecting the organization’s needs for the protection of information shall be identified, documented, regularly reviewed and signed by personnel and other relevant interested parties."),
    ("A.6.7", "Remote working", "Security measures shall be implemented when personnel are working remotely to protect information accessed, processed or stored outside the organization’s premises."),
    ("A.6.8", "Information security event reporting", "The organization shall provide a mechanism for personnel to report observed or suspected information security events through appropriate channels in a timely manner."),

    # A.7 Physical Controls (14)
    ("A.7.1", "Physical security perimeters", "Security perimeters shall be defined and used to protect areas that contain information and other associated assets."),
    ("A.7.2", "Physical entry", "Secure areas shall be protected by appropriate entry controls and access points."),
    ("A.7.3", "Securing offices, rooms and facilities", "Physical security for offices, rooms and facilities shall be designed and implemented."),
    ("A.7.4", "Physical security monitoring", "Premises shall be continuously monitored for unauthorized physical access."),
    ("A.7.5", "Protecting against physical and environmental threats", "Protection against physical and environmental threats, such as natural disasters and other intentional or unintentional physical threats to infrastructure shall be designed and implemented."),
    ("A.7.6", "Working in secure areas", "Security measures for working in secure areas shall be designed and implemented."),
    ("A.7.7", "Clear desk and clear screen", "Clear desk rules for papers and removable storage media and clear screen rules for information processing facilities shall be defined and appropriately enforced."),
    ("A.7.8", "Equipment siting and protection", "Equipment shall be sited and protected to reduce the risks from environmental threats and hazards, and opportunities for unauthorized access."),
    ("A.7.9", "Security of assets off-premises", "Off-site assets shall be protected."),
    ("A.7.10", "Storage media", "Storage media shall be managed through their life cycle of acquisition, use, storage and disposal in accordance with the organization’s classification scheme and handling requirements."),
    ("A.7.11", "Supporting utilities", "Information processing facilities shall be protected from power failures and other disruptions caused by failures in supporting utilities."),
    ("A.7.12", "Cabling security", "Cables carrying power, data or supporting information services shall be protected from interception, interference or damage."),
    ("A.7.13", "Equipment maintenance", "Equipment shall be maintained correctly to ensure its continued availability and integrity."),
    ("A.7.14", "Secure disposal or re-use of equipment", "Items of equipment containing storage media shall be verified to ensure that any sensitive data and licensed software has been removed or securely overwritten prior to disposal or re-use."),

    # A.8 Technological Controls (34)
    ("A.8.1", "User endpoint devices", "Information stored on, processed by or accessible via user endpoint devices shall be protected."),
    ("A.8.2", "Privileged access rights", "The allocation and use of privileged access rights shall be restricted and managed."),
    ("A.8.3", "Information access restriction", "Access to information and other associated assets shall be restricted in accordance with the established topic-specific policy on access control."),
    ("A.8.4", "Access to source code", "Read and write access to source code, development tools and software libraries shall be appropriately managed."),
    ("A.8.5", "Secure authentication", "Secure authentication technologies and procedures shall be implemented based on information access restrictions and the topic-specific policy on access control."),
    ("A.8.6", "Capacity management", "The use of resources shall be monitored and adjusted in line with current and expected capacity requirements."),
    ("A.8.7", "Protection against malware", "Protection against malware shall be implemented and supported by appropriate user awareness."),
    ("A.8.8", "Management of technical vulnerabilities", "Information about technical vulnerabilities of information systems in use shall be obtained, the organization’s exposure to such vulnerabilities shall be evaluated and appropriate measures shall be taken."),
    ("A.8.9", "Configuration management", "Configurations, including security configurations, of hardware, software, services and networks shall be established, documented, implemented, monitored and reviewed."),
    ("A.8.10", "Information deletion", "Information stored in information systems, devices or in any other storage media shall be deleted when no longer required."),
    ("A.8.11", "Data masking", "Data masking shall be used in accordance with the organization’s topic-specific policy on access control and other related topic-specific policies, and business requirements, taking applicable legislation into consideration."),
    ("A.8.12", "Data leakage prevention", "Data leakage prevention measures shall be applied to systems, networks and any other devices that process, store or transmit sensitive information."),
    ("A.8.13", "Information backup", "Backup copies of information, software and systems shall be maintained and regularly tested in accordance with the agreed topic-specific policy on backup."),
    ("A.8.14", "Redundancy of information processing facilities", "Information processing facilities shall be implemented with redundancy sufficient to meet availability requirements."),
    ("A.8.15", "Logging", "Logs that record activities, exceptions, faults and other relevant events shall be produced, stored, protected and analysed."),
    ("A.8.16", "Monitoring activities", "Networks, systems and applications shall be monitored for anomalous behaviour and appropriate actions taken to evaluate potential information security incidents."),
    ("A.8.17", "Clock synchronization", "The clocks of information processing systems used by the organization shall be synchronized to approved time sources."),
    ("A.8.18", "Use of privileged utility programs", "The use of utility programs that can be capable of overriding system and application controls shall be restricted and tightly controlled."),
    ("A.8.19", "Installation of software on operational systems", "Procedures and measures shall be implemented to securely manage software installation on operational systems."),
    ("A.8.20", "Networks security", "Networks and network devices shall be secured, managed and controlled to protect the information systems and applications."),
    ("A.8.21", "Security of network services", "Security mechanisms, service levels and service requirements of network services shall be identified, implemented and monitored."),
    ("A.8.22", "Segregation of networks", "Groups of information services, users and information systems shall be segregated in the organization’s networks."),
    ("A.8.23", "Web filtering", "Access to external websites shall be managed to reduce exposure to malicious content."),
    ("A.8.24", "Use of cryptography", "Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented."),
    ("A.8.25", "Secure development life cycle", "Rules for the secure development of software and systems shall be established and applied."),
    ("A.8.26", "Application security requirements", "Information security requirements shall be identified, specified and approved when developing or acquiring applications."),
    ("A.8.27", "Secure system architecture and engineering principles", "Principles for engineering secure systems shall be established, documented, maintained and applied to any information system development activities."),
    ("A.8.28", "Secure coding", "Secure coding principles shall be applied to software development."),
    ("A.8.29", "Security testing in development and acceptance", "Security testing processes shall be defined and implemented in the development life cycle."),
    ("A.8.30", "Outsourced development", "The organization shall direct, monitor and review the activities related to outsourced system development."),
    ("A.8.31", "Separation of development, test and production environments", "Development, testing and production environments shall be separated and secured."),
    ("A.8.32", "Change management", "Changes to information processing facilities and information systems shall be subject to change management procedures."),
    ("A.8.33", "Test information", "Test information shall be appropriately selected, protected and managed."),
    ("A.8.34", "Protection of information systems during audit testing", "Audit tests and other assurance activities involving assessment of operational systems shall be planned and agreed between the tester and appropriate management.")
]

itil_v4_practices = [
    # General Management Practices (14)
    ("G-01", "Architecture management", "The practice of providing an understanding of all the different elements that make up an organization and how those elements interrelate, enabling the organization to effectively achieve its current and future objectives."),
    ("G-02", "Continual improvement", "The practice of aligning the organization’s practices and services with changing business needs through the ongoing improvement of products, services, and practices, or any element involved in the management of products and services."),
    ("G-03", "Information security management", "The practice of protecting the information needed by the organization to conduct its business. This includes understanding and managing risks to the confidentiality, integrity, and availability of information."),
    ("G-04", "Knowledge management", "The practice of maintaining and improving the effective, efficient, and convenient use of information and knowledge across the organization."),
    ("G-05", "Measurement and reporting", "The practice of supporting good decision-making and continual improvement by decreasing the levels of uncertainty. This is achieved through the collection of relevant data on various managed objects and the valid assessment of this data in an appropriate context."),
    ("G-06", "Organizational change management", "The practice of ensuring that changes in an organization are smoothly and successfully implemented, and that lasting benefits are achieved by managing the human aspects of the changes."),
    ("G-07", "Portfolio management", "The practice of ensuring that the organization has the right mix of programs, projects, products, and services to execute the organization’s strategy within its funding and resource constraints."),
    ("G-08", "Project management", "The practice of ensuring that all the organization’s projects are successfully delivered. This is achieved by planning, delegating, monitoring, and maintaining control of all aspects of the project, and keeping the motivation of the people involved."),
    ("G-09", "Relationship management", "The practice of establishing and nurturing the links between the organization and its stakeholders at strategic and tactical levels. It includes the identification, analysis, monitoring, and continual improvement of relationships with and between stakeholders."),
    ("G-10", "Risk management", "The practice of ensuring that the organization understands and effectively handles risks. Establishing a systemic approach to organizing the inputs, activities, and outputs of risk management."),
    ("G-11", "Service financial management", "The practice of supporting the organization’s strategies and plans for service management by ensuring that the organization’s financial resources and investments are being used effectively."),
    ("G-12", "Strategy management", "The practice of formulating the goals of the organization and adopting the courses of action and allocation of resources necessary for achieving those goals."),
    ("G-13", "Supplier management", "The practice of ensuring that the organization’s suppliers and their performances are managed appropriately to support the seamless provision of quality products and services."),
    ("G-14", "Workforce and talent management", "The practice of ensuring that the organization has the right people with the appropriate skills and knowledge and in the correct roles to support its business objectives."),

    # Service Management Practices (17)
    ("S-01", "Availability management", "The practice of ensuring that services deliver agreed levels of availability to meet the needs of customers and users."),
    ("S-02", "Business analysis", "The practice of analyzing a business or some element of it, defining its associated needs and recommending solutions to address these needs and/or solve a business problem."),
    ("S-03", "Capacity and performance management", "The practice of ensuring that services achieve agreed and expected performance levels, satisfying current and future demand in a cost-effective way."),
    ("S-04", "Change enablement", "The practice of ensuring that risks are properly assessed, authorizing changes to proceed, and managing a change schedule in order to maximize the number of successful service and product changes."),
    ("S-05", "Incident management", "The practice of minimizing the negative impact of incidents by restoring normal service operation as quickly as possible."),
    ("S-06", "IT asset management", "The practice of planning and managing the full lifecycle of all IT assets to help the organization optimize value, control costs, manage risks, support decision-making about purchase, re-use, retirement, and disposal of assets, and meet regulatory and contractual requirements."),
    ("S-07", "Monitoring and event management", "The practice of systematically observing services and service components, and recording and reporting selected changes of state identified as events."),
    ("S-08", "Problem management", "The practice of reducing the likelihood and impact of incidents by identifying actual and potential causes of incidents, and managing workarounds and known errors."),
    ("S-09", "Release management", "The practice of making new and changed services and features available for use."),
    ("S-10", "Service catalogue management", "The practice of providing a single source of consistent information on all services and service offerings, and ensuring that it is available to the relevant audience."),
    ("S-11", "Service configuration management", "The practice of ensuring that accurate and reliable information about the configuration of services, and the configuration items that support them, is available when and where it is needed."),
    ("S-12", "Service continuity management", "The practice of ensuring that the availability and performance of a service are maintained at sufficient levels in case of a disaster."),
    ("S-13", "Service design", "The practice of designing products and services that are fit for purpose, fit for use, and that can be delivered by the organization and its ecosystem."),
    ("S-14", "Service desk", "The practice of capturing demand for incident resolution and service requests. It should also be the entry point and single point of contact for the service provider with all of its users."),
    ("S-15", "Service level management", "The practice of setting clear business-based targets for service levels, and ensuring that delivery of services is properly assessed, monitored, and managed against these targets."),
    ("S-16", "Service request management", "The practice of supporting the agreed quality of a service by handling all pre-defined, user-initiated service requests in an effective and user-friendly manner."),
    ("S-17", "Service validation and testing", "The practice of ensuring that new or changed products and services meet defined requirements."),

    # Technical Management Practices (3)
    ("T-01", "Deployment management", "The practice of moving new or changed hardware, software, documentation, processes, or any other component to live environments."),
    ("T-02", "Infrastructure and platform management", "The practice of overseeing the infrastructure and platforms used by an organization. This enables the monitoring of technology solutions available to the organization, including the technology of external service providers."),
    ("T-03", "Software development and management", "The practice of ensuring that applications meet stakeholder needs in terms of functionality, reliability, maintainability, compliance, and auditability.")
]

itil_v3_processes = [
    # Service Strategy
    ("SS-01", "Strategy Management for IT Services", "Process responsible for defining and maintaining the perspective, position, plans and patterns of an organization with regard to its services and the management of those services."),
    ("SS-02", "Service Portfolio Management", "Process responsible for managing the service portfolio. Service portfolio management ensures that the service provider has the right mix of services to balance the investment in IT with the ability to meet business outcomes."),
    ("SS-03", "Financial Management for IT Services", "Process responsible for managing an IT service provider's budgeting, accounting and charging requirements."),
    ("SS-04", "Demand Management", "Process responsible for understanding, anticipating and influencing customer demand for services. Demand management works with capacity management to ensure that the service provider has sufficient capacity to meet the required demand."),
    ("SS-05", "Business Relationship Management", "Process responsible for maintaining a positive relationship with customers. Business relationship management identifies customer needs and ensures that the service provider is able to meet these needs."),

    # Service Design
    ("SD-01", "Design Coordination", "Process responsible for coordinating all service design activities, processes, and resources."),
    ("SD-02", "Service Level Management", "Process responsible for negotiating service level agreements, and ensuring that these are met. It monitors and reports on service levels, and holds regular service reviews with customers."),
    ("SD-03", "Service Catalogue Management", "Process responsible for ensuring that the Service Catalogue is produced and maintained, containing accurate information on all operational services and those being prepared to be run operationally."),
    ("SD-04", "Availability Management", "Process responsible for ensuring that IT services meet the current and future availability needs of the business in a cost-effective and timely manner."),
    ("SD-05", "Information Security Management", "Process responsible for ensuring that the confidentiality, integrity and availability of an organization's assets, information, data and IT services match the agreed needs of the business."),
    ("SD-06", "Supplier Management", "Process responsible for ensuring that all contracts with suppliers support the needs of the business, and that all suppliers meet their contractual commitments."),
    ("SD-07", "Capacity Management", "Process responsible for ensuring that the capacity of IT services and the IT infrastructure matches the evolving needs of the business in the most cost-effective and timely manner."),
    ("SD-08", "IT Service Continuity Management", "Process responsible for managing risks that could seriously impact IT services. ITSCM ensures that the IT service provider can always provide minimum agreed service levels."),

    # Service Transition
    ("ST-01", "Transition Planning and Support", "Process responsible for planning all service transition processes and coordinating the resources that they require."),
    ("ST-02", "Change Management", "Process responsible for controlling the lifecycle of all changes, enabling beneficial changes to be made with minimum disruption to IT services."),
    ("ST-03", "Service Asset and Configuration Management", "Process responsible for ensuring that the assets required to deliver services are properly controlled, and that accurate and reliable information about those assets is available when and where it is needed."),
    ("ST-04", "Release and Deployment Management", "Process responsible for planning, scheduling and controlling the build, test and deployment of releases, and for delivering new functionality required by the business while protecting the integrity of existing services."),
    ("ST-05", "Service Validation and Testing", "Process responsible for validation and testing of a new or changed IT service. This process ensures that the IT service matches its design specification and meets the needs of the business."),
    ("ST-06", "Change Evaluation", "Process responsible for assessing major changes, like the introduction of a new service or a substantial change to an existing service, before those changes are allowed to proceed."),
    ("ST-07", "Knowledge Management", "Process responsible for sharing perspectives, ideas, experience and information, and for ensuring that these are available in the right place and at the right time."),

    # Service Operation
    ("SO-01", "Event Management", "Process responsible for managing events throughout their lifecycle. Event management is one of the main activities of IT operations."),
    ("SO-02", "Incident Management", "Process responsible for managing the lifecycle of all incidents. Incident management ensures that normal service operation is restored as quickly as possible and the business impact is minimized."),
    ("SO-03", "Request Fulfilment", "Process responsible for managing the lifecycle of all service requests."),
    ("SO-04", "Problem Management", "Process responsible for managing the lifecycle of all problems. Problem management proactively prevents incidents from happening and minimizes the impact of incidents that cannot be prevented."),
    ("SO-05", "Access Management", "Process responsible for allowing users to make use of IT services, data, or other assets. Access management helps to protect the confidentiality, integrity and availability of assets by ensuring that only authorized users are able to access or modify them."),

    # Continual Service Improvement
    ("CSI-01", "Seven-Step Improvement Process", "Process responsible for defining and managing the steps needed to identify, define, gather, process, analyze, present and implement improvements.")
]

pci_dss_v4_requirements = [
    # Principal Requirements (12)
    ("Req-1", "Install and Maintain Network Security Controls", "Network security controls (NSCs) (e.g., firewalls, cloud security groups) must be configured and maintained to protect Cardholder Data Environments (CDE) from unauthorized access."),
    ("Req-2", "Apply Secure Configurations to All System Components", "Vendor-supplied defaults (passwords, strings) must be changed. Systems must be hardened and configured securely before being connected to the network."),
    ("Req-3", "Protect Stored Account Data", "Stored cardholder data (PAN, SAD) must be kept to a minimum and encrypted. Sensitive Authentication Data (SAD) must not be stored after authorization."),
    ("Req-4", "Protect Cardholder Data with Strong Cryptography During Transmission", "Cardholder data must be encrypted with strong cryptography (e.g., TLS 1.2+) during transmission over open, public networks (e.g., internet, wireless)."),
    ("Req-5", "Protect All Systems and Networks from Malicious Software", "Anti-malware mechanisms must be deployed and maintained on all system components to detect and protect against malicious software."),
    ("Req-6", "Develop and Maintain Secure Systems and Software", "Security vulnerabilities must be identified and managed. Software must be developed securely (Secure SDLC) to prevent vulnerabilities (e.g., OWASP Top 10)."),
    ("Req-7", "Restrict Access to System Components and Cardholder Data by Business Need to Know", "Access to cardholder data and system components must be restricted to only those individuals whose job requires such access."),
    ("Req-8", "Identify Users and Authenticate Access to System Components", "Each user must be assigned a unique ID. Access to system components must be authenticated with at least one factor (MFA required for all CDE access)."),
    ("Req-9", "Restrict Physical Access to Cardholder Data", "Physical access to CDE systems, media, and facilities must be restricted and monitored to prevent unauthorized access."),
    ("Req-10", "Log and Monitor All Access to System Components and Cardholder Data", "Logging mechanisms and the ability to track user activities are critical. Logs must be reviewed regularly to detect anomalies."),
    ("Req-11", "Test Security of Systems and Networks Regularly", "Vulnerability scans, penetration testing, and intrusion detection/prevention techniques must be performed frequently to ensure security."),
    ("Req-12", "Support Information Security with Organizational Policies and Programs", "A strong information security policy sets the tone for the whole entity and informs personnel what is expected of them.")
]

soc2_trust_criteria = [
    # Trust Services Criteria (5)
    ("CC (Security)", "Security (Common Criteria)", "The system is protected against unauthorized access (both physical and logical). This is the only mandatory criteria for SOC 2 (Common Criteria)."),
    ("A (Availability)", "Availability", "The system is available for operation and use as committed or agreed. Controls include performance monitoring, disaster recovery, and incident handling."),
    ("PI (Processing)", "Processing Integrity", "System processing is complete, valid, accurate, timely, and authorized. Controls include data validation, error handling, and quality assurance."),
    ("C (Confidentiality)", "Confidentiality", "Information designated as confidential is protected as committed or agreed. Includes encryption, access controls, and data classification."),
    ("P (Privacy)", "Privacy", "Personal information is collected, used, retained, disclosed, and disposed of in conformity with the entity’s privacy notice. Aligns with GAPP (Generally Accepted Privacy Principles).")
]

nist_csf_functions = [
    # NIST CSF 2.0 Functions (6)
    ("GV (Govern)", "Govern", "The organization’s cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored."),
    ("ID (Identify)", "Identify", "The organization’s current cybersecurity risks are understood. Includes Asset Management, Risk Assessment, and Supply Chain Risk Management."),
    ("PR (Protect)", "Protect", "Safeguards to manage the organization’s cybersecurity risks are used. Includes Identity Management, Awareness & Training, Data Security, and Platform Security."),
    ("DE (Detect)", "Detect", "Possible cybersecurity attacks and compromises are found and analyzed. Includes Continuous Monitoring and Adverse Event Analysis."),
    ("RS (Respond)", "Respond", "Actions regarding a detected cybersecurity incident are performed. Includes Incident Management, Analysis, Mitigation, and Communication."),
    ("RC (Recover)", "Recover", "Assets and operations affected by a cybersecurity incident are restored. Includes Recovery Planning and Communication.")
]

def seed_production_frameworks():
    """
    Seeds production frameworks (master data) into the database if they do not exist.
    """
    print("Seeding production frameworks...")
    
    frameworks_added = False
    
    # --- ISO 27001:2022 ---
    if not Framework.query.filter_by(name='ISO27001:2022').first():
        print("Creating Framework ISO27001:2022...")
        iso_framework = Framework(
            name='ISO27001:2022',
            description='Annex A controls for information security, cybersecurity and privacy protection.',
            link='https://www.iso.org/standard/82875.html',
            is_custom=False,
            is_active=False
        )
        
        # Add the 93 controls
        for control_id, name, description in iso_27001_controls:
            iso_framework.framework_controls.append(FrameworkControl(
                control_id=control_id, 
                name=name,
                description=description
            ))
        
        db.session.add(iso_framework)
        frameworks_added = True
        print(f"ISO27001:2022 added with {len(iso_27001_controls)} controls.")

    # --- ITIL v4 ---
    if not Framework.query.filter_by(name='ITIL v4').first():
        print("Creating Framework ITIL v4...")
        itil_framework = Framework(
            name='ITIL v4',
            description='Framework for IT Service Management (ITSM) focused on co-creating value through 34 management practices.',
            link='https://www.axelos.com/best-practice-solutions/itil',
            is_custom=False,
            is_active=False
        )
        
        # Add the 34 practices
        for control_id, name, description in itil_v4_practices:
            itil_framework.framework_controls.append(FrameworkControl(
                control_id=control_id, 
                name=name,
                description=description
            ))

        db.session.add(itil_framework)
        frameworks_added = True
        print(f"ITIL v4 added with {len(itil_v4_practices)} practices.")

    # --- ITIL v3 ---
    if not Framework.query.filter_by(name='ITIL v3').first():
        print("Creating Framework ITIL v3...")
        itil_v3_framework = Framework(
            name='ITIL v3',
            description='Previous version of the IT Service Management (ITSM) framework organized around the Service Lifecycle (Strategy, Design, Transition, Operation, CSI).',
            link='https://www.axelos.com/best-practice-solutions/itil',
            is_custom=False,
            is_active=False
        )
        
        # Add the 26 processes
        for control_id, name, description in itil_v3_processes:
            itil_v3_framework.framework_controls.append(FrameworkControl(
                control_id=control_id, 
                name=name,
                description=description
            ))

        db.session.add(itil_v3_framework)
        frameworks_added = True
        print(f"ITIL v3 added with {len(itil_v3_processes)} processes.")
        
    # --- PCI DSS v4.0 ---
    if not Framework.query.filter_by(name='PCI DSS v4.0').first():
        print("Creating Framework PCI DSS v4.0...")
        pci_framework = Framework(
            name='PCI DSS v4.0',
            description='Payment Card Industry Data Security Standard (v4.0). Essential for any organization that stores, processes, or transmits cardholder data.',
            link='https://www.pcisecuritystandards.org/',
            is_custom=False,
            is_active=False
        )
        
        # Add the 12 Principal Requirements
        for control_id, name, description in pci_dss_v4_requirements:
            pci_framework.framework_controls.append(FrameworkControl(
                control_id=control_id, 
                name=name,
                description=description
            ))

        db.session.add(pci_framework)
        frameworks_added = True
        print(f"PCI DSS v4.0 added with {len(pci_dss_v4_requirements)} requirements.")

    # --- SOC 2 ---
    if not Framework.query.filter_by(name='SOC 2').first():
        print("Creating Framework SOC 2...")
        soc2_framework = Framework(
            name='SOC 2',
            description='AICPA Trust Services Criteria (TSC) for Service Organizations. Focuses on Security, Availability, Processing Integrity, Confidentiality, and Privacy.',
            link='https://www.aicpa.org/topic/audit-assurance/audit-and-assurance-greater-than-soc-2',
            is_custom=False,
            is_active=False
        )
        
        # Add the 5 Trust Services Criteria
        for control_id, name, description in soc2_trust_criteria:
            soc2_framework.framework_controls.append(FrameworkControl(
                control_id=control_id, 
                name=name,
                description=description
            ))

        db.session.add(soc2_framework)
        frameworks_added = True
        print(f"SOC 2 added with {len(soc2_trust_criteria)} criteria.")

    # --- NIST CSF 2.0 ---
    if not Framework.query.filter_by(name='NIST CSF 2.0').first():
        print("Creating Framework NIST CSF 2.0...")
        nist_framework = Framework(
            name='NIST CSF 2.0',
            description='National Institute of Standards and Technology Cybersecurity Framework.',
            link='https://www.nist.gov/cyberframework',
            is_custom=False,
            is_active=False
        )
        
        for control_id, name, description in nist_csf_functions:
            control = FrameworkControl(
                control_id=control_id,
                name=name,
                description=description
            )
            nist_framework.framework_controls.append(control)
        
        db.session.add(nist_framework)
        print(f"NIST CSF 2.0 added with {len(nist_csf_functions)} functions.")
        frameworks_added = True

    # --- ENS (Esquema Nacional de Seguridad) ---
    if not Framework.query.filter_by(name='ENS (Spanish)').first():
        print("Creating Framework ENS (Spanish)...")
        ens_framework = Framework(
            name='ENS (Spanish)',
            description='Esquema Nacional de Seguridad (España)',
            link='https://www.ccn-cert.cni.es/ens.html',
            is_custom=False,
            is_active=False
        )
        
        for control_id, name, description in ens_controls:
            control = FrameworkControl(
                control_id=control_id,
                name=name,
                description=description
            )
            ens_framework.framework_controls.append(control)
            
        db.session.add(ens_framework)
        print(f"ENS (Spanish) added with {len(ens_controls)} controls.")
        frameworks_added = True

    if frameworks_added:
        try:
            db.session.commit()
            print("Production frameworks seeded successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding frameworks: {e}")
    else:
        print("Production frameworks already exist. No changes made.")