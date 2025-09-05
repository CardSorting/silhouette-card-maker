#!/usr/bin/env python3
"""
Main entry point for the Silhouette Card Maker Flask application.
Refactored with blueprints for better organization.
"""

from app import create_app
from flask import flash, redirect, url_for

app = create_app()


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum file size is 64MB.')
    return redirect(url_for('main.index'))


@app.errorhandler(404)
def not_found(e):
    return redirect(url_for('main.index'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)