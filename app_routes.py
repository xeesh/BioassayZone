from flask import render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Assay, ZoneMeasurement, AssayStatistics, AuditLog, User
from auth import log_audit_event, require_permission
from app import app

@app.route('/view_assay/<assay_id>')
@login_required
def view_assay(assay_id):
    """View detailed assay information"""
    assay = Assay.query.get_or_404(assay_id)
    
    # Check permissions - users can only view their own assays unless they're supervisors
    if assay.analyst_id != current_user.id and not current_user.has_permission('view_all_assays'):
        flash('You do not have permission to view this assay.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('view_assay.html', assay=assay, user=current_user)

@app.route('/my_assays')
@login_required
def my_assays():
    """List user's assays"""
    if current_user.has_permission('view_all_assays'):
        assays = Assay.query.order_by(Assay.created_at.desc()).all()
    else:
        assays = Assay.query.filter_by(analyst_id=current_user.id).order_by(Assay.created_at.desc()).all()
    
    return render_template('my_assays.html', assays=assays, user=current_user)

@app.route('/manage_users')
@login_required
@require_permission('manage_users')
def manage_users():
    """User management for administrators"""
    users = User.query.all()
    return render_template('admin/users.html', users=users, user=current_user)

@app.route('/audit_log')
@login_required
@require_permission('view_audit_logs')
def admin_audit_log():
    """System-wide audit log for administrators"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    audit_entries = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/audit_log.html', audit_entries=audit_entries, user=current_user)