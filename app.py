import os
from datetime import datetime, date
from flask import Flask, render_template
from config import Config
from models import db
from database import init_db
from routes.auth import auth_bp
from routes.applicant import applicant_bp
from routes.officer import officer_bp
from routes.admin import admin_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(applicant_bp)
    app.register_blueprint(officer_bp)
    app.register_blueprint(admin_bp)

    # Custom Jinja Template Filters
    @app.template_filter('currency')
    def currency_filter(val):
        if val is None:
            return "₹0.00"
        try:
            return f"₹{float(val):,.2f}"
        except (ValueError, TypeError):
            return str(val)

    @app.template_filter('format_date')
    def format_date_filter(val, fmt='%d %b %Y'):
        if not val:
            return "N/A"
        if isinstance(val, (datetime, date)):
            return val.strftime(fmt)
        try:
            dt = datetime.strptime(str(val), '%Y-%m-%d')
            return dt.strftime(fmt)
        except Exception:
            return str(val)

    @app.template_filter('status_class')
    def status_class_filter(status):
        mapping = {
            'meets_requirements': 'badge-success',
            'PASS': 'badge-success',
            'approved': 'badge-success',
            'fully_verified': 'badge-success',
            'verified': 'badge-success',
            'does_not_meet': 'badge-danger',
            'FAIL': 'badge-danger',
            'rejected': 'badge-danger',
            'discrepancy_detected': 'badge-danger',
            'pending_verification': 'badge-warning',
            'PENDING_VERIFICATION': 'badge-warning',
            'pending': 'badge-warning',
            'partially_verified': 'badge-warning',
            'manual_review': 'badge-info',
            'MANUAL_REVIEW': 'badge-info',
            'submitted': 'badge-primary',
            'NOT_APPLICABLE': 'badge-secondary'
        }
        return mapping.get(status, 'badge-secondary')

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    @app.errorhandler(413)
    def file_too_large(error):
        return render_template('error.html', message="Uploaded file exceeds the maximum allowed 16MB limit."), 413

    # Initialize database and demo data
    init_db(app)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
