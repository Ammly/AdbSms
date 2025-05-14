"""
AdbSms Flask REST API
High-performance REST API for sending SMS via ADB
"""
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, template_folder='../templates')

# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://adbsms:adbsms@localhost/adbsms')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False  # Preserve order of JSON keys in responses

# Authentication settings
app.config['SKIP_AUTH_IN_DEV'] = os.getenv('SKIP_AUTH_IN_DEV', 'True').lower() in ('true', '1', 'yes')
app.config['API_KEY'] = os.getenv('ADBSMS_API_KEY', 'dev-key-change-me-in-production')

# Setup CORS - allow web interface to access API
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Setup rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use redis:// for production
)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Basic routes
@app.route('/api')
def api_index():
    return jsonify({
        "name": "AdbSms API",
        "version": "0.2.0",
        "description": "A high-performance REST API for sending SMS via ADB",
        "documentation": "/api/docs"
    })

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Not found: {request.path}")
    return jsonify({
        "error": "Not found",
        "message": f"The requested URL {request.path} was not found on this server."
    }), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({
        "error": "Server error",
        "message": "An internal server error occurred. Please try again later."
    }), 500

@app.errorhandler(429)
def ratelimit_error(error):
    logger.warning(f"Rate limit exceeded: {get_remote_address()}")
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "You have exceeded your rate limit. Please try again later."
    }), 429

# Register Swagger UI blueprints
from api.swagger import swagger_bp, swaggerui_blueprint
app.register_blueprint(swagger_bp, url_prefix='/api')
app.register_blueprint(swaggerui_blueprint)

# Register API and Web blueprints - import at the end to avoid circular imports
def init_routes():
    # Register API routes
    from api.routes import register_blueprints
    register_blueprints(app)
    
    # Register Web interface routes
    from api.web_routes import register_web_routes
    register_web_routes(app)

# Initialize routes after app has been fully configured
if __name__ != '__main__':
    # Initialize routes when running as WSGI application
    init_routes()
else:
    # When running as a script, initialize routes here
    init_routes()
    app.run(debug=True)