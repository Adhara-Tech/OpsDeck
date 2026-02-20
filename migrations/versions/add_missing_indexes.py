"""Add missing indexes on FK, status, and is_archived columns

Revision ID: add_missing_indexes
Revises: subscription_pricing_models
Create Date: 2026-02-19

"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_missing_indexes'
down_revision = 'subscription_pricing_models'
branch_labels = None
depends_on = None

# (index_name, table, column_list)
INDEXES = [
    # --- auth.py ---
    ('ix_user_is_archived', 'user', ['is_archived']),
    ('ix_user_hide_from_org_chart', 'user', ['hide_from_org_chart']),
    ('ix_user_manager_id', 'user', ['manager_id']),
    ('ix_user_buddy_id', 'user', ['buddy_id']),
    ('ix_user_archived_orgchart', 'user', ['is_archived', 'hide_from_org_chart']),
    ('ix_user_session_user_id', 'user_session', ['user_id']),
    ('ix_org_chart_snapshot_created_by_id', 'org_chart_snapshot', ['created_by_id']),

    # --- assets.py ---
    ('ix_location_is_archived', 'location', ['is_archived']),
    ('ix_asset_user_id', 'asset', ['user_id']),
    ('ix_asset_location_id', 'asset', ['location_id']),
    ('ix_asset_supplier_id', 'asset', ['supplier_id']),
    ('ix_asset_purchase_id', 'asset', ['purchase_id']),
    ('ix_asset_is_archived', 'asset', ['is_archived']),
    ('ix_asset_status', 'asset', ['status']),
    ('ix_asset_assignment_asset_id', 'asset_assignment', ['asset_id']),
    ('ix_asset_assignment_user_id', 'asset_assignment', ['user_id']),
    ('ix_asset_custom_field_asset_id', 'asset_custom_field', ['asset_id']),
    ('ix_peripheral_user_id', 'peripheral', ['user_id']),
    ('ix_peripheral_asset_id', 'peripheral', ['asset_id']),
    ('ix_peripheral_location_id', 'peripheral', ['location_id']),
    ('ix_peripheral_purchase_id', 'peripheral', ['purchase_id']),
    ('ix_peripheral_supplier_id', 'peripheral', ['supplier_id']),
    ('ix_peripheral_is_archived', 'peripheral', ['is_archived']),
    ('ix_peripheral_assignment_peripheral_id', 'peripheral_assignment', ['peripheral_id']),
    ('ix_peripheral_assignment_user_id', 'peripheral_assignment', ['user_id']),
    ('ix_license_user_id', 'license', ['user_id']),
    ('ix_license_purchase_id', 'license', ['purchase_id']),
    ('ix_license_budget_id', 'license', ['budget_id']),
    ('ix_license_subscription_id', 'license', ['subscription_id']),
    ('ix_license_software_id', 'license', ['software_id']),
    ('ix_license_is_archived', 'license', ['is_archived']),
    ('ix_software_supplier_id', 'software', ['supplier_id']),
    ('ix_software_is_archived', 'software', ['is_archived']),
    ('ix_maintenance_log_assigned_to_id', 'maintenance_log', ['assigned_to_id']),
    ('ix_maintenance_log_asset_id', 'maintenance_log', ['asset_id']),
    ('ix_maintenance_log_peripheral_id', 'maintenance_log', ['peripheral_id']),
    ('ix_maintenance_log_status', 'maintenance_log', ['status']),
    ('ix_disposal_record_is_archived', 'disposal_record', ['is_archived']),
    ('ix_disposal_approval_disposal_id', 'disposal_approval', ['disposal_id']),
    ('ix_disposal_approval_changed_by_id', 'disposal_approval', ['changed_by_id']),
    ('ix_depreciation_schedule_asset_id', 'depreciation_schedule', ['asset_id']),
    ('ix_depreciation_schedule_peripheral_id', 'depreciation_schedule', ['peripheral_id']),

    # --- procurement.py ---
    ('ix_supplier_is_archived', 'supplier', ['is_archived']),
    ('ix_purchase_item_purchase_id', 'purchase_item', ['purchase_id']),
    ('ix_purchase_item_user_id', 'purchase_item', ['user_id']),
    ('ix_purchase_supplier_id', 'purchase', ['supplier_id']),
    ('ix_purchase_payment_method_id', 'purchase', ['payment_method_id']),
    ('ix_purchase_budget_id', 'purchase', ['budget_id']),
    ('ix_purchase_is_archived', 'purchase', ['is_archived']),
    ('ix_purchase_cost_validated_by_id', 'purchase', ['cost_validated_by_id']),
    ('ix_subscription_pricing_tier_subscription_id', 'subscription_pricing_tier', ['subscription_id']),
    ('ix_contact_user_id', 'contact', ['user_id']),
    ('ix_subscription_user_id', 'subscription', ['user_id']),
    ('ix_subscription_supplier_id', 'subscription', ['supplier_id']),
    ('ix_subscription_software_id', 'subscription', ['software_id']),
    ('ix_subscription_budget_id', 'subscription', ['budget_id']),
    ('ix_subscription_is_archived', 'subscription', ['is_archived']),
    ('ix_payment_method_is_archived', 'payment_method', ['is_archived']),

    # --- change.py ---
    ('ix_change_requester_id', 'change', ['requester_id']),
    ('ix_change_assignee_id', 'change', ['assignee_id']),
    ('ix_change_approved_by_id', 'change', ['approved_by_id']),
    ('ix_change_status', 'change', ['status']),
    ('ix_change_service_id', 'change', ['service_id']),
    ('ix_change_asset_id', 'change', ['asset_id']),
    ('ix_change_software_id', 'change', ['software_id']),
    ('ix_change_configuration_id', 'change', ['configuration_id']),
    ('ix_change_configuration_version_id', 'change', ['configuration_version_id']),

    # --- security.py ---
    ('ix_compliance_link_framework_control_id', 'compliance_link', ['framework_control_id']),
    ('ix_security_incident_reported_by_id', 'security_incident', ['reported_by_id']),
    ('ix_security_incident_owner_id', 'security_incident', ['owner_id']),
    ('ix_security_incident_assignee_id', 'security_incident', ['assignee_id']),
    ('ix_security_incident_status', 'security_incident', ['status']),
    ('ix_post_incident_review_incident_id', 'post_incident_review', ['incident_id']),
    ('ix_post_incident_review_locked_by_id', 'post_incident_review', ['locked_by_id']),
    ('ix_pir_lesson_review_id', 'pir_lesson', ['review_id']),
    ('ix_risk_affected_item_risk_id', 'risk_affected_item', ['risk_id']),
    ('ix_risk_affected_item_polymorphic', 'risk_affected_item', ['linkable_type', 'linkable_id']),
    ('ix_risk_mitigation_risk_id', 'risk_mitigation', ['risk_id']),
    ('ix_catalog_risk_catalog_id', 'catalog_risk', ['catalog_id']),
    ('ix_catalog_risk_threat_type_id', 'catalog_risk', ['threat_type_id']),
    ('ix_risk_owner_id', 'risk', ['owner_id']),
    ('ix_risk_status', 'risk', ['status']),
    ('ix_risk_threat_type_id', 'risk', ['threat_type_id']),
    ('ix_risk_source_catalog_risk_id', 'risk', ['source_catalog_risk_id']),
    ('ix_risk_history_risk_id', 'risk_history', ['risk_id']),
    ('ix_risk_review_risk_id', 'risk_review', ['risk_id']),
    ('ix_risk_review_user_id', 'risk_review', ['user_id']),
    ('ix_supplier_risk_supplier_id', 'supplier_risk', ['supplier_id']),
    ('ix_asset_inventory_conducted_by_user_id', 'asset_inventory', ['conducted_by_user_id']),
    ('ix_asset_inventory_status', 'asset_inventory', ['status']),
    ('ix_asset_inventory_item_inventory_id', 'asset_inventory_item', ['inventory_id']),
    ('ix_asset_inventory_item_asset_id', 'asset_inventory_item', ['asset_id']),
    ('ix_asset_inventory_item_user_id', 'asset_inventory_item', ['user_id']),
    ('ix_asset_inventory_item_status', 'asset_inventory_item', ['status']),
    ('ix_framework_control_framework_id', 'framework_control', ['framework_id']),
    ('ix_control_evidence_framework_control_id', 'control_evidence', ['framework_control_id']),

    # --- activities.py ---
    ('ix_activity_related_object_activity_id', 'activity_related_object', ['activity_id']),
    ('ix_activity_execution_activity_id', 'activity_execution', ['activity_id']),
    ('ix_activity_execution_executor_id', 'activity_execution', ['executor_id']),
    ('ix_activity_execution_status', 'activity_execution', ['status']),

    # --- communications.py ---
    ('ix_pack_template_pack_id', 'pack_template', ['pack_id']),
    ('ix_pack_template_template_id', 'pack_template', ['template_id']),
    ('ix_campaign_created_by_id', 'campaign', ['created_by_id']),
    ('ix_campaign_status', 'campaign', ['status']),
    ('ix_scheduled_communication_template_id', 'scheduled_communication', ['template_id']),
    ('ix_scheduled_communication_recipient_user_id', 'scheduled_communication', ['recipient_user_id']),
    ('ix_scheduled_communication_status', 'scheduled_communication', ['status']),
    ('ix_scheduled_communication_scheduled_date', 'scheduled_communication', ['scheduled_date']),

    # --- crm.py ---
    ('ix_lead_created_by_id', 'lead', ['created_by_id']),
    ('ix_lead_status', 'lead', ['status']),
    ('ix_lead_is_archived', 'lead', ['is_archived']),
    ('ix_evaluation_requirement_id', 'evaluation', ['requirement_id']),
    ('ix_evaluation_created_by_id', 'evaluation', ['created_by_id']),
    ('ix_opportunity_supplier_id', 'opportunity', ['supplier_id']),
    ('ix_opportunity_primary_contact_id', 'opportunity', ['primary_contact_id']),
    ('ix_opportunity_requirement_id', 'opportunity', ['requirement_id']),
    ('ix_opportunity_risk_id', 'opportunity', ['risk_id']),
    ('ix_opportunity_budget_id', 'opportunity', ['budget_id']),
    ('ix_opportunity_status', 'opportunity', ['status']),
    ('ix_opportunity_item_opportunity_id', 'opportunity_item', ['opportunity_id']),
    ('ix_opportunity_timeline_entry_opportunity_id', 'opportunity_timeline_entry', ['opportunity_id']),
    ('ix_supplier_contact_supplier_id', 'supplier_contact', ['supplier_id']),
    ('ix_supplier_contact_is_archived', 'supplier_contact', ['is_archived']),

    # --- risk_assessment.py ---
    ('ix_risk_assessment_status', 'risk_assessment', ['status']),
    ('ix_risk_assessment_item_assessment_id', 'risk_assessment_item', ['assessment_id']),
    ('ix_risk_assessment_item_original_risk_id', 'risk_assessment_item', ['original_risk_id']),
    ('ix_risk_assessment_evidence_item_id', 'risk_assessment_evidence', ['item_id']),
    ('ix_risk_assessment_evidence_polymorphic', 'risk_assessment_evidence', ['linkable_type', 'linkable_id']),

    # --- audits.py ---
    ('ix_compliance_audit_framework_id', 'compliance_audit', ['framework_id']),
    ('ix_compliance_audit_auditor_id', 'compliance_audit', ['auditor_id']),
    ('ix_compliance_audit_internal_lead_id', 'compliance_audit', ['internal_lead_id']),
    ('ix_compliance_audit_status', 'compliance_audit', ['status']),
    ('ix_audit_control_item_audit_id', 'audit_control_item', ['audit_id']),
    ('ix_audit_control_item_original_control_id', 'audit_control_item', ['original_control_id']),
    ('ix_audit_control_link_audit_item_id', 'audit_control_link', ['audit_item_id']),
    ('ix_audit_control_link_polymorphic', 'audit_control_link', ['linkable_type', 'linkable_id']),

    # --- onboarding.py ---
    ('ix_pack_item_pack_id', 'pack_item', ['pack_id']),
    ('ix_pack_item_software_id', 'pack_item', ['software_id']),
    ('ix_pack_item_service_id', 'pack_item', ['service_id']),
    ('ix_pack_item_subscription_id', 'pack_item', ['subscription_id']),
    ('ix_pack_item_course_id', 'pack_item', ['course_id']),
    ('ix_onboarding_process_user_id', 'onboarding_process', ['user_id']),
    ('ix_onboarding_process_pack_id', 'onboarding_process', ['pack_id']),
    ('ix_onboarding_process_assigned_manager_id', 'onboarding_process', ['assigned_manager_id']),
    ('ix_onboarding_process_assigned_buddy_id', 'onboarding_process', ['assigned_buddy_id']),
    ('ix_onboarding_process_status', 'onboarding_process', ['status']),
    ('ix_offboarding_process_user_id', 'offboarding_process', ['user_id']),
    ('ix_offboarding_process_manager_id', 'offboarding_process', ['manager_id']),
    ('ix_offboarding_process_status', 'offboarding_process', ['status']),
    ('ix_process_item_onboarding_process_id', 'process_item', ['onboarding_process_id']),
    ('ix_process_item_offboarding_process_id', 'process_item', ['offboarding_process_id']),

    # --- policy.py ---
    ('ix_policy_version_policy_id', 'policy_version', ['policy_id']),
    ('ix_policy_version_status', 'policy_version', ['status']),
    ('ix_policy_acknowledgement_policy_version_id', 'policy_acknowledgement', ['policy_version_id']),
    ('ix_policy_acknowledgement_user_id', 'policy_acknowledgement', ['user_id']),

    # --- training.py ---
    ('ix_course_assignment_course_id', 'course_assignment', ['course_id']),
    ('ix_course_assignment_user_id', 'course_assignment', ['user_id']),
    ('ix_training_session_assignment_id', 'training_session', ['assignment_id']),

    # --- bcdr.py ---
    ('ix_bcdr_test_log_plan_id', 'bcdr_test_log', ['plan_id']),
    ('ix_bcdr_test_log_assignee_id', 'bcdr_test_log', ['assignee_id']),
    ('ix_bcdr_test_log_status', 'bcdr_test_log', ['status']),

    # --- contracts.py ---
    ('ix_contract_supplier_id', 'contract', ['supplier_id']),
    ('ix_contract_status', 'contract', ['status']),
    ('ix_contract_item_contract_id', 'contract_item', ['contract_id']),

    # --- configuration.py ---
    ('ix_configuration_service_id', 'configuration', ['service_id']),
    ('ix_configuration_software_id', 'configuration', ['software_id']),
    ('ix_configuration_license_id', 'configuration', ['license_id']),
    ('ix_configuration_asset_id', 'configuration', ['asset_id']),
    ('ix_configuration_version_configuration_id', 'configuration_version', ['configuration_id']),
    ('ix_configuration_version_created_by_id', 'configuration_version', ['created_by_id']),

    # --- services.py ---
    ('ix_business_service_owner_id', 'business_service', ['owner_id']),
    ('ix_business_service_cost_center_id', 'business_service', ['cost_center_id']),
    ('ix_business_service_status', 'business_service', ['status']),
    ('ix_service_component_service_id', 'service_component', ['service_id']),

    # --- credentials.py ---
    ('ix_credential_secret_credential_id', 'credential_secret', ['credential_id']),

    # --- certificates.py ---
    ('ix_certificate_version_certificate_id', 'certificate_version', ['certificate_id']),
    ('ix_certificate_version_is_active', 'certificate_version', ['is_active']),

    # --- uar.py ---
    ('ix_uar_execution_is_archived', 'uar_execution', ['is_archived']),
    ('ix_uar_comparison_execution_id', 'uar_comparison', ['execution_id']),
    ('ix_uar_finding_execution_id', 'uar_finding', ['execution_id']),
    ('ix_uar_finding_assigned_to_id', 'uar_finding', ['assigned_to_id']),
    ('ix_uar_finding_security_incident_id', 'uar_finding', ['security_incident_id']),
    ('ix_uar_finding_status', 'uar_finding', ['status']),

    # --- hiring.py ---
    ('ix_hiring_candidate_stage_id', 'hiring_candidate', ['stage_id']),

    # --- core.py ---
    ('ix_tag_is_archived', 'tag', ['is_archived']),
    ('ix_link_software_id', 'link', ['software_id']),
    ('ix_documentation_software_id', 'documentation', ['software_id']),
    ('ix_custom_field_value_field_definition_id', 'custom_field_value', ['field_definition_id']),

    # --- permissions.py ---
    ('ix_permission_module_id', 'permission', ['module_id']),
    ('ix_permission_user_id', 'permission', ['user_id']),
    ('ix_permission_group_id', 'permission', ['group_id']),

    # --- notifications.py ---
    ('ix_notification_preference_template_id', 'notification_preference', ['template_id']),

    # --- finance.py ---
    ('ix_budget_is_archived', 'budget', ['is_archived']),
]


def upgrade():
    conn = op.get_bind()
    for name, table, columns in INDEXES:
        cols = ', '.join(columns)
        # IF NOT EXISTS prevents failure if index already exists
        # The entire statement is a no-op if table doesn't exist (caught by DO block)
        conn.execute(text(
            f"DO $$ BEGIN "
            f"CREATE INDEX IF NOT EXISTS {name} ON \"{table}\" ({cols}); "
            f"EXCEPTION WHEN OTHERS THEN NULL; END $$;"
        ))


def downgrade():
    conn = op.get_bind()
    for name, _, _ in reversed(INDEXES):
        conn.execute(text(f"DROP INDEX IF EXISTS {name};"))
