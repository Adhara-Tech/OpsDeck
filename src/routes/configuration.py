from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from .main import login_required
from ..extensions import db
from ..models.configuration import Configuration, ConfigurationVersion
from ..models import User
from ..utils.differ import get_semantic_diff
import json

configuration_bp = Blueprint('configuration', __name__)

@configuration_bp.route('/')
@login_required
def index():
    configurations = Configuration.query.all()
    # Simple list view
    return render_template('configuration/index.html', configurations=configurations)

@configuration_bp.route('/<int:id>')
@login_required
def detail(id):
    config = Configuration.query.get_or_404(id)
    latest = config.latest_version
    
    # If no version exists, start with empty structure
    if not latest:
        data = {}
        version_number = 0
    else:
        data = latest.data
        version_number = latest.version_number
        
    return render_template('configuration/detail.html', 
                           configuration=config, 
                           data=data, 
                           version_number=version_number,
                           latest_version=latest)

@configuration_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        config = Configuration(
            name=name,
            description=description,
            owner_id=session['user_id'],
            owner_type='User'
        )
        db.session.add(config)
        db.session.commit()
        
        # Create initial empty version or template?
        # Let's create an empty version 1
        initial_version = ConfigurationVersion(
            configuration_id=config.id,
            version_number=1,
            data={},
            created_by_id=session['user_id'],
            commit_message="Initial empty configuration"
        )
        db.session.add(initial_version)
        db.session.commit()
        
        flash('Configuration created', 'success')
        return redirect(url_for('configuration.detail', id=config.id))
        
    return render_template('configuration/new.html')

@configuration_bp.route('/<int:id>/snapshot', methods=['POST'])
@login_required
def snapshot(id):
    config = Configuration.query.get_or_404(id)
    
    # Parse the JSON form data. 
    # For now, let's assume the frontend sends a 'config_data' field with JSON string
    # or we construct it.
    
    try:
        raw_data = request.form.get('config_data')
        if not raw_data:
            flash('No data provided', 'error')
            return redirect(url_for('configuration.detail', id=id))
            
        data = json.loads(raw_data)
        commit_message = request.form.get('commit_message', 'Updated configuration')
        
        latest = config.latest_version
        new_version_number = (latest.version_number + 1) if latest else 1
        
        version = ConfigurationVersion(
            configuration_id=config.id,
            version_number=new_version_number,
            data=data,
            created_by_id=session['user_id'],
            commit_message=commit_message
        )
        db.session.add(version)
        db.session.commit()
        
        flash(f'Snapshot v{new_version_number} saved.', 'success')
        
    except json.JSONDecodeError:
        flash('Invalid JSON', 'error')
    except Exception as e:
        flash(f'Error saving snapshot: {str(e)}', 'error')
        
    return redirect(url_for('configuration.detail', id=id))

@configuration_bp.route('/<int:id>/compare')
@login_required
def compare(id):
    config = Configuration.query.get_or_404(id)
    
    v1_id = request.args.get('v1', type=int)
    v2_id = request.args.get('v2', type=int)
    
    if not v1_id or not v2_id:
        # Default to comparing latest with previous
        latest = config.latest_version
        if latest and latest.version_number > 1:
            v2 = latest
            v1 = ConfigurationVersion.query.filter_by(configuration_id=id, version_number=latest.version_number - 1).first()
        else:
            flash('Not enough versions to compare', 'warning')
            return redirect(url_for('configuration.detail', id=id))
    else:
        v1 = ConfigurationVersion.query.get_or_404(v1_id)
        v2 = ConfigurationVersion.query.get_or_404(v2_id)
        
    diff = get_semantic_diff(v1.data, v2.data)
    
    return render_template('configuration/compare.html', 
                           configuration=config,
                           v1=v1,
                           v2=v2,
                           diff=diff)

@configuration_bp.route('/<int:id>/history')
@login_required
def history(id):
    config = Configuration.query.get_or_404(id)
    versions = config.versions.order_by(ConfigurationVersion.version_number.desc()).all()
    return render_template('configuration/history.html', configuration=config, versions=versions)
