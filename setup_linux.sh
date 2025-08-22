#!/bin/bash

echo "===================================="
echo "Bioassay Zone Measurement Tool Setup"
echo "===================================="
echo

# Check Python installation
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9+ using your package manager"
    exit 1
fi

python3 --version

# Check PostgreSQL
echo
echo "Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed"
    echo "Install with: sudo apt install postgresql postgresql-contrib"
    exit 1
fi

# Install Python dependencies
echo
echo "Installing Python dependencies..."
pip3 install flask flask-login flask-sqlalchemy flask-wtf
pip3 install bcrypt opencv-python pillow reportlab 
pip3 install psycopg2-binary numpy scipy sqlalchemy werkzeug wtforms

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

# Run database setup
echo
echo "Running database setup..."
python3 setup_database.py

if [ $? -ne 0 ]; then
    echo "ERROR: Database setup failed"
    exit 1
fi

echo
echo "===================================="
echo "Setup completed successfully!"
echo "===================================="
echo
echo "To start the application:"
echo "  python3 app.py"
echo
echo "Then open: http://localhost:5000"
echo "Default login: admin / Admin123!"
echo

# Make the script executable
chmod +x setup_linux.sh