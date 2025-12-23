import pytest
from src.models import db, ComplianceAudit, AuditControlItem, Framework, FrameworkControl, Attachment
from src.models.auth import User

def test_create_audit_snapshot(auth_client, app):
    """
    Test 1: Test de Modelo (Snapshot Logic)
    Verifica que al crear una auditoría se copian correctamente los controles del framework.
    """
    # Setup: Crear Framework y Controles
    with app.app_context():
        fw = Framework(name='Framework Test Snapshot', is_custom=True)
        c1 = FrameworkControl(control_id='C.1', name='Control 1', description='Desc 1')
        c2 = FrameworkControl(control_id='C.2', name='Control 2', description='Desc 2')
        fw.framework_controls.extend([c1, c2])
        
        auditor = User(name='Auditor', email='auditor@test.com', role='admin')
        auditor.set_password('password')
        
        db.session.add(fw)
        db.session.add(auditor)
        db.session.commit()
        
        fw_id = fw.id
        auditor_id = auditor.id

    # Acción: Crear Snapshot (llamando al método del modelo directamente o vía ruta si se prefiere, 
    # pero el requisito dice "Llama a ComplianceAudit.create_snapshot()")
    with app.app_context():
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw_id,
            name='Auditoría Q1',
            auditor_id=auditor_id
        )
        audit_id = audit.id

    # Verificaciones
    with app.app_context():
        audit = ComplianceAudit.query.get(audit_id)
        assert audit is not None
        assert audit.name == 'Auditoría Q1'
        
        # Se crean exactamente 2 AuditControlItem
        assert audit.audit_items.count() == 2
        
        # Verificar copia correcta de datos
        items = audit.audit_items.all()
        c1_item = next((i for i in items if i.control_code == 'C.1'), None)
        c2_item = next((i for i in items if i.control_code == 'C.2'), None)
        
        assert c1_item is not None
        assert c1_item.control_title == 'Control 1'
        assert c1_item.control_description == 'Desc 1'
        assert c1_item.is_applicable is True # Por defecto True
        
        assert c2_item is not None
        assert c2_item.control_title == 'Control 2'

def test_update_audit_item_soa(auth_client, app):
    """
    Test 2: Test de SOA y Estado
    Verifica la actualización de items (is_applicable, justification).
    """
    # Setup: Crear Auditoría con 1 item
    with app.app_context():
        fw = Framework(name='Framework SOA', is_custom=True)
        c1 = FrameworkControl(control_id='SOA.1', name='Control SOA')
        fw.framework_controls.append(c1)
        
        auditor = User.query.filter_by(email='admin@test.com').first() # Usar el admin del fixture
        if not auditor:
             auditor = User(name='Admin', email='admin@test.com', role='admin')
             auditor.set_password('password')
             db.session.add(auditor)
             db.session.commit()

        db.session.add(fw)
        db.session.commit()
        
        audit = ComplianceAudit.create_snapshot(fw.id, 'Auditoría SOA', auditor.id)
        item_id = audit.audit_items.first().id

    # Acción: Modificar item
    with app.app_context():
        item = AuditControlItem.query.get(item_id)
        item.is_applicable = False
        item.justification = 'No aplica por X razón'
        db.session.commit()

    # Verificación: Recargar y comprobar
    with app.app_context():
        item = AuditControlItem.query.get(item_id)
        assert item.is_applicable is False
        assert item.justification == 'No aplica por X razón'

def test_audit_item_attachment(auth_client, app):
    """
    Test 3: Test de Integración de Evidencias
    Verifica que se pueden adjuntar archivos a un AuditControlItem (polimorfismo).
    """
    # Setup: Crear Item
    with app.app_context():
        # Necesitamos una auditoría padre para crear un item válido (FKs)
        fw = Framework(name='Framework Attach', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        auditor = User.query.first()
        audit = ComplianceAudit.create_snapshot(fw.id, 'Auditoría Attach', auditor.id)
        
        # Crear un item manualmente o usar uno del snapshot (el snapshot crea items si hay controles, 
        # pero aquí el framework no tiene controles, así que creamos uno manual para el test o añadimos control al fw)
        # Mejor añadimos control al fw antes del snapshot para ser consistentes
        c1 = FrameworkControl(control_id='ATT.1', name='Control Attach')
        fw.framework_controls.append(c1)
        db.session.commit()
        
        # Re-crear snapshot para tener el item
        audit = ComplianceAudit.create_snapshot(fw.id, 'Auditoría Attach 2', auditor.id)
        item = audit.audit_items.first()
        item_id = item.id

    # Acción: Crear Attachment vinculado
    with app.app_context():
        # Simular un archivo adjunto
        attachment = Attachment(
            filename='evidencia.pdf',
            secure_filename='evidencia_12345.pdf',
            linkable_type='AuditControlItem',
            linkable_id=item_id
        )
        db.session.add(attachment)
        db.session.commit()

    # Verificación
    with app.app_context():
        item = AuditControlItem.query.get(item_id)
        assert item.attachments.count() == 1
        att = item.attachments.first()
        assert att.filename == 'evidencia.pdf'
        assert att.linkable_type == 'AuditControlItem'

def test_delete_audit_cascades(auth_client, app):
    """
    Test 4: Test de Cascada (Borrado)
    Verifica que al borrar una auditoría se borran sus items.
    """
    # Setup: Crear Auditoría con items
    with app.app_context():
        fw = Framework(name='Framework Cascade', is_custom=True)
        fw.framework_controls.append(FrameworkControl(control_id='DEL.1', name='C1'))
        fw.framework_controls.append(FrameworkControl(control_id='DEL.2', name='C2'))
        db.session.add(fw)
        db.session.commit()
        
        auditor = User.query.first()
        audit = ComplianceAudit.create_snapshot(fw.id, 'Auditoría Delete', auditor.id)
        audit_id = audit.id
        
        assert AuditControlItem.query.filter_by(audit_id=audit_id).count() == 2

    # Acción: Borrar Auditoría
    with app.app_context():
        audit = ComplianceAudit.query.get(audit_id)
        db.session.delete(audit)
        db.session.commit()

    # Verificación
    with app.app_context():
        assert ComplianceAudit.query.get(audit_id) is None
        assert AuditControlItem.query.filter_by(audit_id=audit_id).count() == 0
