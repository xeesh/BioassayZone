from flask import Flask, render_template, request, jsonify, send_file, session
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from image_processor import ImageProcessor
from report_generator import ReportGenerator
from audit_logger import AuditLogger
import cv2
import numpy as np

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-for-sessions')

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page for image upload and assay setup"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle image upload and initial processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
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
            analyst_name = request.form.get('analyst_name', 'Unknown')
            sample_type = request.form.get('sample_type', 'Unknown')
            
            # Store session data
            session['current_assay'] = {
                'id': file_id,
                'filename': safe_filename,
                'filepath': filepath,
                'assay_name': assay_name,
                'analyst_name': analyst_name,
                'sample_type': sample_type,
                'timestamp': datetime.now().isoformat()
            }
            
            # Log upload action
            audit_logger.log_action(
                analyst_name,
                'IMAGE_UPLOAD',
                f"Uploaded image for assay '{assay_name}'",
                {'filename': filename, 'assay_id': file_id}
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
def analysis():
    """Analysis page with image display and zone detection tools"""
    if 'current_assay' not in session:
        return render_template('index.html', error='No assay data found. Please upload an image first.')
    
    return render_template('analysis.html', assay=session['current_assay'])

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
def generate_report():
    """Generate PDF report with all measurement data"""
    try:
        if 'current_assay' not in session:
            return jsonify({'error': 'No assay data found'}), 400
        
        data = request.get_json()
        zones = data.get('zones', [])
        statistics = session.get('statistics', {})
        
        assay = session['current_assay']
        
        # Generate report
        report_filename = f"bioassay_report_{assay['id']}.pdf"
        report_path = os.path.join(REPORTS_FOLDER, report_filename)
        
        report_data = {
            'assay': assay,
            'zones': zones,
            'statistics': statistics,
            'audit_trail': audit_logger.get_audit_trail(assay['id'])
        }
        
        report_generator.create_report(report_data, report_path)
        
        # Log report generation
        audit_logger.log_action(
            assay['analyst_name'],
            'REPORT_GENERATED',
            f"PDF report generated",
            {'assay_id': assay['id'], 'report_file': report_filename}
        )
        
        return jsonify({
            'success': True,
            'report_url': f'/download_report/{report_filename}',
            'message': 'Report generated successfully'
        })
        
    except Exception as e:
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
