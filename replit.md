# Bioassay Zone Measurement Tool - USP-81 / 21 CFR Part 11 Compliant

## Overview

This is a comprehensive web-based bioassay zone measurement application built with Flask that provides automated detection and manual measurement of inhibition zones in Petri dish images. The system is designed specifically for pharmaceutical and microbiological laboratories to analyze microbial assays with full USP-81 and 21 CFR Part 11 compliance. The application processes uploaded microscopy images using advanced computer vision techniques to detect circular inhibition zones, performs statistical analysis according to USP guidelines, and generates comprehensive PDF reports for regulatory compliance.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **✅ Database Integration**: Implemented full PostgreSQL database with user management, assay tracking, and audit logs
- **✅ User Authentication**: Added secure login system with role-based access control (Analyst, Supervisor, Administrator)
- **✅ Electronic Signatures**: Implemented 21 CFR Part 11 compliant electronic signature workflow
- **✅ Enhanced Audit Logging**: Tamper-proof audit trail with integrity checking and secure logging
- **✅ USP-81 Statistical Calculations**: Added ANOVA, parallel line assay analysis, and potency calculations
- **✅ Password Security**: Enforced strong password policies with history tracking and expiration

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **JavaScript Framework**: Vanilla JavaScript with Canvas API for image manipulation
- **UI Components**: Interactive canvas for zone detection, measurement tools, and real-time analysis
- **Authentication UI**: Professional login/register pages with security features
- **Styling**: Custom CSS with Bootstrap integration for professional laboratory interface

### Backend Architecture
- **Web Framework**: Flask with Flask-Login for user session management
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy for database operations
- **Request Handling**: RESTful API endpoints for file upload, image processing, and report generation
- **File Management**: Secure file upload with validation and unique filename generation
- **Session Management**: Flask sessions with secure secret key management

### Authentication and Security
- **User Management**: Role-based access control with three levels (Analyst, Supervisor, Administrator)
- **Password Security**: BCrypt hashing with password history tracking and strength validation
- **Account Protection**: Failed login attempt limiting with temporary account lockouts
- **Session Security**: Secure session management with CSRF protection capabilities
- **Electronic Signatures**: Cryptographic signature implementation with integrity verification

### Database Architecture
- **Primary Database**: PostgreSQL with environment-based configuration
- **User Model**: Complete user management with role-based permissions and security tracking
- **Assay Model**: Full assay lifecycle tracking with analyst assignment and approval workflow
- **Zone Measurements**: Individual zone data storage with automated and manual detection tracking
- **Audit Logging**: Comprehensive audit trail with tamper-proof integrity checking
- **Electronic Signatures**: Legal compliance tracking for document approval workflow

### Image Processing Pipeline
- **Computer Vision**: OpenCV (cv2) for automated zone detection using HoughCircles algorithm
- **Image Analysis**: Gaussian blur preprocessing, grayscale conversion, and circular pattern recognition
- **Measurement Calculation**: Pixel-to-millimeter conversion with configurable DPI settings
- **Manual Override**: Interactive canvas tools for manual zone marking and adjustment

### Statistical Analysis (USP-81 Compliant)
- **Basic Statistics**: Mean, median, standard deviation, coefficient of variation
- **Outlier Detection**: Modified Z-score based outlier identification
- **Parallel Line Assay**: 2+2 and 3+3 design analysis with ANOVA calculations
- **Potency Estimation**: Log-scale potency calculations with confidence intervals
- **Validity Tests**: Linearity, parallelism, and significance testing
- **Quality Assessment**: Precision grading based on CV% thresholds

### Report Generation System
- **PDF Engine**: ReportLab for professional laboratory report generation
- **Report Templates**: Structured PDF layouts with company branding and compliance sections
- **Data Visualization**: Tables, charts, and embedded images in reports
- **Audit Integration**: Complete audit trail inclusion in reports
- **Electronic Signature Support**: Signature verification and legal compliance documentation

## External Dependencies

### Core Web Framework
- **Flask**: Python web framework for request handling and routing
- **Flask-Login**: User session management and authentication
- **Flask-SQLAlchemy**: Database ORM integration
- **Flask-WTF**: Form handling and CSRF protection capabilities
- **Werkzeug**: Security utilities including password hashing

### Database and Security
- **PostgreSQL**: Production database with ACID compliance
- **psycopg2-binary**: PostgreSQL adapter for Python
- **SQLAlchemy**: Advanced ORM with relationship management
- **BCrypt**: Secure password hashing and verification

### Scientific Computing
- **NumPy**: Numerical computing for statistical calculations and image array manipulation
- **SciPy**: Advanced statistical functions including ANOVA and regression analysis
- **OpenCV (cv2)**: Computer vision library for automated zone detection
- **PIL/Pillow**: Image loading and basic processing capabilities

### Report Generation
- **ReportLab**: PDF generation library for laboratory reports
- **reportlab.platypus**: High-level PDF document construction
- **reportlab.lib**: Styling, colors, and layout utilities

### Frontend Libraries (CDN)
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome 6**: Icon library for user interface elements
- **JavaScript Canvas API**: Native browser API for image manipulation

## Project Architecture

### User Roles and Permissions
- **Analyst**: Can create assays, perform analysis, and view their own reports
- **Supervisor**: Can approve reports, apply electronic signatures, and view all assays
- **Administrator**: Full system access including user management and audit log access

### Compliance Features
- **21 CFR Part 11**: Electronic signature workflow with password confirmation and audit trails
- **USP-81**: Statistical analysis methods for bioassay validation and potency calculation
- **Data Integrity**: Tamper-proof audit logging with cryptographic integrity verification
- **User Authentication**: Secure login with role-based access control and password policies

### Security Implementation
- **Password Policies**: Minimum 8 characters with complexity requirements and history tracking
- **Account Lockout**: Automatic lockout after 5 failed attempts with 30-minute timeout
- **Audit Trail**: Complete activity logging with IP address and timestamp tracking
- **Electronic Signatures**: Cryptographically secured signatures with verification capabilities