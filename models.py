from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import DateTime, Boolean, Text, JSON
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import hmac

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='analyst')  # analyst, supervisor, administrator
    active = db.Column(Boolean, default=True, nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    last_login = db.Column(DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(DateTime)
    
    # Password policy tracking
    password_changed_at = db.Column(DateTime, default=datetime.utcnow)
    password_history = db.Column(JSON)  # Store hashes of previous passwords
    
    # Relationships
    assays = db.relationship('Assay', foreign_keys='Assay.analyst_id', backref='analyst', lazy=True)
    approved_assays = db.relationship('Assay', foreign_keys='Assay.approved_by', backref='approver', lazy=True)
    audit_entries = db.relationship('AuditLog', backref='user', lazy=True)
    signatures = db.relationship('ElectronicSignature', backref='signer', lazy=True)
    
    def set_password(self, password):
        """Set password with history tracking"""
        new_hash = generate_password_hash(password)
        
        # Track password history (store up to 10 previous passwords)
        if self.password_history is None:
            self.password_history = []
        
        if self.password_hash:
            self.password_history.append(self.password_hash)
            # Keep only last 10 passwords
            self.password_history = self.password_history[-10:]
        
        self.password_hash = new_hash
        self.password_changed_at = datetime.utcnow()
    
    def check_password(self, password):
        """Check password with account lockout protection"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return False
        
        is_valid = check_password_hash(self.password_hash, password)
        
        if not is_valid:
            self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
            if self.failed_login_attempts >= 5:
                # Lock account for 30 minutes
                self.locked_until = datetime.utcnow() + timedelta(minutes=30)
        else:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_login = datetime.utcnow()
        
        db.session.commit()
        return is_valid
    
    def can_reuse_password(self, password):
        """Check if password has been used recently (prevent reuse)"""
        if not self.password_history:
            return True
        
        for old_hash in self.password_history:
            if check_password_hash(old_hash, password):
                return False
        return True
    
    def has_permission(self, permission):
        """Check role-based permissions"""
        permissions = {
            'analyst': ['create_assay', 'modify_assay', 'view_reports'],
            'supervisor': ['create_assay', 'modify_assay', 'view_reports', 'approve_reports', 'electronic_sign'],
            'administrator': ['create_assay', 'modify_assay', 'view_reports', 'approve_reports', 'electronic_sign', 'manage_users', 'view_audit_logs']
        }
        return permission in permissions.get(self.role, [])


class Assay(db.Model):
    """Assay model for storing bioassay information"""
    __tablename__ = 'assays'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(200), nullable=False)
    sample_type = db.Column(db.String(100))
    analyst_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_filename = db.Column(db.String(255))
    image_path = db.Column(db.String(500))
    status = db.Column(db.String(20), default='active')  # active, completed, archived
    created_at = db.Column(DateTime, default=datetime.utcnow)
    completed_at = db.Column(DateTime)
    
    # Compliance tracking
    validated = db.Column(Boolean, default=False)
    approved = db.Column(Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(DateTime)
    
    # Relationships
    zones = db.relationship('ZoneMeasurement', backref='assay', lazy=True, cascade='all, delete-orphan')
    statistics = db.relationship('AssayStatistics', backref='assay', uselist=False, cascade='all, delete-orphan')
    signatures = db.relationship('ElectronicSignature', backref='assay', lazy=True)


class ZoneMeasurement(db.Model):
    """Model for individual zone measurements"""
    __tablename__ = 'zone_measurements'
    
    id = db.Column(db.Integer, primary_key=True)
    assay_id = db.Column(db.String(36), db.ForeignKey('assays.id'), nullable=False)
    zone_id = db.Column(db.String(50), nullable=False)  # auto_1, manual_1, etc.
    x_position = db.Column(db.Float, nullable=False)
    y_position = db.Column(db.Float, nullable=False)
    radius_pixels = db.Column(db.Float, nullable=False)
    diameter_mm = db.Column(db.Float, nullable=False)
    detection_type = db.Column(db.String(20), nullable=False)  # automatic, manual
    confidence = db.Column(db.Float)  # For automatic detection
    created_at = db.Column(DateTime, default=datetime.utcnow)
    modified_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssayStatistics(db.Model):
    """Model for storing calculated statistics"""
    __tablename__ = 'assay_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    assay_id = db.Column(db.String(36), db.ForeignKey('assays.id'), nullable=False)
    zone_count = db.Column(db.Integer, nullable=False)
    mean_diameter = db.Column(db.Float, nullable=False)
    median_diameter = db.Column(db.Float, nullable=False)
    std_deviation = db.Column(db.Float, nullable=False)
    min_diameter = db.Column(db.Float, nullable=False)
    max_diameter = db.Column(db.Float, nullable=False)
    diameter_range = db.Column(db.Float, nullable=False)
    cv_percent = db.Column(db.Float, nullable=False)
    calculated_at = db.Column(DateTime, default=datetime.utcnow)
    
    # USP-81 specific calculations
    anova_results = db.Column(JSON)  # Store ANOVA calculation results
    potency_estimate = db.Column(db.Float)  # Final potency calculation
    confidence_interval = db.Column(JSON)  # Store CI bounds
    validity_tests = db.Column(JSON)  # Store validity test results


class AuditLog(db.Model):
    """Enhanced audit logging for compliance"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(Text, nullable=False)
    entity_type = db.Column(db.String(50))  # assay, user, system, etc.
    entity_id = db.Column(db.String(50))
    old_values = db.Column(JSON)  # Store previous values for changes
    new_values = db.Column(JSON)  # Store new values for changes
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    session_id = db.Column(db.String(100))
    
    # Security and integrity
    checksum = db.Column(db.String(64))  # SHA-256 hash for integrity
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generate_checksum()
    
    def generate_checksum(self):
        """Generate integrity checksum for audit entry"""
        data = f"{self.timestamp}:{self.user_id}:{self.action}:{self.description}"
        self.checksum = hashlib.sha256(data.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify audit entry hasn't been tampered with"""
        expected = f"{self.timestamp}:{self.user_id}:{self.action}:{self.description}"
        expected_hash = hashlib.sha256(expected.encode()).hexdigest()
        return self.checksum == expected_hash


class ElectronicSignature(db.Model):
    """Electronic signature model for 21 CFR Part 11 compliance"""
    __tablename__ = 'electronic_signatures'
    
    id = db.Column(db.Integer, primary_key=True)
    assay_id = db.Column(db.String(36), db.ForeignKey('assays.id'), nullable=False)
    signer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    signature_type = db.Column(db.String(50), nullable=False)  # approval, review, final
    signed_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    meaning = db.Column(Text, nullable=False)  # The meaning of the signature
    signature_hash = db.Column(db.String(256), nullable=False)  # Cryptographic signature
    
    # Additional security
    ip_address = db.Column(db.String(45))
    document_hash = db.Column(db.String(64))  # Hash of signed document/data
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generate_signature()
    
    def generate_signature(self):
        """Generate cryptographic signature"""
        data = f"{self.assay_id}:{self.signer_id}:{self.signed_at}:{self.meaning}"
        # In production, this should use a proper digital signature algorithm
        self.signature_hash = hashlib.sha256(data.encode()).hexdigest()


class SystemConfiguration(db.Model):
    """System configuration for compliance settings"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(Text)
    description = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))