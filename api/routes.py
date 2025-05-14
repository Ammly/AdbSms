"""
API routes for AdbSms - High-performance implementation
"""
import os
import tempfile
import time
from datetime import datetime
from flask import request, jsonify, Blueprint, current_app, url_for
from werkzeug.utils import secure_filename
from functools import wraps
import traceback

from api.models import Message, BulkMessageJob, DeviceStatus
from api.auth import require_api_key

# Initialize Blueprint for API v1
api_v1 = Blueprint('api_v1', __name__)

# Helper decorator for handling exceptions consistently
def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Import logger to avoid circular import
            from api.app import logger
            logger.error(f"Error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "error": "Internal server error", 
                "message": str(e)
            }), 500
    return decorated_function

# Device status endpoints
@api_v1.route('/device/status', methods=['GET'])
@handle_exceptions
@require_api_key
def device_status():
    """Get current device connection status"""
    # Import here to avoid circular import
    from api.app import limiter, db, logger
    from api.tasks import check_adb_connection_task
    
    # Apply rate limiter
    limiter.limit("30/minute")(lambda: None)()
    
    status = DeviceStatus.query.order_by(DeviceStatus.last_check.desc()).first()
    
    if not status:
        # If no status exists, trigger a check and create one
        task = check_adb_connection_task.delay()
        return jsonify({
            "status": "checking",
            "message": "Checking device status...",
            "task_id": task.id
        })
    
    # If status is outdated (older than 5 minutes), trigger a new check
    if (datetime.utcnow() - status.last_check).total_seconds() > 300:
        task = check_adb_connection_task.delay()
        return jsonify({
            "status": "refreshing",
            "message": "Status is outdated, refreshing...",
            "last_status": status.to_dict(),
            "task_id": task.id
        })
    
    return jsonify(status.to_dict())


@api_v1.route('/device/check', methods=['POST'])
@handle_exceptions
@require_api_key
def check_device():
    """Force a check of the device connection"""
    # Import here to avoid circular import
    from api.app import limiter, logger
    from api.tasks import check_adb_connection_task
    
    # Apply rate limiter
    limiter.limit("10/minute")(lambda: None)()
    
    task = check_adb_connection_task.delay()
    logger.info(f"Device check initiated: {task.id}")
    return jsonify({
        "status": "accepted",
        "task_id": task.id,
        "message": "Device check initiated"
    })


# SMS endpoints
@api_v1.route('/sms', methods=['POST'])
@handle_exceptions
@require_api_key
def send_sms():
    """Send a single SMS message"""
    # Import here to avoid circular import
    from api.app import db, limiter, logger
    from api.tasks import send_sms_task
    
    # Apply rate limiter
    limiter.limit("30/minute")(lambda: None)()
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    # Validate input
    required_fields = ['phone_number', 'content']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Validate phone number format (basic validation)
    phone = data['phone_number']
    if not (phone.startswith('+') and len(phone) >= 7):
        return jsonify({"error": "Phone number must start with + and be at least 7 characters"}), 400
    
    # Validate content length
    content = data['content']
    if len(content) > 1000:
        return jsonify({"error": "Message content exceeds 1000 character limit"}), 400
    
    # Create message record
    message = Message(
        phone_number=phone,
        content=content,
        sim_id=data.get('sim_id', 3),
        status='pending'
    )
    
    db.session.add(message)
    db.session.commit()
    
    # Queue the task
    task = send_sms_task.delay(message.id)
    logger.info(f"SMS queued: {message.id}, task: {task.id}")
    
    return jsonify({
        "status": "accepted",
        "message_id": message.id,
        "task_id": task.id,
        "url": url_for('api_v1.get_message', message_id=message.id)
    }), 202


@api_v1.route('/sms/<int:message_id>', methods=['GET'])
@handle_exceptions
@require_api_key
def get_message(message_id):
    """Get status of a specific message"""
    # Import here to avoid circular import
    from api.app import db
    
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    return jsonify(message.to_dict())


@api_v1.route('/sms/bulk', methods=['POST'])
@handle_exceptions
@require_api_key
def send_bulk_sms():
    """Process a bulk SMS job from CSV data"""
    # Import here to avoid circular import
    from api.app import db, limiter, logger
    from api.tasks import process_csv_upload
    
    # Apply rate limiter
    limiter.limit("5/minute")(lambda: None)()
    
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400
    
    # Save the file to a temporary location
    filename = secure_filename(file.filename)
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    file.save(temp_path)
    
    # Get parameters
    sim_id = request.form.get('sim_id', 3, type=int)
    delay = request.form.get('delay', 1.0, type=float)
    
    # Basic validation
    if delay < 0.1:
        return jsonify({"error": "Delay must be at least 0.1 seconds"}), 400
    if delay > 10.0:
        return jsonify({"error": "Delay cannot exceed 10 seconds"}), 400
    
    # Queue the processing task
    task = process_csv_upload.delay(
        temp_path,
        filename,
        sim_id,
        delay
    )
    
    logger.info(f"Bulk SMS job queued: {filename}, task: {task.id}")
    
    return jsonify({
        "status": "accepted",
        "task_id": task.id,
        "message": "CSV file queued for processing"
    }), 202


# Bulk job endpoints
@api_v1.route('/bulk/<int:job_id>', methods=['GET'])
@handle_exceptions
@require_api_key
def get_bulk_job(job_id):
    """Get status of a specific bulk SMS job"""
    # Import here to avoid circular import
    from api.app import db
    
    job = BulkMessageJob.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    result = job.to_dict()
    
    # Add progress percentage
    if job.total_messages > 0:
        result["progress"] = round(
            (job.successful_messages + job.failed_messages) / job.total_messages * 100, 1
        )
    else:
        result["progress"] = 0
    
    return jsonify(result)


@api_v1.route('/bulk', methods=['GET'])
@handle_exceptions
@require_api_key
def list_bulk_jobs():
    """List all bulk SMS jobs"""
    # Import here to avoid circular import
    from api.app import db
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Limit page size
    if per_page > 50:
        per_page = 50
    
    jobs = BulkMessageJob.query.order_by(BulkMessageJob.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        "total": jobs.total,
        "pages": jobs.pages,
        "current_page": jobs.page,
        "per_page": jobs.per_page,
        "jobs": [job.to_dict() for job in jobs.items]
    })


# Statistics endpoints
@api_v1.route('/stats', methods=['GET'])
@handle_exceptions
@require_api_key
def get_stats():
    """Get SMS statistics"""
    # Import here to avoid circular import
    from api.app import db
    
    # Count messages by status
    messages = {
        "total": Message.query.count(),
        "sent": Message.query.filter_by(status="sent").count(),
        "failed": Message.query.filter_by(status="failed").count(),
        "pending": Message.query.filter_by(status="pending").count(),
        "processing": Message.query.filter_by(status="processing").count()
    }
    
    # Count bulk jobs by status
    jobs = {
        "total": BulkMessageJob.query.count(),
        "completed": BulkMessageJob.query.filter_by(status="completed").count(),
        "failed": BulkMessageJob.query.filter_by(status="failed").count(),
        "pending": BulkMessageJob.query.filter_by(status="pending").count(),
        "processing": BulkMessageJob.query.filter_by(status="processing").count()
    }
    
    # Device status
    device = DeviceStatus.query.order_by(DeviceStatus.last_check.desc()).first()
    device_status = device.to_dict() if device else {"connected": False, "state": None}
    
    return jsonify({
        "messages": messages,
        "jobs": jobs,
        "device": device_status
    })


# Health check endpoint - Open access (no auth required)
@api_v1.route('/health', methods=['GET'])
@handle_exceptions
def health_check():
    """API health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.2.0"
    })


# API documentation - Open access (no auth required)
@api_v1.route('/docs', methods=['GET'])
def api_docs():
    """API documentation"""
    return jsonify({
        "message": "Please visit /api/docs for Swagger UI documentation"
    })

# Define a function to register blueprints to avoid circular imports
def register_blueprints(app):
    # Register the v1 blueprint with a unique name for /api
    app.register_blueprint(api_v1, url_prefix='/api')
    
    # For backward compatibility, also register at /api/v1 with a different name
    app.register_blueprint(api_v1, url_prefix='/api/v1', name='api_v1_specific')