import pytest
from src.models import RiskAssessment, RiskAssessmentItem, Risk, ThreatType, User
from src.models import db

@pytest.fixture
def admin_user_id(app, auth_client):
    """Fetch the ID of the admin user created by auth_client."""
    with app.app_context():
        user = User.query.filter_by(email='admin@test.com').first()
        return user.id

def test_create_assessment_snapshot(auth_client, app, admin_user_id):
    """Test creating an assessment and importing open risks."""
    # auth_client is already logged in as admin@test.com
    
    with app.app_context():
        # Create a Threat Type
        threat = ThreatType(name="Phishing", category="Adversarial")
        db.session.add(threat)
        db.session.commit()

        # Create a Risk
        risk = Risk(
            risk_description="Test Risk",
            status="Open",
            inherent_impact=5, inherent_likelihood=5,
            residual_impact=4, residual_likelihood=4,
            threat_type_id=threat.id,
            owner_id=admin_user_id
        )
        db.session.add(risk)
        db.session.commit()

        # Create Assessment importing risks
        response = auth_client.post('/risk-assessments/new', data={
            'name': 'Test Assessment',
            'include_risks': 'yes'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"Test Assessment" in response.data
        assert b"Assessment created with 1 snapshot items." in response.data
        
        # Verify DB
        assessment = RiskAssessment.query.filter_by(name='Test Assessment').first()
        assert assessment is not None
        assert len(assessment.items) == 1
        item = assessment.items[0]
        assert item.risk_description == "Test Risk"
        assert item.threat_type_name == "Phishing"
        assert item.residual_score == 16 # (4*4)

def test_edit_assessment_item_isolation(auth_client, app, admin_user_id):
    """Test that editing an assessment item DOES NOT change the original risk."""
    
    with app.app_context():
        # Setup Risk and Assessment
        threat = ThreatType(name="Malware", category="Adversarial")
        db.session.add(threat)
        db.session.commit()
        
        orig_risk = Risk(risk_description="Original", status="Open", residual_impact=5, residual_likelihood=5, threat_type_id=threat.id, owner_id=admin_user_id)
        db.session.add(orig_risk)
        db.session.commit()
        
        assessment = RiskAssessment(name="Iso Test", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        item = RiskAssessmentItem(assessment_id=assessment.id, original_risk_id=orig_risk.id, risk_description="Original", residual_impact=5, residual_likelihood=5)
        db.session.add(item)
        db.session.commit()
        
        # Edit the ITEM
        response = auth_client.post(f'/risk-assessments/item/{item.id}/edit', data={
            'risk_description': 'Modified in Assessment',
            'residual_impact': 2,
            'residual_likelihood': 2,
            'mitigation_notes': ' mitigation'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify Isolation
        db.session.refresh(item)
        db.session.refresh(orig_risk)
        
        assert item.residual_score == 4 # (2*2)
        assert orig_risk.residual_score == 25 # (5*5) # Should remain unchanged

def test_lock_assessment(auth_client, app):
    """Test locking an assessment."""
    
    with app.app_context():
        assessment = RiskAssessment(name="To Lock", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        response = auth_client.post(f'/risk-assessments/{assessment.id}/lock', follow_redirects=True)
        assert response.status_code == 200
        
        db.session.refresh(assessment)
        assert assessment.status == 'Locked'
        assert assessment.locked_at is not None

def test_pdf_export_route(auth_client, app):
    """Test PDF export route returns PDF content."""
    
    with app.app_context():
        assessment = RiskAssessment(name="PDF Test", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        response = auth_client.get(f'/risk-assessments/{assessment.id}/pdf')
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'


def test_lock_assessment_with_sync(auth_client, app, admin_user_id):
    """Test locking an assessment WITH sync_to_live updates live risks."""
    
    with app.app_context():
        # Create a live risk with high residual score
        live_risk = Risk(
            risk_description="Live Risk", 
            status="Identified", 
            residual_impact=5, 
            residual_likelihood=5,
            owner_id=admin_user_id
        )
        db.session.add(live_risk)
        db.session.commit()
        live_risk_id = live_risk.id
        
        # Create assessment with item linked to the live risk
        assessment = RiskAssessment(name="Sync Test", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        # Assessment item has lower residual scores
        item = RiskAssessmentItem(
            assessment_id=assessment.id,
            original_risk_id=live_risk_id,
            risk_description="Live Risk",
            residual_impact=2,
            residual_likelihood=2
        )
        db.session.add(item)
        db.session.commit()
        assessment_id = assessment.id
        
        # Lock WITH sync_to_live
        response = auth_client.post(
            f'/risk-assessments/{assessment_id}/lock',
            data={'sync_to_live': 'on'},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"1 live risk(s) updated" in response.data
        
        # Verify live risk was updated
        updated_risk = db.session.get(Risk, live_risk_id)
        assert updated_risk.residual_impact == 2
        assert updated_risk.residual_likelihood == 2
        assert updated_risk.residual_score == 4


def test_lock_assessment_without_sync(auth_client, app, admin_user_id):
    """Test locking an assessment WITHOUT sync_to_live does NOT update live risks."""
    
    with app.app_context():
        # Create a live risk
        live_risk = Risk(
            risk_description="Unchanged Risk", 
            status="Identified", 
            residual_impact=5, 
            residual_likelihood=5,
            owner_id=admin_user_id
        )
        db.session.add(live_risk)
        db.session.commit()
        live_risk_id = live_risk.id
        
        # Create assessment with item linked to the live risk
        assessment = RiskAssessment(name="No Sync Test", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        item = RiskAssessmentItem(
            assessment_id=assessment.id,
            original_risk_id=live_risk_id,
            risk_description="Unchanged Risk",
            residual_impact=1,
            residual_likelihood=1
        )
        db.session.add(item)
        db.session.commit()
        assessment_id = assessment.id
        
        # Lock WITHOUT sync_to_live (checkbox not checked)
        response = auth_client.post(
            f'/risk-assessments/{assessment_id}/lock',
            data={},  # No sync_to_live
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"updated" not in response.data.lower()
        
        # Verify live risk was NOT updated
        unchanged_risk = db.session.get(Risk, live_risk_id)
        assert unchanged_risk.residual_impact == 5
        assert unchanged_risk.residual_likelihood == 5
        assert unchanged_risk.residual_score == 25


def test_status_change_on_sync(auth_client, app, admin_user_id):
    """Test that sync updates risk status based on residual score thresholds."""
    
    with app.app_context():
        # Create a live risk that will be mitigated (score < 5)
        mitigate_risk = Risk(
            risk_description="To Mitigate", 
            status="In Treatment", 
            residual_impact=5, 
            residual_likelihood=5,
            owner_id=admin_user_id
        )
        db.session.add(mitigate_risk)
        
        # Create a live risk that will stay in treatment (score >= 15)
        treatment_risk = Risk(
            risk_description="Stay Treatment", 
            status="Identified", 
            residual_impact=1, 
            residual_likelihood=1,
            owner_id=admin_user_id
        )
        db.session.add(treatment_risk)
        db.session.commit()
        
        mitigate_id = mitigate_risk.id
        treatment_id = treatment_risk.id
        
        # Create assessment
        assessment = RiskAssessment(name="Status Test", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        # Item that reduces score below 5 -> Mitigated
        item1 = RiskAssessmentItem(
            assessment_id=assessment.id,
            original_risk_id=mitigate_id,
            risk_description="To Mitigate",
            residual_impact=1,
            residual_likelihood=1  # Score = 1 < 5
        )
        db.session.add(item1)
        
        # Item that raises score above 15 -> In Treatment
        item2 = RiskAssessmentItem(
            assessment_id=assessment.id,
            original_risk_id=treatment_id,
            risk_description="Stay Treatment",
            residual_impact=4,
            residual_likelihood=4  # Score = 16 >= 15
        )
        db.session.add(item2)
        db.session.commit()
        assessment_id = assessment.id
        
        # Lock with sync
        response = auth_client.post(
            f'/risk-assessments/{assessment_id}/lock',
            data={'sync_to_live': 'on'},
            follow_redirects=True
        )
        assert response.status_code == 200
        
        # Verify statuses were updated
        mitigated = db.session.get(Risk, mitigate_id)
        assert mitigated.status == 'Mitigated'
        
        in_treatment = db.session.get(Risk, treatment_id)
        assert in_treatment.status == 'In Treatment'


def test_assessment_history_visible_on_risk(auth_client, app, admin_user_id):
    """Test that the Assessment History tab shows locked assessment data."""
    
    with app.app_context():
        # Create a live risk
        live_risk = Risk(
            risk_description="History Test Risk", 
            status="Identified", 
            residual_impact=4, 
            residual_likelihood=4,
            owner_id=admin_user_id
        )
        db.session.add(live_risk)
        db.session.commit()
        live_risk_id = live_risk.id
        
        # Create and lock an assessment
        assessment = RiskAssessment(name="History Assessment", status="Draft")
        db.session.add(assessment)
        db.session.commit()
        
        item = RiskAssessmentItem(
            assessment_id=assessment.id,
            original_risk_id=live_risk_id,
            risk_description="History Test Risk",
            residual_impact=3,
            residual_likelihood=3
        )
        db.session.add(item)
        db.session.commit()
        
        # Lock the assessment
        auth_client.post(f'/risk-assessments/{assessment.id}/lock', data={})
        
        # View the risk detail page
        response = auth_client.get(f'/risk/{live_risk_id}')
        assert response.status_code == 200
        assert b"Assessment History" in response.data
        assert b"History Assessment" in response.data
