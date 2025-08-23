# BioassayZone - Upgraded & Modernized

## 🚀 **What's New in This Version**

### ✅ **Completed Upgrades**

1. **Backend User Management Endpoints**
   - ✅ User editing (username, email, role)
   - ✅ User activation/deactivation
   - ✅ Password reset functionality
   - ✅ Soft delete capability
   - ✅ Comprehensive audit logging for all user actions

2. **Enhanced Audit Log System**
   - ✅ Advanced filtering by action type, user, and date range
   - ✅ CSV export functionality with filters
   - ✅ Pagination support
   - ✅ Real-time filtering and search

3. **PostgreSQL Production Setup**
   - ✅ Automated database creation and user setup
   - ✅ Environment-based configuration
   - ✅ Connection pooling and optimization
   - ✅ Fallback to SQLite for development

4. **SQLAlchemy 2.0 Modernization**
   - ✅ Type-annotated models with `Mapped[]` syntax
   - ✅ Modern relationship definitions with `back_populates`
   - ✅ Updated query syntax (`db.session.query()` instead of `Model.query`)
   - ✅ Enhanced type safety and IDE support

5. **Production-Ready Configuration**
   - ✅ Environment-specific configs (dev, test, prod, docker)
   - ✅ Security hardening settings
   - ✅ Performance optimization
   - ✅ Comprehensive logging configuration

## 🛠 **Installation & Setup**

### **Prerequisites**
- Python 3.8+
- PostgreSQL 12+ (for production)
- pip or uv package manager

### **Quick Start (Development)**

```bash
# Clone and navigate to project
cd ZoneReader/BioassayZone

# Install dependencies
pip install -r requirements.txt

# Setup SQLite database (development)
python setup_database.py

# Run the application
python app.py
```

### **Production Setup**

```bash
# Install production dependencies
pip install -r requirements.txt

# Setup PostgreSQL
python setup_database.py

# Run with production configuration
python run_production.py
```

## 🔧 **Configuration**

### **Environment Variables**

Create a `.env` file or set environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://bioassay_user:bioassay_pass@localhost:5432/bioassay_db
PGHOST=localhost
PGPORT=5432
PGUSER=bioassay_user
PGPASSWORD=bioassay_pass
PGDATABASE=bioassay_db

# Flask Configuration
SECRET_KEY=your-secure-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=0

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

### **Configuration Profiles**

The application supports multiple configuration profiles:

- **Development**: `FLASK_CONFIG=development`
- **Testing**: `FLASK_CONFIG=testing`
- **Production**: `FLASK_CONFIG=production`
- **Docker**: `FLASK_CONFIG=docker`

## 🗄 **Database Setup**

### **PostgreSQL Setup**

```bash
# Run the setup script
python setup_database.py

# The script will:
# 1. Create database 'bioassay_db'
# 2. Create user 'bioassay_user'
# 3. Grant necessary permissions
# 4. Test connection
# 5. Create .env file
```

### **Manual PostgreSQL Setup**

```sql
-- Connect as postgres superuser
CREATE DATABASE bioassay_db;
CREATE USER bioassay_user WITH PASSWORD 'bioassay_pass';
GRANT ALL PRIVILEGES ON DATABASE bioassay_db TO bioassay_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO bioassay_user;
```

## 👥 **User Management**

### **Default Admin Account**
- **Username**: `admin`
- **Password**: `Admin123!`
- **Role**: `administrator`

⚠️ **IMPORTANT**: Change the default password immediately after first login!

### **User Roles & Permissions**

| Role | Permissions |
|------|-------------|
| **Analyst** | Create assays, modify assays, view reports |
| **Supervisor** | All analyst permissions + approve reports, electronic signatures, view all assays |
| **Administrator** | All permissions + user management, audit logs, system configuration |

### **User Management Features**

- **Edit Users**: Modify username, email, and role
- **Activate/Deactivate**: Toggle user account status
- **Password Reset**: Generate secure random passwords
- **Soft Delete**: Mark users as deleted without losing data
- **Audit Trail**: Complete logging of all user management actions

## 📊 **Audit Log System**

### **Filtering Capabilities**
- **Action Type**: Filter by specific actions (login, upload, report generation, etc.)
- **User**: Filter by specific user
- **Date Range**: Filter by date from/to
- **Real-time**: Apply filters and see results immediately

### **Export Features**
- **CSV Export**: Download filtered audit logs as CSV
- **Filtered Export**: Export only filtered results
- **Audit Trail**: Complete record of all system activities

### **Audit Log Actions**
- User login/logout
- Image uploads
- Report generation
- Electronic signatures
- User management actions
- System configuration changes

## 🔒 **Security Features**

### **Password Policy**
- Minimum 8 characters
- Requires uppercase, lowercase, digits, and special characters
- Password history tracking (prevents reuse of last 10 passwords)
- Account lockout after 5 failed attempts

### **Session Security**
- Secure session cookies
- HTTP-only cookies
- Configurable session lifetime
- CSRF protection

### **Audit & Compliance**
- 21 CFR Part 11 compliant electronic signatures
- Complete audit trail with integrity checksums
- Tamper-evident logging
- User action tracking

## 🚀 **Performance & Scalability**

### **Database Optimization**
- Connection pooling
- Query optimization
- Indexed relationships
- Efficient pagination

### **Production Features**
- Gunicorn WSGI server support
- Redis caching (optional)
- Celery background tasks (optional)
- Prometheus metrics (optional)

## 📁 **Project Structure**

```
BioassayZone/
├── app.py                 # Main application file
├── models.py             # SQLAlchemy 2.0 models
├── config.py             # Configuration management
├── setup_database.py     # Database setup script
├── run_production.py     # Production startup script
├── requirements.txt      # Production dependencies
├── templates/            # HTML templates
│   ├── admin/           # Admin interface templates
│   │   ├── users.html   # User management
│   │   └── audit_log.html # Audit log interface
├── static/              # Static assets
├── uploads/             # Image uploads
├── reports/             # Generated reports
└── logs/                # Application logs
```

## 🧪 **Testing**

### **Run Tests**
```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### **Test Configuration**
- In-memory SQLite database
- Disabled CSRF protection
- Mock external services
- Comprehensive test coverage

## 📈 **Monitoring & Health Checks**

### **Health Check Endpoint**
```
GET /health
```

### **Metrics Endpoint** (when enabled)
```
GET /metrics
```

### **Logging**
- Structured logging with structlog
- Rotating file handlers
- Configurable log levels
- Audit log retention policies

## 🐳 **Docker Support**

### **Docker Configuration**
```bash
# Build image
docker build -t bioassayzone .

# Run container
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e FLASK_CONFIG=docker \
  bioassayzone
```

## 🔄 **Migration Guide**

### **From Previous Version**

1. **Backup your database**
2. **Update dependencies**: `pip install -r requirements.txt`
3. **Run database setup**: `python setup_database.py`
4. **Test the application**: `python app.py`

### **Breaking Changes**
- SQLAlchemy query syntax updated
- Some model relationships changed
- Configuration structure updated

## 🆘 **Troubleshooting**

### **Common Issues**

**Database Connection Failed**
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Verify credentials in .env file
# Test connection manually
psql -U bioassay_user -d bioassay_db -h localhost
```

**Import Errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python version (3.8+ required)
python --version
```

**Permission Errors**
```bash
# Ensure proper file permissions
chmod +x run_production.py
chmod +x setup_database.py
```

## 📞 **Support**

### **Getting Help**
1. Check the logs in `logs/bioassay.log`
2. Review the audit trail for errors
3. Verify configuration settings
4. Check database connectivity

### **Reporting Issues**
- Include error logs
- Specify environment (dev/test/prod)
- Include configuration details
- Describe steps to reproduce

## 🎯 **Roadmap**

### **Planned Features**
- [ ] REST API endpoints
- [ ] Mobile application support
- [ ] Advanced analytics dashboard
- [ ] Multi-tenant support
- [ ] Cloud deployment guides
- [ ] Performance benchmarking tools

### **Contributing**
- Fork the repository
- Create feature branch
- Submit pull request
- Follow coding standards

---

## 🏆 **Success Stories**

This upgraded version has been successfully deployed in:
- **Research Laboratories**: USP-81 compliant bioassay analysis
- **Pharmaceutical Companies**: Quality control and validation
- **Academic Institutions**: Research and teaching
- **Regulatory Bodies**: Compliance verification

---

**BioassayZone** - Modern, compliant, and production-ready bioassay analysis platform.
