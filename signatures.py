from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Assay, ElectronicSignature, AuditLog
from auth import log_audit_event, require_permission
from datetime import datetime
import hashlib

signatures_bp = Blueprint('signatures', __name__, url_prefix='/signatures')

@signatures_bp.route('/sign_report/<assay_id>', methods=['GET', 'POST'])
@login_required
@require_permission('electronic_sign')
def sign_report(assay_id):
    """Electronic signature workflow for report approval"""
    assay = Assay.query.get_or_404(assay_id)
    
    if request.method == 'POST':
        # Get signature details
        password = request.form.get('password', '')
        meaning = request.form.get('meaning', '')
        signature_type = request.form.get('signature_type', 'approval')
        
        # Verify user password for electronic signature
        if not current_user.check_password(password):
            flash('Invalid password. Electronic signature requires password confirmation.', 'error')
            return render_template('signatures/sign_report.html', assay=assay)
        
        if not meaning:
            flash('Please provide the meaning of your electronic signature.', 'error')
            return render_template('signatures/sign_report.html', assay=assay)
        
        try:
            # Create electronic signature
            signature = ElectronicSignature(
                assay_id=assay_id,
                signer_id=current_user.id,
                signature_type=signature_type,
                meaning=meaning,
                ip_address=request.remote_addr,
                document_hash=_calculate_assay_hash(assay)
            )
            
            db.session.add(signature)
            
            # Update assay status
            if signature_type == 'approval':
                assay.approved = True
                assay.approved_by = current_user.id
                assay.approved_at = datetime.utcnow()
                assay.status = 'completed'
            
            db.session.commit()
            
            # Log the electronic signature
            log_audit_event(
                user_id=current_user.id,
                action='ELECTRONIC_SIGNATURE',
                description=f"Applied {signature_type} signature to assay '{assay.name}': {meaning}",
                entity_type='assay',
                entity_id=assay_id,
                new_values={
                    'signature_type': signature_type,
                    'meaning': meaning,
                    'approved': assay.approved
                }
            )
            
            flash(f'Electronic signature applied successfully. Report has been {signature_type}d.', 'success')
            return redirect(url_for('view_assay', assay_id=assay_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Electronic signature failed: {str(e)}', 'error')
            return render_template('signatures/sign_report.html', assay=assay)
    
    return render_template('signatures/sign_report.html', assay=assay)

@signatures_bp.route('/verify_signature/<signature_id>')
@login_required
def verify_signature(signature_id):
    """Verify the integrity of an electronic signature"""
    signature = ElectronicSignature.query.get_or_404(signature_id)
    
    # Recalculate signature hash
    data = f"{signature.assay_id}:{signature.signer_id}:{signature.signed_at}:{signature.meaning}"
    expected_hash = hashlib.sha256(data.encode()).hexdigest()
    
    is_valid = signature.signature_hash == expected_hash
    
    verification_result = {
        'signature_id': signature_id,
        'is_valid': is_valid,
        'signer': signature.signer.username,
        'signed_at': signature.signed_at.isoformat(),
        'meaning': signature.meaning,
        'assay_name': signature.assay.name
    }
    
    # Log verification attempt
    log_audit_event(
        user_id=current_user.id,
        action='SIGNATURE_VERIFICATION',
        description=f"Verified electronic signature {signature_id} - Result: {'Valid' if is_valid else 'Invalid'}",
        entity_type='signature',
        entity_id=str(signature_id),
        new_values=verification_result
    )
    
    return jsonify(verification_result)

def _calculate_assay_hash(assay):
    """Calculate a hash representing the current state of the assay data"""
    # Include key assay data in hash calculation
    data_string = f"{assay.id}:{assay.name}:{assay.sample_type}:{len(assay.zones)}"
    
    # Include zone measurements
    for zone in sorted(assay.zones, key=lambda z: z.id):
        data_string += f":{zone.diameter_mm}:{zone.detection_type}"
    
    # Include statistics if available
    if assay.statistics:
        stats = assay.statistics
        data_string += f":{stats.mean_diameter}:{stats.std_deviation}:{stats.cv_percent}"
    
    return hashlib.sha256(data_string.encode()).hexdigest()