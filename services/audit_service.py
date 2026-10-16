from flask import request, session
from models import db, AuditLog

def log_action(action, application_id=None, details=None, user_id=None, user_role=None):
    """
    Log an event into the audit trail.
    Safe to call with or without an active request context.
    """
    try:
        if user_id is None and session and 'user_id' in session:
            user_id = session.get('user_id')
        if user_role is None and session and 'role' in session:
            user_role = session.get('role')
            
        ip = None
        if request:
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            
        audit_entry = AuditLog(
            user_id=user_id,
            user_role=user_role,
            action=action,
            application_id=application_id,
            details=details,
            ip_address=ip
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        # Don't fail the primary transaction if logging encounters an issue
        try:
            db.session.rollback()
        except Exception:
            pass
