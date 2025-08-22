# Bioassay Zone Measurement Tool
## USP-81 / 21 CFR Part 11 Compliant System

A comprehensive web-based bioassay zone measurement application for pharmaceutical and microbiological laboratories. This system provides automated detection and manual measurement of inhibition zones in Petri dish images with full regulatory compliance.

![Dashboard Preview](https://via.placeholder.com/800x400/2c5aa0/ffffff?text=Professional+ZoneSight+Plus+Dashboard)

## Features

### Core Functionality
- **Automated Zone Detection**: Computer vision-based circular zone detection using OpenCV
- **Manual Measurement Tools**: Interactive canvas for precise manual measurements
- **Statistical Analysis**: USP-81 compliant statistical calculations and validation
- **Report Generation**: Professional PDF reports with embedded images and data
- **Image Processing**: Support for multiple formats (PNG, JPG, JPEG, TIFF, BMP)

### Compliance & Security
- **21 CFR Part 11**: Electronic signature workflow with tamper-proof audit trails
- **USP-81**: Statistical methods for bioassay validation and potency calculations
- **Role-Based Access**: Three-tier user system (Analyst, Supervisor, Administrator)
- **Audit Logging**: Comprehensive activity tracking with integrity verification
- **Data Security**: Encrypted passwords, secure sessions, and failed login protection

### Professional Interface
- **ZoneSight Plus Design**: Modern pharmaceutical-grade user interface
- **Dashboard Analytics**: Real-time statistics and activity monitoring
- **Advanced Navigation**: Sidebar navigation with quick access to all features
- **Responsive Design**: Bootstrap-based responsive interface for all devices

## Requirements

### System Requirements
- **Python**: 3.9 or higher
- **PostgreSQL**: 12.0 or higher
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: 2GB free space for application and database

### Python Dependencies
The application requires the following Python packages:
- Flask 3.1.2 (Web framework)
- Flask-Login 0.7.0 (User authentication)
- Flask-SQLAlchemy 3.1.1 (Database ORM)
- PostgreSQL adapter (psycopg2-binary)
- OpenCV 4.11+ (Computer vision)
- ReportLab 4.4+ (PDF generation)
- NumPy & SciPy (Scientific computing)
- Pillow (Image processing)

## Installation Guide

### Step 1: Install PostgreSQL

#### Windows
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer and follow the setup wizard
3. Remember the password you set for the 'postgres' user
4. Ensure PostgreSQL service is running

#### macOS
```bash
# Using Homebrew
brew install postgresql
brew services start postgresql
```

#### Ubuntu/Linux
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 2: Clone and Setup Application

```bash
# Clone the repository
git clone <repository-url>
cd bioassay-zone-measurement

# Install Python dependencies
pip install flask flask-login flask-sqlalchemy flask-wtf
pip install bcrypt opencv-python pillow reportlab
pip install psycopg2-binary numpy scipy sqlalchemy werkzeug wtforms
```

### Step 3: Database Setup

Run the automated database setup script:

```bash
python setup_database.py
```

The script will:
- ✅ Check PostgreSQL installation and service
- ✅ Create database and user for the application
- ✅ Generate .env file with database configuration
- ✅ Provide next steps for launching the application

#### Manual Database Setup (Alternative)

If the automated script doesn't work, you can set up manually:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE USER bioassay_user WITH PASSWORD 'bioassay_pass';
CREATE DATABASE bioassay_db OWNER bioassay_user;
GRANT ALL PRIVILEGES ON DATABASE bioassay_db TO bioassay_user;
\\q
```

Create `.env` file in the project root:
```env
DATABASE_URL=postgresql://bioassay_user:bioassay_pass@localhost:5432/bioassay_db
PGHOST=localhost
PGPORT=5432
PGUSER=bioassay_user
PGPASSWORD=bioassay_pass
PGDATABASE=bioassay_db
SECRET_KEY=your-secret-key-change-this-in-production
```

### Step 4: Launch Application

```bash
python app.py
```

The application will:
- Create all database tables automatically
- Create default admin user (admin / Admin123!)
- Start the web server on http://localhost:5000

## Quick Start Guide

### First Time Setup
1. **Open Browser**: Navigate to http://localhost:5000
2. **Login**: Use default admin credentials:
   - Username: `admin`
   - Password: `Admin123!`
3. **Change Password**: Immediately change the admin password
4. **Create Users**: Add analyst and supervisor accounts as needed

### Basic Workflow
1. **Upload Image**: Click "Zone Analysis" and upload a Petri dish image
2. **Auto Detection**: System automatically detects circular zones
3. **Manual Adjustment**: Fine-tune measurements using interactive tools
4. **Analysis**: Review statistical calculations and USP-81 compliance
5. **Generate Report**: Create professional PDF reports
6. **Electronic Signature**: Supervisors can apply 21 CFR Part 11 signatures

## User Roles & Permissions

### Analyst
- Create and perform bioassay analyses
- Upload images and measure zones
- View their own assays and results
- Generate individual reports

### Supervisor  
- All Analyst permissions
- Apply electronic signatures to reports
- View all assays from all users
- Approve completed analyses

### Administrator
- All Supervisor permissions
- User management (create/edit/deactivate users)
- System audit log access
- Database maintenance and backups

## Configuration Options

### Database Configuration
Edit `.env` file to change database settings:
```env
DATABASE_URL=postgresql://username:password@host:port/database
```

### Security Settings
- `SECRET_KEY`: Flask session encryption key (change in production!)
- Password policies: Minimum 8 characters, complexity requirements
- Session timeout: 24 hours default
- Failed login lockout: 5 attempts, 30-minute timeout

### File Storage
- **Uploads**: `./uploads/` directory for user images
- **Reports**: `./reports/` directory for generated PDFs
- **Audit Logs**: `audit_log.json` for compliance tracking

## Compliance Documentation

### 21 CFR Part 11 Features
- ✅ Electronic signatures with user authentication
- ✅ Tamper-proof audit trails with integrity checking
- ✅ Access controls with role-based permissions
- ✅ Electronic record retention and archival
- ✅ System validation and documentation

### USP-81 Statistical Methods
- ✅ Parallel line assay analysis (2+2 and 3+3 designs)
- ✅ ANOVA calculations for linearity and parallelism
- ✅ Potency estimation with confidence intervals
- ✅ Outlier detection using modified Z-scores
- ✅ Quality assessment with precision grading

## Troubleshooting

### Common Issues

#### Database Connection Errors
```
Solution: Check PostgreSQL service is running and credentials in .env file
```

#### Module Import Errors
```
Solution: Ensure all Python dependencies are installed: pip install <package>
```

#### Port Already in Use
```
Solution: Change port in app.py or kill process using port 5000
```

#### Image Upload Failures
```
Solution: Check file format (PNG/JPG/TIFF) and ensure uploads/ directory exists
```

### Error Logs
- **Application Logs**: Check console output when running python app.py
- **Database Logs**: PostgreSQL logs location varies by OS
- **Audit Logs**: audit_log.json contains compliance-related events

## Development

### Project Structure
```
bioassay-zone-measurement/
├── app.py                 # Main Flask application
├── app_routes.py          # Additional route handlers
├── models.py              # Database models
├── auth.py                # User authentication
├── signatures.py          # Electronic signatures
├── image_processor.py     # Computer vision processing
├── report_generator.py    # PDF report generation
├── usp_calculations.py    # Statistical calculations
├── audit_logger.py        # Compliance logging
├── setup_database.py      # Database setup script
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── uploads/               # User uploaded images
└── reports/               # Generated PDF reports
```

### Adding New Features
1. Create new route in `app_routes.py`
2. Add database models in `models.py` 
3. Update templates in `templates/`
4. Add audit logging for compliance
5. Update tests and documentation

## Security Considerations

### Production Deployment
- Change `SECRET_KEY` to a strong random value
- Use HTTPS with proper SSL certificates
- Set up PostgreSQL with strong authentication
- Regular security updates and patches
- Implement network firewalls and access controls

### Data Protection
- All passwords are hashed with bcrypt
- Session data is encrypted
- Database connections use SSL in production
- Audit logs track all user activities
- Electronic signatures prevent data tampering

## Support & Documentation

### Getting Help
- Check troubleshooting section above
- Review application logs for error details
- Ensure all dependencies are properly installed
- Verify PostgreSQL service is running

### Regulatory Compliance
This system is designed to meet USP-81 and 21 CFR Part 11 requirements for pharmaceutical laboratories. Always consult with your quality assurance team and regulatory experts to ensure proper validation and compliance in your specific environment.

---

**Version**: 2.0.0  
**Last Updated**: August 2025  
**License**: Professional Laboratory Use  
**Compliance**: USP-81, 21 CFR Part 11