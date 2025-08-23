from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import DateTime, Boolean, Text, JSON, String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import hmac
from typing import Optional, List

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role management"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default='analyst')  # analyst, supervisor, administrator
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Password policy tracking
    password_changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    password_history: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)  # Store hashes of previous passwords
    
    # Relationships
    assays: Mapped[List["Assay"]] = relationship("Assay", foreign_keys="Assay.analyst_id", back_populates="analyst")
    approved_assays: Mapped[List["Assay"]] = relationship("Assay", foreign_keys="Assay.approved_by", back_populates="approver")
    audit_entries: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    signatures: Mapped[List["ElectronicSignature"]] = relationship("ElectronicSignature", back_populates="signer")
    
    def set_password(self, password: str) -> None:
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
    
    def check_password(self, password: str) -> bool:
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
    
    def can_reuse_password(self, password: str) -> bool:
        """Check if password has been used recently (prevent reuse)"""
        if not self.password_history:
            return True
        
        for old_hash in self.password_history:
            if check_password_hash(old_hash, password):
                return False
        return True
    
    def has_permission(self, permission: str) -> bool:
        """Check role-based permissions"""
        permissions = {
            'analyst': ['create_assay', 'modify_assay', 'view_reports'],
            'supervisor': ['create_assay', 'modify_assay', 'view_reports', 'approve_reports', 'electronic_sign', 'view_all_assays'],
            'administrator': ['create_assay', 'modify_assay', 'view_reports', 'approve_reports', 'electronic_sign', 'manage_users', 'view_audit_logs', 'view_all_assays']
        }
        return permission in permissions.get(self.role, [])


class Assay(db.Model):
    """Assay model for storing bioassay information"""
    __tablename__ = 'assays'
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sample_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    analyst_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='active')  # active, completed, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Compliance tracking
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    analyst: Mapped["User"] = relationship("User", foreign_keys=[analyst_id], back_populates="assays")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], back_populates="approved_assays")
    zones: Mapped[List["ZoneMeasurement"]] = relationship("ZoneMeasurement", back_populates="assay", cascade="all, delete-orphan")
    statistics: Mapped[Optional["AssayStatistics"]] = relationship("AssayStatistics", back_populates="assay", uselist=False, cascade="all, delete-orphan")
    signatures: Mapped[List["ElectronicSignature"]] = relationship("ElectronicSignature", back_populates="assay")


class ZoneMeasurement(db.Model):
    """Model for individual zone measurements"""
    __tablename__ = 'zone_measurements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assay_id: Mapped[str] = mapped_column(String(36), ForeignKey('assays.id'), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)  # auto_1, manual_1, etc.
    x_position: Mapped[float] = mapped_column(Float, nullable=False)
    y_position: Mapped[float] = mapped_column(Float, nullable=False)
    radius_pixels: Mapped[float] = mapped_column(Float, nullable=False)
    diameter_mm: Mapped[float] = mapped_column(Float, nullable=False)
    detection_type: Mapped[str] = mapped_column(String(20), nullable=False)  # automatic, manual
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For automatic detection
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assay: Mapped["Assay"] = relationship("Assay", back_populates="zones")


class AssayStatistics(db.Model):
    """Model for storing calculated statistics"""
    __tablename__ = 'assay_statistics'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assay_id: Mapped[str] = mapped_column(String(36), ForeignKey('assays.id'), nullable=False)
    zone_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_diameter: Mapped[float] = mapped_column(Float, nullable=False)
    median_diameter: Mapped[float] = mapped_column(Float, nullable=False)
    std_deviation: Mapped[float] = mapped_column(Float, nullable=False)
    min_diameter: Mapped[float] = mapped_column(Float, nullable=False)
    max_diameter: Mapped[float] = mapped_column(Float, nullable=False)
    diameter_range: Mapped[float] = mapped_column(Float, nullable=False)
    cv_percent: Mapped[float] = mapped_column(Float, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # USP-81 specific calculations
    anova_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store ANOVA calculation results
    potency_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Final potency calculation
    confidence_interval: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store CI bounds
    validity_tests: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store validity test results
    
    # Relationships
    assay: Mapped["Assay"] = relationship("Assay", back_populates="statistics")


class AuditLog(db.Model):
    """Enhanced audit logging for compliance"""
    __tablename__ = 'audit_logs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # assay, user, system, etc.
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store previous values for changes
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Store new values for changes
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Security and integrity
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash for integrity
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_entries")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generate_checksum()
    
    def generate_checksum(self) -> None:
        """Generate integrity checksum for audit entry"""
        data = f"{self.timestamp}:{self.user_id}:{self.action}:{self.description}"
        self.checksum = hashlib.sha256(data.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify audit entry hasn't been tampered with"""
        expected = f"{self.timestamp}:{self.user_id}:{self.action}:{self.description}"
        expected_hash = hashlib.sha256(expected.encode()).hexdigest()
        return self.checksum == expected_hash


class ElectronicSignature(db.Model):
    """Electronic signature model for 21 CFR Part 11 compliance"""
    __tablename__ = 'electronic_signatures'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assay_id: Mapped[str] = mapped_column(String(36), ForeignKey('assays.id'), nullable=False)
    signer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    signature_type: Mapped[str] = mapped_column(String(50), nullable=False)  # approval, review, final
    signed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)  # The meaning of the signature
    signature_hash: Mapped[str] = mapped_column(String(256), nullable=False)  # Cryptographic signature
    
    # Additional security
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    document_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Hash of signed document/data
    
    # Relationships
    assay: Mapped["Assay"] = relationship("Assay", back_populates="signatures")
    signer: Mapped["User"] = relationship("User", back_populates="signatures")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generate_signature()
    
    def generate_signature(self) -> None:
        """Generate cryptographic signature"""
        data = f"{self.assay_id}:{self.signer_id}:{self.signed_at}:{self.meaning}"
        # In production, this should use a proper digital signature algorithm
        self.signature_hash = hashlib.sha256(data.encode()).hexdigest()


class SystemConfiguration(db.Model):
    """System configuration for compliance settings"""
    __tablename__ = 'system_config'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)