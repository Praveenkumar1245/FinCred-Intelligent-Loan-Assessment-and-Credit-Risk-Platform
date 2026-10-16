from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Applicant
from services.audit_service import log_action

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            role = session.get('role')
            if role not in allowed_roles:
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('applicant.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('applicant.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash("This account is currently deactivated. Please contact an administrator.", "danger")
                return render_template('login.html')

            # Set session
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_action("USER_LOGIN", user_id=user.id, user_role=user.role, details=f"User {user.username} logged in successfully.")
            flash(f"Welcome back, {user.full_name}!", "success")
            
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('applicant.dashboard'))
        else:
            flash("Invalid username/email or password. Please try again.", "danger")
            log_action("FAILED_LOGIN_ATTEMPT", details=f"Failed login attempt for username: {username}")

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('applicant.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validations
        if not username or not email or not full_name or not password:
            flash("All fields are mandatory.", "danger")
            return render_template('login.html', show_register=True)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('login.html', show_register=True)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('login.html', show_register=True)

        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose a different username.", "warning")
            return render_template('login.html', show_register=True)

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please log in.", "warning")
            return render_template('login.html', show_register=True)

        new_user = User(
            username=username,
            email=email,
            full_name=full_name,
            role='applicant'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # Create basic applicant profile
        applicant_profile = Applicant(
            user_id=new_user.id,
            full_name=full_name,
            email=email
        )
        db.session.add(applicant_profile)
        db.session.commit()

        log_action("USER_REGISTERED", user_id=new_user.id, user_role='applicant', details=f"New applicant {username} registered.")
        flash("Registration successful! You may now log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('login.html', show_register=True)

@auth_bp.route('/logout')
def logout():
    uid = session.get('user_id')
    role = session.get('role')
    log_action("USER_LOGOUT", user_id=uid, user_role=role, details="User logged out.")
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('auth.login'))
