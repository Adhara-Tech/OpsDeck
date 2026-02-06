"""
Extended tests for Security Activities module.
Tests for features not covered in test_activities.py:
- Execution detail and edit routes
- Attachments on ActivityExecution
- Compliance links on SecurityActivity
"""
import io
from datetime import date
from src.models import (
    SecurityActivity, ActivityExecution, User, Framework, FrameworkControl
)
from src import db
from src.utils.timezone_helper import today


def test_execution_detail_route(auth_client, app):
    """Test that the execution detail page loads correctly."""
    with app.app_context():
        # Setup
        activity = SecurityActivity(name='Test Activity')
        db.session.add(activity)
        user = User.query.first()
        db.session.commit()
        
        execution = ActivityExecution(
            activity_id=activity.id,
            executor_id=user.id,
            execution_date=today(),
            status='success',
            outcome_notes='Test execution notes'
        )
        db.session.add(execution)
        db.session.commit()
        execution_id = execution.id
    
    # Action
    response = auth_client.get(f'/security/activities/execution/{execution_id}')
    
    # Verify
    assert response.status_code == 200
    assert b'Test Activity' in response.data
    assert b'Test execution notes' in response.data
    assert b'success' in response.data


def test_edit_execution_route(auth_client, app):
    """Test editing an existing execution via the edit route."""
    with app.app_context():
        # Setup
        activity = SecurityActivity(name='Editable Execution')
        db.session.add(activity)
        user = User.query.first()
        db.session.commit()
        
        execution = ActivityExecution(
            activity_id=activity.id,
            executor_id=user.id,
            execution_date=date(2023, 6, 1),
            status='in_progress',
            outcome_notes='Initial notes'
        )
        db.session.add(execution)
        db.session.commit()
        execution_id = execution.id
        user_id = user.id
    
    # Action: Update execution
    data = {
        'executor_id': user_id,
        'execution_date': '2023-06-15',
        'status': 'success',
        'outcome_notes': 'Updated notes after completion'
    }
    response = auth_client.post(
        f'/security/activities/execution/{execution_id}/edit',
        data=data,
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'Execution updated successfully' in response.data
    assert b'Updated notes after completion' in response.data
    
    # Verify database changes
    with app.app_context():
        updated = db.session.get(ActivityExecution,execution_id)
        assert updated.status == 'success'
        assert updated.execution_date == date(2023, 6, 15)
        assert updated.outcome_notes == 'Updated notes after completion'


def test_execution_attachments(auth_client, app):
    """Test file upload on ActivityExecution via edit route."""
    with app.app_context():
        # Setup
        activity = SecurityActivity(name='Activity with Evidence')
        db.session.add(activity)
        user = User.query.first()
        db.session.commit()
        
        execution = ActivityExecution(
            activity_id=activity.id,
            executor_id=user.id,
            execution_date=today(),
            status='success'
        )
        db.session.add(execution)
        db.session.commit()
        execution_id = execution.id
        user_id = user.id
    
    # Action: Upload file via edit route
    data = {
        'executor_id': user_id,
        'execution_date': today().strftime('%Y-%m-%d'),
        'status': 'success',
        'outcome_notes': 'Completed with evidence'
    }
    
    # Create a fake file
    file_data = io.BytesIO(b"Test evidence file content")
    data['files'] = (file_data, 'evidence.pdf')
    
    response = auth_client.post(
        f'/security/activities/execution/{execution_id}/edit',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    
    # Verify attachment was created
    with app.app_context():
        execution = db.session.get(ActivityExecution,execution_id)
        attachments_list = list(execution.attachments)
        assert len(attachments_list) > 0
        attachment = attachments_list[0]
        assert attachment.linkable_type == 'ActivityExecution'
        assert attachment.linkable_id == execution_id
        assert 'evidence' in attachment.filename.lower() or attachment.filename == 'evidence.pdf'


def test_activity_compliance_links(auth_client, app):
    """Test that SecurityActivity has compliance links working correctly."""
    with app.app_context():
        # Setup: Create a framework and control
        framework = Framework(name='ISO 27001', is_custom=False)
        db.session.add(framework)
        db.session.commit()
        
        control = FrameworkControl(
            framework_id=framework.id,
            control_id='A.5.1',
            name='Access Control Policy',
            description='Test control'
        )
        db.session.add(control)
        db.session.commit()
        
        # Create an activity
        activity = SecurityActivity(
            name='Access Review Activity',
            frequency='monthly'
        )
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id
        control_id = control.id
    
    # Action: Create a ComplianceLink to the activity
    with app.app_context():
        from src.models.security import ComplianceLink
        
        link = ComplianceLink(
            framework_control_id=control_id,
            linkable_type='SecurityActivity',
            linkable_id=activity_id,
            description='This activity demonstrates compliance with access control'
        )
        db.session.add(link)
        db.session.commit()
    
    # Verify: Activity has compliance links
    with app.app_context():
        activity = db.session.get(SecurityActivity,activity_id)
        assert activity.compliance_links.count() == 1
        
        link = activity.compliance_links.first()
        assert link.linkable_type == 'SecurityActivity'
        assert link.linkable_id == activity_id
        assert link.framework_control.control_id == 'A.5.1'
        assert 'access control' in link.description.lower()
