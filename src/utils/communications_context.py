"""
Communications Context Factory

Builds context dictionaries for Jinja2 template rendering based on
the target process type.
"""
from datetime import datetime
from ..models.onboarding import OnboardingProcess, OffboardingProcess


def get_template_context(scheduled_comm):
    """
    Build context dict for Jinja2 template rendering based on target_type.
    
    Args:
        scheduled_comm: ScheduledCommunication instance
    
    Returns:
        dict: Context variables for Jinja2 template rendering
    """
    context = {
        'today': datetime.utcnow().date(),
    }
    
    if scheduled_comm.target_type == 'onboarding':
        process = OnboardingProcess.query.get(scheduled_comm.target_id)
        if process:
            context.update({
                'new_hire_name': process.new_hire_name,
                'start_date': process.start_date,
                'pack': process.pack,
            })
            
            if process.user:
                context['user'] = {
                    'name': process.user.name,
                    'email': process.user.email,
                    'job_title': process.user.job_title or '',
                }
            else:
                context['user'] = {
                    'name': process.new_hire_name,
                    'email': process.target_email or '',
                    'job_title': '',
                }
            
            if process.assigned_manager:
                context['manager'] = {
                    'name': process.assigned_manager.name,
                    'email': process.assigned_manager.email,
                }
            else:
                context['manager'] = None
            
            if process.assigned_buddy:
                context['buddy'] = {
                    'name': process.assigned_buddy.name,
                    'email': process.assigned_buddy.email,
                }
            else:
                context['buddy'] = None
                
    elif scheduled_comm.target_type == 'offboarding':
        process = OffboardingProcess.query.get(scheduled_comm.target_id)
        if process:
            context.update({
                'departure_date': process.departure_date,
            })
            
            if process.user:
                context['user'] = {
                    'name': process.user.name,
                    'email': process.user.email,
                    'job_title': process.user.job_title or '',
                }
            else:
                context['user'] = None
            
            if process.manager:
                context['manager'] = {
                    'name': process.manager.name,
                    'email': process.manager.email,
                }
            else:
                context['manager'] = None
            
            # Offboarding doesn't have buddy
            context['buddy'] = None
    
    elif scheduled_comm.target_type == 'campaign':
        # For campaigns, use the recipient_user stored in the scheduled communication
        if scheduled_comm.recipient_user:
            user = scheduled_comm.recipient_user
            context['user'] = {
                'name': user.name,
                'email': user.email,
                'job_title': user.job_title or '',
                'department': user.department or '',
            }
            # Also add manager if available
            if user.manager:
                context['manager'] = {
                    'name': user.manager.name,
                    'email': user.manager.email,
                }
            else:
                context['manager'] = None
        else:
            # Fallback to cached recipient info
            context['user'] = {
                'name': scheduled_comm.recipient_name or 'User',
                'email': scheduled_comm.recipient_email or '',
                'job_title': '',
                'department': '',
            }
            context['manager'] = None
    
    return context


def render_email_template(template_or_campaign, context):
    """
    Render an email template or campaign with the given context.
    
    Args:
        template_or_campaign: EmailTemplate or Campaign instance
        context: dict of context variables
    
    Returns:
        tuple: (subject, body_html) rendered with Jinja2
    """
    from jinja2 import UndefinedError
    from jinja2.sandbox import SandboxedEnvironment
    
    # Use sandboxed environment for security
    env = SandboxedEnvironment()
    
    try:
        # Render subject
        subject_template = env.from_string(template_or_campaign.subject)
        subject = subject_template.render(**context)
        
        # Render body
        body_template = env.from_string(template_or_campaign.body_html)
        body_html = body_template.render(**context)
        
        return subject, body_html
    except UndefinedError:
        # Log undefined variable but still render
        return template_or_campaign.subject, template_or_campaign.body_html
    except Exception as e:
        raise ValueError(f"Template rendering error: {str(e)}")

