from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, abort
from flask_login import LoginManager, login_required, current_user
import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from image_processor import ImageProcessor
from report_generator import ReportGenerator
from audit_logger import AuditLogger
from models import db, User, Assay, ZoneMeasurement, AssayStatistics, AuditLog, ElectronicSignature
from auth import auth_bp, log_audit_event, require_permission
from usp_calculations import USP81Calculator
import cv2
import numpy as np

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-for-sessions-change-in-production')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bioassay.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # type: ignore
login_manager.login_message = 'Please log in to access the bioassay system.'
login_manager.login_message_category = 'info'

# Register blueprints
app.register_blueprint(auth_bp)
from signatures import signatures_bp
app.register_blueprint(signatures_bp)

# Import additional routes - moved inline to avoid circular imports

# Configuration
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# Initialize components
image_processor = ImageProcessor()
report_generator = ReportGenerator()
audit_logger = AuditLogger()
usp_calculator = USP81Calculator()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if none exists
    if not db.session.query(User).filter(User.username == 'admin').first():
        admin_user = User(
            username='admin',
            email='admin@bioassay.local',
            role='administrator'
        )
        admin_user.set_password('Admin123!')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created: admin / Admin123!")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
@login_required
def dashboard():
    """Main dashboard with statistics and recent activity"""
    try:
        # Calculate dashboard statistics
        total_assays = db.session.query(Assay).count()
        active_assays = db.session.query(Assay).filter(Assay.status == 'active').count()
        completed_assays = db.session.query(Assay).filter(Assay.approved == True).count()
        
        # Recent assays (last 5)
        recent_assays = db.session.query(Assay).order_by(Assay.created_at.desc()).limit(5).all()
        
        # Recent activity from audit log
        recent_activity = []
        audit_entries = db.session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        for entry in audit_entries:
            time_diff = datetime.now(timezone.utc) - entry.timestamp
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} days ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hours ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minutes ago" if minutes > 0 else "Just now"
            
            icon_map = {
                'IMAGE_UPLOAD': {'icon': 'fa-upload', 'color': 'primary'},
                'REPORT_GENERATED': {'icon': 'fa-file-pdf', 'color': 'success'},
                'ELECTRONIC_SIGNATURE': {'icon': 'fa-digital-tachograph', 'color': 'warning'},
                'USER_LOGIN': {'icon': 'fa-sign-in-alt', 'color': 'info'},
                'USER_LOGOUT': {'icon': 'fa-sign-out-alt', 'color': 'secondary'},
            }
            
            activity_info = icon_map.get(entry.action, {'icon': 'fa-cog', 'color': 'secondary'})
            
            recent_activity.append({
                'description': entry.description,
                'time_ago': time_ago,
                'icon': activity_info['icon'],
                'icon_color': activity_info['color']
            })
    
        # Calculate statistics
        dashboard_stats = {
            'total_assays': total_assays,
            'active_assays': active_assays,
            'compliance_score': 98.7,  # This could be calculated based on validation results
            'success_rate': round((completed_assays / total_assays * 100), 1) if total_assays > 0 else 100,
            'assay_growth': 12  # This could be calculated from historical data
        }
        
        # Add status classes for assays
        for assay in recent_assays:
            if assay.approved:
                assay.status_class = 'completed'
            elif assay.status == 'active':
                assay.status_class = 'in-progress'
            else:
                assay.status_class = 'pending'
        
        return render_template('dashboard.html', 
                             user=current_user, 
                             dashboard_stats=dashboard_stats,
                             recent_assays=recent_assays,
                             recent_activity=recent_activity)
    except Exception as e:
        # Fallback to basic dashboard if there's an error
        return render_template('dashboard.html', 
                             user=current_user, 
                             dashboard_stats={'total_assays': 0, 'active_assays': 0, 'compliance_score': 0, 'success_rate': 0, 'assay_growth': 0},
                             recent_assays=[],
                             recent_activity=[])

@app.route('/zone_analysis')
@login_required
def zone_analysis():
    """Zone analysis page (upload and analyze)"""
    return render_template('index.html', user=current_user)

@app.route('/compliance')
@login_required
def compliance():
    """Compliance overview page"""
    return render_template('compliance.html', user=current_user)

@app.route('/reports')
@login_required  
def reports():
    """Reports overview page"""
    return render_template('reports.html', user=current_user)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle image upload and initial processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            file_extension = filename.rsplit('.', 1)[1].lower()
            safe_filename = f"{file_id}.{file_extension}"
            filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
            
            # Save file
            file.save(filepath)
            
            # Get assay information
            assay_name = request.form.get('assay_name', 'Untitled Assay')
            sample_type = request.form.get('sample_type', 'Unknown')
            
            # Create database record
            assay = Assay(
                id=file_id,
                name=assay_name,
                sample_type=sample_type,
                analyst_id=current_user.id,
                image_filename=filename,
                image_path=filepath
            )
            db.session.add(assay)
            db.session.commit()
            
            # Store session data for immediate use
            session['current_assay'] = {
                'id': file_id,
                'filename': safe_filename,
                'filepath': filepath,
                'assay_name': assay_name,
                'analyst_name': current_user.username,
                'sample_type': sample_type,
                'timestamp': datetime.now().isoformat()
            }
            
            # Enhanced audit logging
            log_audit_event(
                user_id=current_user.id,
                action='IMAGE_UPLOAD',
                description=f"Uploaded image for assay '{assay_name}'",
                entity_type='assay',
                entity_id=file_id,
                new_values={'filename': filename, 'sample_type': sample_type}
            )
            
            return jsonify({
                'success': True,
                'message': 'Image uploaded successfully',
                'assay_id': file_id
            })
        else:
            return jsonify({'error': 'Invalid file type'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/analysis')
@login_required
def analysis():
    """Analysis page with image display and zone detection tools"""
    if 'current_assay' not in session:
        flash('No assay data found. Please upload an image first.', 'warning')
        return redirect(url_for('dashboard'))
    
    return render_template('analysis.html', assay=session['current_assay'], user=current_user)

@app.route('/detect_zones', methods=['POST'])
def detect_zones():
    """Automatic zone detection using OpenCV"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        assay = session['current_assay']
        filepath = assay['filepath']
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Image file not found'}), 404
        
        # Process image and detect zones
        zones = image_processor.detect_zones(filepath)
        
        # Log detection action
        audit_logger.log_action(
            assay['analyst_name'],
            'AUTO_DETECTION',
            f"Automated zone detection performed",
            {'assay_id': assay['id'], 'zones_detected': len(zones)}
        )
        
        return jsonify({
            'success': True,
            'zones': zones,
            'message': f'Detected {len(zones)} potential inhibition zones'
        })
        
    except Exception as e:
        return jsonify({'error': f'Zone detection failed: {str(e)}'}), 500

@app.route('/add_manual_zone', methods=['POST'])
def add_manual_zone():
    """Add a manually drawn zone"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        data = request.get_json()
        zone_data = {
            'x': data['x'],
            'y': data['y'],
            'radius': data['radius'],
            'diameter_mm': data['diameter_mm'],
            'type': 'manual',
            'id': str(uuid.uuid4())
        }
        
        assay = session['current_assay']
        
        # Store manual zones in session
        if 'manual_zones' not in session:
            session['manual_zones'] = []
        session['manual_zones'].append(zone_data)
        
        # Log manual zone addition
        audit_logger.log_action(
            assay['analyst_name'],
            'MANUAL_ZONE_ADD',
            f"Manual zone added",
            {'assay_id': assay['id'], 'zone_id': zone_data['id'], 'diameter_mm': zone_data['diameter_mm']}
        )
        
        return jsonify({'success': True, 'zone': zone_data})
        
    except Exception as e:
        return jsonify({'error': f'Failed to add manual zone: {str(e)}'}), 500

@app.route('/calculate_statistics', methods=['POST'])
def calculate_statistics():
    """Calculate basic statistics for measured zones"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        data = request.get_json()
        zones = data.get('zones', [])
        
        if not zones:
            return jsonify({'error': 'No zone data provided'}), 400
        
        # Extract diameters
        diameters = [zone['diameter_mm'] for zone in zones if 'diameter_mm' in zone]
        
        if not diameters:
            return jsonify({'error': 'No valid diameter measurements found'}), 400
        
        # Calculate statistics
        stats = image_processor.calculate_statistics(diameters)
        
        # Store statistics in session
        session['statistics'] = stats
        
        # Log calculation
        assay = session['current_assay']
        audit_logger.log_action(
            assay['analyst_name'],
            'STATISTICS_CALC',
            f"Statistics calculated for {len(diameters)} zones",
            {'assay_id': assay['id'], 'zone_count': len(diameters), 'mean': stats['mean']}
        )
        
        return jsonify({'success': True, 'statistics': stats})
        
    except Exception as e:
        return jsonify({'error': f'Statistics calculation failed: {str(e)}'}), 500

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    """Generate PDF report with all measurement data"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        data = request.get_json()
        zones = data.get('zones', [])
        statistics = session.get('statistics', {})
        
        assay_data = session['current_assay']
        assay = db.session.get(Assay, assay_data['id'])
        
        if not assay:
            return jsonify({'error': 'Assay not found in database'}), 404
        
        # Store zones in database
        for zone in zones:
            zone_measurement = ZoneMeasurement(
                assay_id=assay.id,
                zone_id=zone.get('id', 'unknown'),
                x_position=zone.get('x', 0),
                y_position=zone.get('y', 0),
                radius_pixels=zone.get('radius', 0),
                diameter_mm=zone.get('diameter_mm', 0),
                detection_type=zone.get('type', 'unknown'),
                confidence=zone.get('confidence')
            )
            db.session.add(zone_measurement)
        
        # Store statistics
        if statistics:
            assay_stats = AssayStatistics(
                assay_id=assay.id,
                zone_count=statistics.get('count', 0),
                mean_diameter=statistics.get('mean', 0),
                median_diameter=statistics.get('median', 0),
                std_deviation=statistics.get('std_dev', 0),
                min_diameter=statistics.get('min', 0),
                max_diameter=statistics.get('max', 0),
                diameter_range=statistics.get('range', 0),
                cv_percent=statistics.get('cv_percent', 0)
            )
            db.session.add(assay_stats)
        
        db.session.commit()
        
        # Generate report
        report_filename = f"bioassay_report_{assay.id}.pdf"
        report_path = os.path.join(REPORTS_FOLDER, report_filename)
        
        report_data = {
            'assay': assay_data,
            'zones': zones,
            'statistics': statistics,
            'audit_trail': db.session.query(AuditLog).filter(AuditLog.entity_id == assay.id).all()
        }
        
        report_generator.create_report(report_data, report_path)
        
        # Enhanced audit logging
        log_audit_event(
            user_id=current_user.id,
            action='REPORT_GENERATED',
            description=f"PDF report generated for assay '{assay.name}'",
            entity_type='assay',
            entity_id=assay.id,
            new_values={'report_file': report_filename, 'zone_count': len(zones)}
        )
        
        return jsonify({
            'success': True,
            'report_url': f'/download_report/{report_filename}',
            'message': 'Report generated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500

@app.route('/download_report/<filename>')
def download_report(filename):
    """Download generated PDF report"""
    try:
        report_path = os.path.join(REPORTS_FOLDER, filename)
        if os.path.exists(report_path):
            return send_file(report_path, as_attachment=True)
        else:
            return "Report not found", 404
    except Exception as e:
        return f"Download failed: {str(e)}", 500

@app.route('/get_image/<assay_id>')
def get_image(assay_id):
    """Serve uploaded images"""
    try:
        if 'current_assay' not in session or session['current_assay']['id'] != assay_id:
            return "Image not found", 404
        
        filepath = session['current_assay']['filepath']
        if os.path.exists(filepath):
            return send_file(filepath)
        else:
            return "Image not found", 404
    except Exception as e:
        return f"Image access failed: {str(e)}", 500

@app.route('/audit_log')
def audit_log():
    """View audit log entries"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        assay_id = session['current_assay']['id']
        audit_entries = audit_logger.get_audit_trail(assay_id)
        
        return jsonify({
            'success': True,
            'audit_entries': audit_entries
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve audit log: {str(e)}'}), 500

# Additional routes moved from app_routes.py
@app.route('/view_assay/<assay_id>')
@login_required
def view_assay(assay_id):
    """View detailed assay information"""
    assay = db.session.get(Assay, assay_id)
    if not assay:
        abort(404)
    
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
        assays = db.session.query(Assay).order_by(Assay.created_at.desc()).all()
    else:
        assays = db.session.query(Assay).filter(Assay.analyst_id == current_user.id).order_by(Assay.created_at.desc()).all()
    
    return render_template('my_assays.html', assays=assays, user=current_user)

@app.route('/manage_users')
@login_required
@require_permission('manage_users')
def manage_users():
    """User management for administrators"""
    users = db.session.query(User).all()
    return render_template('admin/users.html', users=users, user=current_user)

@app.route('/admin/audit_log')
@login_required
@require_permission('view_audit_logs')
def admin_audit_log():
    """System-wide audit log for administrators"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get filter parameters
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query with filters
    query = db.session.query(AuditLog)
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < to_date)
        except ValueError:
            pass
    
    audit_entries = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique actions and users for filter dropdowns
    actions = db.session.query(AuditLog.action).distinct().all()
    users = db.session.query(User.id, User.username).all()
    
    return render_template('admin/audit_log.html', 
                         audit_entries=audit_entries, 
                         user=current_user,
                         actions=actions,
                         users=users,
                         current_filters={
                             'action': action_filter,
                             'user': user_filter,
                             'date_from': date_from,
                             'date_to': date_to
                         })

# USP-81 Compliance Endpoints
@app.route('/usp81/validate', methods=['POST'])
@login_required
def validate_usp81_compliance():
    """Validate assay data against USP-81 requirements"""
    try:
        data = request.get_json()
        assay_data = data.get('assay_data', {})
        
        if not assay_data:
            return jsonify({'error': 'No assay data provided'}), 400
        
        # Perform USP-81 validation
        validation_result = usp_calculator.comprehensive_usp81_validation(assay_data)
        
        # Generate report data
        report_data = usp_calculator.generate_usp81_report_data(validation_result, assay_data)
        
        # Log validation action
        log_audit_event(
            user_id=current_user.id,
            action='USP81_VALIDATION',
            description=f"USP-81 compliance validation performed - Score: {validation_result.score:.1f}%",
            entity_type='assay',
            entity_id=data.get('assay_id', 'unknown'),
            new_values={'compliance_score': validation_result.score, 'is_compliant': validation_result.is_compliant}
        )
        
        return jsonify({
            'success': True,
            'validation_result': {
                'is_compliant': validation_result.is_compliant,
                'score': validation_result.score,
                'checks_passed': validation_result.checks_passed,
                'total_checks': validation_result.total_checks,
                'status': 'COMPLIANT' if validation_result.is_compliant else 'NON-COMPLIANT'
            },
            'details': validation_result.details,
            'recommendations': validation_result.recommendations,
            'report_data': report_data
        })
        
    except Exception as e:
        return jsonify({'error': f'USP-81 validation failed: {str(e)}'}), 500

@app.route('/usp81/report/<assay_id>')
@login_required
def generate_usp81_report(assay_id):
    """Generate USP-81 compliance report for an assay"""
    try:
        assay = db.session.get(Assay, assay_id)
        if not assay:
            return jsonify({'error': 'Assay not found'}), 404
        
        # Check permissions
        if assay.analyst_id != current_user.id and not current_user.has_permission('view_all_assays'):
            flash('You do not have permission to view this assay.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get zone measurements for this assay
        zone_measurements = db.session.query(ZoneMeasurement).filter(ZoneMeasurement.assay_id == assay_id).all()
        
        # Organize data for USP-81 validation
        concentration_data = {}
        zone_data = {}
        
        # Group measurements by concentration (this would need to be enhanced based on your data structure)
        # For now, we'll use a simplified approach
        for zone in zone_measurements:
            # You might need to add concentration field to ZoneMeasurement or get it from assay metadata
            concentration = getattr(zone, 'concentration', 1.0)  # Default concentration
            if concentration not in concentration_data:
                concentration_data[concentration] = []
            concentration_data[concentration].append(zone.diameter_mm)
            
            # Group by standard (you might need to add standard field)
            standard = getattr(zone, 'standard', 'Unknown')
            if standard not in zone_data:
                zone_data[standard] = {'measurements': []}
            zone_data[standard]['measurements'].append(zone.diameter_mm)
        
        assay_data = {
            'concentration_data': concentration_data,
            'zone_data': zone_data
        }
        
        # Perform validation
        validation_result = usp_calculator.comprehensive_usp81_validation(assay_data)
        report_data = usp_calculator.generate_usp81_report_data(validation_result, assay_data)
        
        # Log report generation
        log_audit_event(
            user_id=current_user.id,
            action='USP81_REPORT_GENERATED',
            description=f"USP-81 compliance report generated for assay '{assay.name}'",
            entity_type='assay',
            entity_id=assay_id,
            new_values={'compliance_score': validation_result.score}
        )
        
        return render_template('usp81_report.html', 
                             assay=assay, 
                             validation_result=validation_result,
                             report_data=report_data,
                             user=current_user)
        
    except Exception as e:
        flash(f'Failed to generate USP-81 report: {str(e)}', 'error')
        return redirect(url_for('view_assay', assay_id=assay_id))

@app.route('/usp81/compliance_dashboard')
@login_required
def usp81_compliance_dashboard():
    """USP-81 compliance overview dashboard"""
    try:
        # Get all assays for the user (or all if supervisor/admin)
        if current_user.has_permission('view_all_assays'):
            assays = db.session.query(Assay).all()
        else:
            assays = db.session.query(Assay).filter(Assay.analyst_id == current_user.id).all()
        
        compliance_summary = {
            'total_assays': len(assays),
            'compliant_assays': 0,
            'non_compliant_assays': 0,
            'average_score': 0,
            'total_score': 0
        }
        
        assay_compliance_data = []
        
        for assay in assays:
            # Get zone measurements for this assay
            zone_measurements = db.session.query(ZoneMeasurement).filter(ZoneMeasurement.assay_id == assay.id).all()
            
            if zone_measurements:
                # Simplified validation (in production, you'd want more sophisticated data organization)
                concentration_data = {}
                for zone in zone_measurements:
                    concentration = getattr(zone, 'concentration', 1.0)
                    if concentration not in concentration_data:
                        concentration_data[concentration] = []
                    concentration_data[concentration].append(zone.diameter_mm)
                
                assay_data = {'concentration_data': concentration_data, 'zone_data': {}}
                validation_result = usp_calculator.comprehensive_usp81_validation(assay_data)
                
                compliance_summary['total_score'] += validation_result.score
                if validation_result.is_compliant:
                    compliance_summary['compliant_assays'] += 1
                else:
                    compliance_summary['non_compliant_assays'] += 1
                
                assay_compliance_data.append({
                    'assay': assay,
                    'compliance_score': validation_result.score,
                    'is_compliant': validation_result.is_compliant,
                    'checks_passed': validation_result.checks_passed,
                    'total_checks': validation_result.total_checks
                })
        
        if compliance_summary['total_assays'] > 0:
            compliance_summary['average_score'] = compliance_summary['total_score'] / compliance_summary['total_assays']
        
        return render_template('usp81_compliance_dashboard.html',
                             compliance_summary=compliance_summary,
                             assay_compliance_data=assay_compliance_data,
                             user=current_user)
        
    except Exception as e:
        flash(f'Failed to load compliance dashboard: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# User Management Endpoints
@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
@require_permission('manage_users')
def edit_user(user_id):
    """Edit user information"""
    try:
        user = db.session.get_or_404(User, user_id)
        
        # Prevent editing own account through this endpoint
        if user.id == current_user.id:
            flash('You cannot edit your own account through this interface.', 'warning')
            return redirect(url_for('manage_users'))
        
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        role = data.get('role')
        
        # Validate role
        if role not in ['analyst', 'supervisor', 'administrator']:
            return jsonify({'error': 'Invalid role specified'}), 400
        
        # Check if username/email already exists (excluding current user)
        if username != user.username:
            existing_user = db.session.query(User).filter(User.username == username).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Username already exists'}), 400
        
        if email != user.email:
            existing_email = db.session.query(User).filter(User.email == email).first()
            if existing_email and existing_email.id != user_id:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Update user
        user.username = username
        user.email = email
        user.role = role
        
        db.session.commit()
        
        # Log the change
        log_audit_event(
            user_id=current_user.id,
            action='USER_UPDATED',
            description=f"Updated user '{username}' (ID: {user_id})",
            entity_type='user',
            entity_id=str(user_id),
            old_values={'username': user.username, 'email': user.email, 'role': user.role},
            new_values={'username': username, 'email': email, 'role': role}
        )
        
        flash(f'User {username} updated successfully.', 'success')
        return jsonify({'success': True, 'message': 'User updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@require_permission('manage_users')
def toggle_user_status(user_id):
    """Toggle user active/inactive status"""
    try:
        user = db.session.get_or_404(User, user_id)
        
        # Prevent deactivating own account
        if user.id == current_user.id:
            return jsonify({'error': 'You cannot deactivate your own account'}), 400
        
        # Toggle status
        new_status = not user.active
        user.active = new_status
        
        # If deactivating, clear any locks
        if not new_status:
            user.locked_until = None
            user.failed_login_attempts = 0
        
        db.session.commit()
        
        # Log the change
        action = 'USER_DEACTIVATED' if not new_status else 'USER_ACTIVATED'
        status_text = 'deactivated' if not new_status else 'activated'
        
        log_audit_event(
            user_id=current_user.id,
            action=action,
            description=f"User '{user.username}' {status_text}",
            entity_type='user',
            entity_id=str(user_id),
            old_values={'active': not new_status},
            new_values={'active': new_status}
        )
        
        message = f"User {user.username} {status_text} successfully."
        flash(message, 'success')
        return jsonify({'success': True, 'message': message, 'active': new_status})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to toggle user status: {str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@require_permission('manage_users')
def reset_user_password(user_id):
    """Reset user password to default"""
    try:
        user = db.session.get_or_404(User, user_id)
        
        # Generate a secure random password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = ''.join(secrets.choice(alphabet) for i in range(12))
        
        # Set new password
        user.set_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        
        db.session.commit()
        
        # Log the change
        log_audit_event(
            user_id=current_user.id,
            action='PASSWORD_RESET',
            description=f"Password reset for user '{user.username}'",
            entity_type='user',
            entity_id=str(user_id)
        )
        
        message = f"Password for {user.username} has been reset. New password: {new_password}"
        flash(message, 'success')
        return jsonify({'success': True, 'message': 'Password reset successfully', 'new_password': new_password})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@require_permission('manage_users')
def delete_user(user_id):
    """Delete a user (soft delete)"""
    try:
        user = db.session.get_or_404(User, user_id)
        
        # Prevent deleting own account
        if user.id == current_user.id:
            return jsonify({'error': 'You cannot delete your own account'}), 400
        
        # Check if user has any assays
        if user.assays:
            return jsonify({'error': 'Cannot delete user with existing assays'}), 400
        
        # Soft delete - mark as inactive and rename
        user.active = False
        user.username = f"deleted_{user.username}_{user.id}"
        user.email = f"deleted_{user.email}_{user.id}"
        
        db.session.commit()
        
        # Log the change
        log_audit_event(
            user_id=current_user.id,
            action='USER_DELETED',
            description=f"User '{user.username}' deleted",
            entity_type='user',
            entity_id=str(user_id)
        )
        
        flash(f'User {user.username} deleted successfully.', 'success')
        return jsonify({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

@app.route('/admin/audit_log/export')
@login_required
@require_permission('view_audit_logs')
def export_audit_log():
    """Export audit log to CSV"""
    try:
        # Get filter parameters
        action_filter = request.args.get('action', '')
        user_filter = request.args.get('user', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query with filters
        query = db.session.query(AuditLog)
        
        if action_filter:
            query = query.filter(AuditLog.action == action_filter)
        
        if user_filter:
            query = query.filter(AuditLog.user_id == user_filter)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(AuditLog.timestamp >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(AuditLog.timestamp < to_date)
            except ValueError:
                pass
        
        audit_entries = query.order_by(AuditLog.timestamp.desc()).all()
        
        # Generate CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Timestamp', 'User', 'Action', 'Description', 'Entity Type', 'Entity ID', 'IP Address'])
        
        # Write data
        for entry in audit_entries:
            username = entry.user.username if entry.user else f"User ID: {entry.user_id}" if entry.user_id else "System"
            writer.writerow([
                entry.timestamp.strftime('%Y-%m-%d %H:%M:%S') if entry.timestamp else 'N/A',
                username,
                entry.action,
                entry.description,
                entry.entity_type or '-',
                entry.entity_id or '-',
                entry.ip_address or '-'
            ])
        
        output.seek(0)
        
        # Log export
        log_audit_event(
            user_id=current_user.id,
            action='AUDIT_LOG_EXPORTED',
            description=f"Audit log exported with {len(audit_entries)} entries",
            entity_type='system',
            entity_id='audit_log'
        )
        
        return send_file(
            StringIO(output.getvalue()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
