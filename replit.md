# Bioassay Zone Measurement Tool

## Overview

This is a web-based bioassay zone measurement application built with Flask that provides automated detection and manual measurement of inhibition zones in Petri dish images. The system is designed for pharmaceutical and microbiological laboratories to analyze microbial assays with proper audit logging and reporting capabilities. The application processes uploaded microscopy images using computer vision techniques to detect circular inhibition zones and generates comprehensive PDF reports for regulatory compliance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **JavaScript Framework**: Vanilla JavaScript with Canvas API for image manipulation
- **UI Components**: Interactive canvas for zone detection, measurement tools, and real-time analysis
- **Styling**: Custom CSS with Bootstrap integration for professional laboratory interface

### Backend Architecture
- **Web Framework**: Flask with session management for user state
- **Request Handling**: RESTful API endpoints for file upload, image processing, and report generation
- **File Management**: Secure file upload with validation and unique filename generation
- **Session Management**: Flask sessions with configurable secret key for user state persistence

### Image Processing Pipeline
- **Computer Vision**: OpenCV (cv2) for automated zone detection using HoughCircles algorithm
- **Image Analysis**: Gaussian blur preprocessing, grayscale conversion, and circular pattern recognition
- **Measurement Calculation**: Pixel-to-millimeter conversion with configurable DPI settings
- **Manual Override**: Interactive canvas tools for manual zone marking and adjustment

### Data Storage Solutions
- **File Storage**: Local filesystem with organized directory structure (uploads/, reports/)
- **Audit Logging**: JSON-based audit trail system with timestamped entries
- **Session Data**: Server-side session storage for user workflow state
- **Report Storage**: Generated PDF reports stored locally with unique identifiers

### Authentication and Authorization
- **Current State**: Basic session-based state management without user authentication
- **Audit Trail**: User identification through manual entry rather than authenticated sessions
- **Access Control**: No role-based permissions currently implemented
- **Session Security**: Configurable secret key for session encryption

### Report Generation System
- **PDF Engine**: ReportLab for professional laboratory report generation
- **Report Templates**: Structured PDF layouts with company branding and compliance sections
- **Data Visualization**: Tables, charts, and embedded images in reports
- **Export Formats**: PDF output with print-optimized layouts

## External Dependencies

### Core Web Framework
- **Flask**: Python web framework for request handling and routing
- **Jinja2**: Template engine for HTML rendering (included with Flask)
- **Werkzeug**: WSGI utilities for secure file handling (included with Flask)

### Image Processing Libraries
- **OpenCV (cv2)**: Computer vision library for automated zone detection
- **NumPy**: Numerical computing for image array manipulation
- **PIL/Pillow**: Image loading and basic processing capabilities

### Report Generation
- **ReportLab**: PDF generation library for laboratory reports
- **reportlab.platypus**: High-level PDF document construction
- **reportlab.lib**: Styling, colors, and layout utilities

### Frontend Libraries (CDN)
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome 6**: Icon library for user interface elements
- **JavaScript Canvas API**: Native browser API for image manipulation

### Development and Deployment
- **Python 3.x**: Runtime environment
- **Environment Variables**: Configuration management for sensitive settings
- **File System**: Local storage for uploads, reports, and audit logs

### Missing Integration Opportunities
- **Database**: Currently using JSON files; could integrate PostgreSQL for scalable data storage
- **Authentication Service**: Could integrate OAuth2 or LDAP for user management
- **Cloud Storage**: Could integrate AWS S3 or similar for file storage
- **Scanner Integration**: Could add TWAIN/WIA libraries for direct scanner connectivity