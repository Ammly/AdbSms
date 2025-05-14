"""
API routes for AdbSms - High-performance implementation
"""
import os
import tempfile
import time
import io
import base64
from datetime import datetime, timedelta
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
    
    # Read the file content instead of saving to a temporary file
    # This way we can pass the content directly to the Celery task
    csv_content = file.read().decode('utf-8')
    
    # Get parameters
    sim_id = request.form.get('sim_id', 3, type=int)
    delay = request.form.get('delay', 1.0, type=float)
    
    # Basic validation
    if delay < 0.1:
        return jsonify({"error": "Delay must be at least 0.1 seconds"}), 400
    if delay > 10.0:
        return jsonify({"error": "Delay cannot exceed 10 seconds"}), 400
    
    # Queue the processing task with the CSV content directly
    task = process_csv_upload.delay(
        csv_content,
        secure_filename(file.filename),
        sim_id,
        delay
    )
    
    logger.info(f"Bulk SMS job queued: {file.filename}, task: {task.id}")
    
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


@api_v1.route('/messages/history', methods=['GET'])
@handle_exceptions
@require_api_key
def messages_history():
    """Get message history with pagination and filtering"""
    # Import here to avoid circular import
    from api.app import db
    from sqlalchemy import or_
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit page size
    if per_page > 100:
        per_page = 100
    
    # Get filter parameters
    status = request.args.get('status', 'all', type=str)
    date_range = request.args.get('date_range', 'all', type=str)
    phone_number = request.args.get('phone_number', '', type=str)
    
    # Build query with filters
    query = Message.query
    
    # Filter by status
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Filter by date range
    now = datetime.utcnow()
    if date_range == 'today':
        query = query.filter(Message.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif date_range == 'yesterday':
        yesterday = now - timedelta(days=1)
        query = query.filter(
            Message.created_at >= yesterday.replace(hour=0, minute=0, second=0, microsecond=0),
            Message.created_at < now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
    elif date_range == 'week':
        query = query.filter(Message.created_at >= now - timedelta(days=7))
    elif date_range == 'month':
        query = query.filter(Message.created_at >= now - timedelta(days=30))
    
    # Filter by phone number (partial match)
    if phone_number:
        query = query.filter(Message.phone_number.like(f'%{phone_number}%'))
    
    # Execute paginated query
    paginated_messages = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Return paginated results
    return jsonify({
        "total": paginated_messages.total,
        "pages": paginated_messages.pages,
        "current_page": paginated_messages.page,
        "per_page": paginated_messages.per_page,
        "messages": [message.to_dict() for message in paginated_messages.items]
    })


# Statistics endpoints
@api_v1.route('/stats', methods=['GET'])
@handle_exceptions
@require_api_key
def get_stats():
    """Get SMS statistics"""
    # Import here to avoid circular import
    from api.app import db
    from sqlalchemy import func
    
    # Get time range parameter
    time_range = request.args.get('time_range', 'all', type=str)
    
    # Set time filter based on time range
    now = datetime.utcnow()
    time_filter = None
    
    if time_range == 'day':
        time_filter = now - timedelta(days=1)
    elif time_range == 'week':
        time_filter = now - timedelta(days=7)
    elif time_range == 'month':
        time_filter = now - timedelta(days=30)
    elif time_range == 'year':
        time_filter = now - timedelta(days=365)
    
    # Base queries
    message_query = Message.query
    job_query = BulkMessageJob.query
    
    # Apply time filter if specified
    if time_filter:
        message_query = message_query.filter(Message.created_at >= time_filter)
        job_query = job_query.filter(BulkMessageJob.created_at >= time_filter)
    
    # Count messages by status
    messages = {
        "total": message_query.count(),
        "sent": message_query.filter_by(status="sent").count(),
        "failed": message_query.filter_by(status="failed").count(),
        "pending": message_query.filter_by(status="pending").count(),
        "processing": message_query.filter_by(status="processing").count()
    }
    
    # Count bulk jobs by status
    jobs = {
        "total": job_query.count(),
        "completed": job_query.filter_by(status="completed").count(),
        "failed": job_query.filter_by(status="failed").count(),
        "pending": job_query.filter_by(status="pending").count(),
        "processing": job_query.filter_by(status="processing").count()
    }
    
    # Device status
    device = DeviceStatus.query.order_by(DeviceStatus.last_check.desc()).first()
    device_status = device.to_dict() if device else {"connected": False, "state": None}
    
    # Get time-series data for charts
    timeData = {
        "labels": [],
        "messages": [],
        "successRate": []
    }
    
    # Generate time labels and data based on time range
    if time_range == 'day':
        # Hourly data for the last 24 hours
        for i in range(23, -1, -1):
            start_time = now - timedelta(hours=i)
            end_time = now - timedelta(hours=i-1) if i > 0 else now
            
            # Add hour label
            timeData["labels"].append(start_time.strftime('%H:00'))
            
            # Count messages in this hour
            hour_messages = message_query.filter(
                Message.created_at >= start_time,
                Message.created_at < end_time
            )
            
            total = hour_messages.count()
            successful = hour_messages.filter_by(status="sent").count()
            
            timeData["messages"].append(total)
            timeData["successRate"].append(round((successful / total * 100) if total > 0 else 0))
            
    elif time_range == 'week':
        # Daily data for the last 7 days
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # Add day label
            timeData["labels"].append(day.strftime('%a'))
            
            # Count messages on this day
            day_messages = message_query.filter(
                Message.created_at >= day_start,
                Message.created_at < day_end
            )
            
            total = day_messages.count()
            successful = day_messages.filter_by(status="sent").count()
            
            timeData["messages"].append(total)
            timeData["successRate"].append(round((successful / total * 100) if total > 0 else 0))
            
    elif time_range == 'month':
        # Weekly data for the last 30 days
        for i in range(4, 0, -1):
            week_start = now - timedelta(days=i*7)
            week_end = now - timedelta(days=(i-1)*7) if i > 1 else now
            
            # Add week label
            timeData["labels"].append(f"Week {5-i}")
            
            # Count messages in this week
            week_messages = message_query.filter(
                Message.created_at >= week_start,
                Message.created_at < week_end
            )
            
            total = week_messages.count()
            successful = week_messages.filter_by(status="sent").count()
            
            timeData["messages"].append(total)
            timeData["successRate"].append(round((successful / total * 100) if total > 0 else 0))
            
    elif time_range == 'year' or time_range == 'all':
        # Monthly data for the last 12 months
        for i in range(11, -1, -1):
            month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start.replace(month=month_start.month+1) if month_start.month < 12 
                        else month_start.replace(year=month_start.year+1, month=1))
            
            # Add month label
            timeData["labels"].append(month_start.strftime('%b'))
            
            # Count messages in this month
            month_messages = message_query.filter(
                Message.created_at >= month_start,
                Message.created_at < month_end
            )
            
            total = month_messages.count()
            successful = month_messages.filter_by(status="sent").count()
            
            timeData["messages"].append(total)
            timeData["successRate"].append(round((successful / total * 100) if total > 0 else 0))
    
    return jsonify({
        "messages": messages,
        "jobs": jobs,
        "device": device_status,
        "timeData": timeData
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


@api_v1.route('/messages', methods=['GET'])
@handle_exceptions
@require_api_key
def list_messages():
    """List recent messages"""
    # Import here to avoid circular import
    from api.app import db
    
    # Get query parameters
    limit = request.args.get('limit', 10, type=int)
    sort = request.args.get('sort', 'desc', type=str)
    
    # Limit to reasonable values
    if limit > 100:
        limit = 100
    
    # Build query with appropriate sorting
    query = Message.query
    if sort.lower() == 'desc':
        query = query.order_by(Message.created_at.desc())
    else:
        query = query.order_by(Message.created_at.asc())
    
    # Execute the query with limit
    messages = query.limit(limit).all()
    
    return jsonify({
        "messages": [message.to_dict() for message in messages],
        "count": len(messages),
        "limit": limit
    })


# Define a function to register blueprints to avoid circular imports
def register_blueprints(app):
    # Register the v1 blueprint with a unique name for /api
    app.register_blueprint(api_v1, url_prefix='/api')
    
    # For backward compatibility, also register at /api/v1 with a different name
    app.register_blueprint(api_v1, url_prefix='/api/v1', name='api_v1_specific')