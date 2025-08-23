from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, AuditLog, db
from datetime import datetime, timedelta
import re
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_password_strength(password):
    """Validate password meets security requirements"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    
    return errors

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Secure login with audit logging"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            log_security_event('LOGIN_ATTEMPT_FAILED', f'Empty credentials for username: {username}')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username, active=True).first()
        
        if user and user.check_password(password):
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                flash(f'Account locked until {user.locked_until.strftime("%Y-%m-%d %H:%M")}', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=True)
            
            # Log successful login
            log_audit_event(
                user_id=user.id,
                action='USER_LOGIN',
                description=f'User {user.username} logged in successfully'
            )
            
            # Check if password needs to be changed (older than 90 days)
            if user.password_changed_at < datetime.utcnow() - timedelta(days=90):
                flash('Your password has expired. Please change it.', 'warning')
                return redirect(url_for('auth.change_password'))
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            log_security_event('LOGIN_ATTEMPT_FAILED', f'Invalid credentials for username: {username}')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Secure logout with audit logging"""
    log_audit_event(
        user_id=current_user.id,
        action='USER_LOGOUT',
        description=f'User {current_user.username} logged out'
    )
    
    logout_user()
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Secure password change with history checking"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('auth/change_password.html')
        
        password_errors = validate_password_strength(new_password)
        if password_errors:
            for error in password_errors:
                flash(error, 'error')
            return render_template('auth/change_password.html')
        
        # Check password history
        if not current_user.can_reuse_password(new_password):
            flash('Password has been used recently. Please choose a different password.', 'error')
            return render_template('auth/change_password.html')
        
        # Set new password
        current_user.set_password(new_password)
        db.session.commit()
        
        # Log password change
        log_audit_event(
            user_id=current_user.id,
            action='PASSWORD_CHANGED',
            description=f'User {current_user.username} changed password'
        )
        
        flash('Password changed successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('auth/change_password.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (admin only in production)"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'analyst')
        
        # Validate input
        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        # Validate password
        password_errors = validate_password_strength(password)
        if password_errors:
            for error in password_errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Create user
        user = User(
            username=username,
            email=email,
            role=role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log user creation
        log_audit_event(
            user_id=user.id,
            action='USER_CREATED',
            description=f'New user {username} registered with role {role}'
        )
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

def log_audit_event(user_id=None, action='', description='', entity_type=None, entity_id=None, old_values=None, new_values=None):
    """Log audit events for compliance"""
    try:
        audit_entry = AuditLog(
            user_id=user_id or (current_user.id if current_user.is_authenticated else None),
            action=action,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            session_id=session.get('session_id') if session else None
        )
        
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        # In production, this should use proper logging
        print(f"Failed to log audit event: {e}")

def log_security_event(event_type, description):
    """Log security-related events"""
    log_audit_event(
        action=event_type,
        description=description,
        entity_type='security'
    )

def require_permission(permission):
    """Decorator to check user permissions"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                flash('Insufficient permissions for this action', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator