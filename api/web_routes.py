"""
Web interface routes for AdbSms
"""
import os
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Render the dashboard page"""
    api_key = current_app.config.get('API_KEY', 'dev-key-change-me-in-production')
    return render_template('index.html', api_key=api_key)

@web_bp.route('/bulk')
def bulk():
    """Render the bulk SMS management page"""
    api_key = current_app.config.get('API_KEY', 'dev-key-change-me-in-production')
    return render_template('bulk.html', api_key=api_key)

@web_bp.route('/history')
def history():
    """Render the message history page"""
    api_key = current_app.config.get('API_KEY', 'dev-key-change-me-in-production')
    return render_template('history.html', api_key=api_key)

@web_bp.route('/stats')
def stats():
    """Render the statistics page"""
    api_key = current_app.config.get('API_KEY', 'dev-key-change-me-in-production')
    return render_template('stats.html', api_key=api_key)

# Define a function to register the blueprint to avoid circular imports
def register_web_routes(app):
    app.register_blueprint(web_bp)