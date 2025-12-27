# Workflows

OpsDeck is designed around several key operational workflows.

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
