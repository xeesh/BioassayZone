from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from flask_login import LoginManager, login_required, current_user
import os
import json
import uuid
from datetime import datetime, timedelta
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
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access the bioassay system.'
login_manager.login_message_category = 'info'

# Register blueprints
app.register_blueprint(auth_bp)
from signatures import signatures_bp
app.register_blueprint(signatures_bp)

# Import additional routes
import app_routes

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
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if none exists
    if not User.query.filter_by(username='admin').first():
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
def index():
    """Main page for image upload and assay setup"""
    return render_template('index.html', user=current_user)

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
        return redirect(url_for('index'))
    
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
        assay = Assay.query.get(assay_data['id'])
        
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
            'audit_trail': AuditLog.query.filter_by(entity_id=assay.id).all()
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
