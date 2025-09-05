# Silhouette Card Maker - Refactored Flask App

## Overview
This is the refactored version of the Silhouette Card Maker Flask application, restructured using Flask blueprints and featuring a modern TailwindCSS-based UI.

## Architecture Changes

### Blueprint Structure
- **Main** (`app/main/`): Core card generation functionality
- **API** (`app/api/`): RESTful API endpoints
- **Offset** (`app/offset/`): PDF offset correction tools
- **Calibration** (`app/calibration/`): Calibration PDF generation

### New Features
- **Modern UI**: TailwindCSS-based responsive design
- **Blueprint Architecture**: Modular, maintainable code organization
- **Enhanced UX**: Drag & drop file uploads, better visual feedback
- **Improved Navigation**: Tab-based interface with clear separation of concerns

## File Structure
```
app/
├── __init__.py              # Application factory
├── config.py               # Configuration settings
├── utils.py                # Shared utility functions
├── templates/              # Jinja2 templates with TailwindCSS
│   ├── base.html          # Base template with modern styling
│   ├── index.html         # Main interface
│   ├── offset.html        # PDF offset tool
│   └── select_back.html   # Back image selection
├── main/                  # Main blueprint
│   ├── __init__.py
│   └── routes.py
├── api/                   # API blueprint
│   ├── __init__.py
│   └── routes.py
├── offset/                # Offset blueprint
│   ├── __init__.py
│   └── routes.py
└── calibration/           # Calibration blueprint
    ├── __init__.py
    └── routes.py
```

## Running the Application

### Using the new entry point:
```bash
python run.py
```

### The original applications remain for compatibility:
- `python app.py` - Original simple version
- `python app_enhanced.py` - Enhanced version

## Key Improvements

1. **Modular Architecture**: Blueprints provide better code organization
2. **Modern UI/UX**: TailwindCSS creates a professional, responsive interface
3. **Enhanced File Handling**: Improved drag & drop with visual feedback
4. **Better Error Handling**: Centralized error handling and user feedback
5. **Configuration Management**: Centralized config with environment variable support
6. **Template Inheritance**: DRY principle with base templates
7. **Maintainability**: Separated concerns make the codebase easier to maintain

## Configuration
Environment variables can be used to override defaults:
- `SECRET_KEY`: Flask secret key for sessions
- `UPLOAD_FOLDER`: Directory for temporary uploads

## Development
The application maintains full compatibility with the original functionality while providing a more maintainable and modern codebase for future development.