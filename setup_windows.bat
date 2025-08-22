@echo off
echo ====================================
echo Bioassay Zone Measurement Tool Setup
echo ====================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo.
echo Installing Python dependencies...
pip install flask flask-login flask-sqlalchemy flask-wtf
pip install bcrypt opencv-python pillow reportlab 
pip install psycopg2-binary numpy scipy sqlalchemy werkzeug wtforms

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Running database setup...
python setup_database.py

if errorlevel 1 (
    echo ERROR: Database setup failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo Setup completed successfully!
echo ====================================
echo.
echo To start the application:
echo   python app.py
echo.
echo Then open: http://localhost:5000
echo Default login: admin / Admin123!
echo.
pause