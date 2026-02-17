# OpsDeck Operational Workflows

This document describes the primary workflows implemented in OpsDeck and how different modules interact to support IT operations and governance.

## Asset Lifecycle Management

1.  **Procurement**:
    *   A **Purchase** is recorded, linked to a **Supplier** and **Budget**.
    *   The purchase details (cost, date, warranty) form the basis for the asset record.

2.  **Onboarding**:
    *   An **Asset** is created from the purchase.
    *   Status is set to "In Stock".
    *   Asset is tagged and assigned a location.

3.  **Assignment**:
    *   The asset is assigned to a **User**.
    *   Status changes to "In Use".
    *   The user sees the asset in their profile.

4.  **Maintenance**:
    *   Issues are logged via **MaintenanceLog**.
    *   Status may change to "In Repair".
    *   Costs of repair are tracked.

5.  **End of Life**:
    *   Asset is marked as "Awaiting Disposal".
    *   A **DisposalRecord** is created, detailing the method (e-waste, sale, donation) and any proceeds.
    *   Asset is archived but remains in history for audit purposes.

## Service Management (Service Catalog)

1.  **Definition**:
    *   **Business Services** (e.g., "Customer Portal", "HR System") are defined.
    *   Services are designated as "Critical" or "Non-Critical".

2.  **Dependency Mapping**:
    *   **Components** (Assets, Software, other Services) are linked to the Business Service.
    *   This creates a topology view showing what infrastructure supports which business function.

3.  **Context & Compliance**:
    *   Documentation, Policies, and Security Activities are linked to the Service.
    *   Compliance status is tracked at the service level, linking the service to specific Framework Controls.

## Compliance & Audits

1.  **Framework Management**:
    *   **Frameworks** (ISO 27001, SOC2) and **FrameworkControls** are defined.

2.  **Evidence Collection (Continuous)**:
    *   Users link "Linkable Objects" (Assets, Policies, Services, etc.) to controls via the **Compliance Link** feature.
    *   This builds a continuous repository of evidence.

3.  **Audit Execution (The Defense Room)**:
    *   **Audit Creation**:
        *   **Fresh Start**: Create a blank audit.
        *   **Renewal**: Clone a previous audit's scope and evidence.
    *   **Snapshot**: The system freezes the current state of Framework Controls and their links into **AuditControlItems**.
    *   **Gap Analysis**: Auditors review the interface to see controls without evidence.
    *   **Locking**: Once finalized, the audit is **Locked** to prevent further changes, creating an immutable record.

## Risk Management

1.  **Identification**:
    *   **Run a Risk Assessment** to identify threats.
    *   Create a **Risk** record, categorizing it (CIA Triad) and assigning an owner.

2.  **Context**:
    *   Link the Risk to affected **Assets**, **Business Services**, or **Vendors**.

3.  **Assessment**:
    *   Define Inherent Risk (Impact x Likelihood).
    *   Define Residual Risk (after mitigation).

4.  **Mitigation**:
    *   Link **Security Activities** (mitigations) to the Risk.
    *   Set **Validity Periods** for the assessment (e.g., this risk assessment is valid until the next review date).

## Procurement & Budgets

1.  **Budgeting**:
    *   **Budgets** are created with defined **Validity Periods**.
    *   Status is tracked (Active/Expired) based on dates.

2.  **Purchasing**:
    *   Purchases are validated against the budget's validity period.
    *   Subscriptions are tracked for renewals.

3.  **Forecasting**:
    *   12-month forecast based on active subscriptions.

## Incident Management

1.  **Reporting**: A **SecurityIncident** is logged.
2.  **Investigation**: Evidence gathered, affected assets linked.
3.  **Resolution**: Root cause identified, status "Resolved".
4.  **Review**: Post-Incident Review (PIR), lessons learned.

## User Access Review (UAR) Automation

1.  **Comparison Setup**:
    *   Define a **UARComparison** with two datasets (e.g., HRIS vs. Identity Provider).
    *   Configure data sources (CSV upload, database query, API endpoint).
    *   Map fields for comparison (email, employee_id, etc.).

2.  **Scheduled Execution**:
    *   Comparisons can be scheduled (daily, weekly, monthly).
    *   APScheduler triggers **UARExecution** automatically.
    *   Data is loaded from configured sources and compared.

3.  **Finding Detection**:
    *   **UARFinding** records are created for discrepancies:
        *   **Mismatch**: Record exists in both but fields differ.
        *   **Orphan**: Record exists in system A but not B.
        *   **Missing**: Record exists in system B but not A.
    *   Each finding includes severity, affected user, and detailed comparison data.

4.  **Finding Management**:
    *   Findings can be marked as false positives.
    *   Bulk operations: assign, resolve, create incidents, export.
    *   Visual diff viewer shows field-by-field changes for mismatches.
    *   Comments and status tracking for resolution workflow.

5.  **Compliance Integration**:
    *   UAR findings can be linked to compliance controls.
    *   Regular UAR execution provides evidence for access governance requirements.
    *   Findings feed into compliance status for frameworks like SOC 2.

## Compliance Drift Detection

1.  **Snapshot Capture**:
    *   Daily automated snapshots of compliance status for all frameworks.
    *   Captures control status (compliant, manual, warning, non-compliant, uncovered).
    *   Manual snapshot creation available via UI.

2.  **Drift Analysis**:
    *   Compares consecutive snapshots to detect changes.
    *   Identifies **regressions** (status worsened) and **improvements**.
    *   Assigns severity: critical (non-compliant), high (warning), medium (other regressions).

3.  **Timeline Visualization**:
    *   Drift dashboard displays timeline of changes over configurable periods.
    *   Statistics cards show total regressions, improvements, and net change.
    *   Event details modal provides control-by-control breakdown.

4.  **Alerting**:
    *   Automatic alerts when critical regressions are detected.
    *   Logged to application logs for monitoring integration.
    *   Future: email/Slack notifications for immediate response.

## Universal Search

1.  **Query Execution**:
    *   Users enter search query in universal search interface.
    *   Search executes across configured entity types (assets, users, findings, incidents, etc.).
    *   Results grouped by entity type with result counts.

2.  **Faceted Filtering**:
    *   Dynamic filters based on search results (status, severity, date ranges).
    *   Entity type selection to narrow search scope.
    *   Filter application triggers new search with updated parameters.

3.  **Saved Searches**:
    *   Users can save frequently-used searches with filters.
    *   Saved searches accessible from sidebar for quick re-execution.
