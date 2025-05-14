"""
Celery tasks for AdbSms - High-performance implementation
"""
import os
import sys
import pandas as pd
import time
import logging
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import concurrent.futures
from typing import List, Dict, Any, Tuple

from celery.signals import task_success, task_failure, task_retry, task_prerun, task_postrun
from celery.utils.log import get_task_logger

from api.celery_app import celery
from flask import current_app

# Setup logging
logger = get_task_logger(__name__)

# Add project root to path to import main.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main

# Import app but avoid circular imports
from api.app import app as flask_app

# Enhanced Task monitoring setup with improved app context handling
@task_success.connect
def task_success_handler(sender=None, **kwargs):
    logger.info(f"Task {sender.name}[{sender.request.id}] succeeded")

@task_failure.connect
def task_failure_handler(sender=None, exception=None, **kwargs):
    logger.error(f"Task {sender.name}[{sender.request.id}] failed: {exception}")

@task_retry.connect
def task_retry_handler(sender=None, reason=None, **kwargs):
    logger.warning(f"Task {sender.name}[{sender.request.id}] retried: {reason}")

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Ensure application context is available for tasks"""
    logger.debug(f"Setting up app context for task {task.name}[{task_id}]")
    # Note: The actual app context is created within each task function

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, retval=None, state=None, **kwargs):
    """Clean up resources after task execution"""
    logger.debug(f"Cleaning up after task {task.name}[{task_id}], state: {state}")
    # Flask app context is automatically popped at the end of the 'with' block in each task

@celery.task(bind=True, name="api.tasks.send_sms_task", 
             max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def send_sms_task(self, message_id):
    """
    Task to send a single SMS message
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import Message, DeviceStatus
        
        message = Message.query.get(message_id)
        if not message:
            logger.error(f"Message not found: {message_id}")
            return {"status": "error", "error": "Message not found"}
        
        message.status = "processing"
        db.session.commit()
        
        try:
            # First verify ADB connection
            device_connected = main.check_adb_connection()
            if not device_connected:
                logger.error(f"ADB connection failed for SMS {message_id}. No device connected.")
                message.status = "failed"
                db.session.commit()
                # Update device status
                device_status = DeviceStatus.query.first()
                if not device_status:
                    device_status = DeviceStatus()
                device_status.connected = False
                device_status.last_check = datetime.utcnow()
                db.session.add(device_status)
                db.session.commit()
                # Retry with exponential backoff
                raise Exception("No ADB device connected")

            # Log the command we're about to run
            logger.info(f"Sending SMS to {message.phone_number} with SIM ID {message.sim_id}")
            
            # Use the existing send_sms function from main.py
            result = main.send_sms(
                phone_number=message.phone_number,
                message=message.content,
                sim_id=message.sim_id
            )
            
            if result:
                message.status = "sent"
                message.sent_at = datetime.utcnow()
                logger.info(f"Successfully sent SMS {message_id} to {message.phone_number}")
            else:
                message.status = "failed"
                logger.error(f"Failed to send SMS {message_id} to {message.phone_number}")
            
            db.session.commit()
            return {
                "status": "success" if result else "error",
                "message_id": message_id,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None
            }
        except Exception as e:
            logger.error(f"Error sending SMS {message_id}: {str(e)}")
            # Get detailed error info 
            import traceback
            logger.error(f"Exception details: {traceback.format_exc()}")
            
            message.status = "failed"
            db.session.commit()
            # Re-raise the exception for retry mechanism
            raise


@celery.task(bind=True, name="api.tasks.process_bulk_sms_job")
def process_bulk_sms_job(self, job_id):
    """
    Task to process a bulk SMS job
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import BulkMessageJob, Message
        
        job = BulkMessageJob.query.get(job_id)
        if not job:
            logger.error(f"Job not found: {job_id}")
            return {"status": "error", "error": "Job not found"}
        
        job.status = "processing"
        db.session.commit()
        
        try:
            # Load CSV into DataFrame
            df = pd.read_csv(
                job.filename,
                dtype={
                    'phone_number': str,
                    'message': str
                }
            )
            
            # Update total messages count
            total_messages = len(df)
            job.total_messages = total_messages
            db.session.commit()
            
            # Process messages in chunks (batches) for better performance
            success_count = 0
            failure_count = 0
            
            # Create records for all messages upfront
            batch_size = 100  # Process in chunks of 100 messages
            message_ids = []
            
            # Process in batches for better performance
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                batch_ids = []

                # Create records for this batch
                for _, row in batch.iterrows():
                    phone_number = str(row['phone_number'])
                    content = str(row['message'])

                    # Create message record
                    message = Message(
                        phone_number=phone_number,
                        content=content,
                        sim_id=job.sim_id,
                        status='pending'
                    )

                    db.session.add(message)
                    
                # Commit the batch    
                db.session.commit()
                
                # Collect IDs from the batch
                for _, row in batch.iterrows():
                    phone_number = str(row['phone_number'])
                    message = Message.query.filter_by(
                        phone_number=phone_number,
                        status='pending'
                    ).order_by(Message.created_at.desc()).first()
                    
                    if message:
                        batch_ids.append(message.id)
                
                # Queue the tasks with appropriate delays
                for idx, msg_id in enumerate(batch_ids):
                    # Schedule with staggered delays to avoid flooding
                    countdown = job.delay * idx
                    send_sms_task.apply_async(args=[msg_id], countdown=countdown)
                
                # Update message_ids list
                message_ids.extend(batch_ids)
                
                # Update job progress
                job.successful_messages = 0  # Will be updated as tasks complete
                job.failed_messages = 0  # Will be updated as tasks complete
                job.total_messages = len(message_ids)
                db.session.commit()
                
                # Monitor progress periodically
                time.sleep(2)  # Brief pause between batches
            
            # The job is now queued, we'll mark it as 'processing'
            # Individual message statuses will be updated by their respective tasks
            job.status = "processing"
            db.session.commit()
            
            # Start a background task to monitor this job
            monitor_bulk_job.apply_async(args=[job_id], countdown=5)
            
            return {
                "status": "processing",
                "job_id": job_id,
                "total_messages": len(message_ids)
            }
            
        except Exception as e:
            logger.error(f"Error in bulk SMS job {job_id}: {str(e)}")
            job.status = "failed"
            job.failed_messages = job.total_messages
            db.session.commit()
            
            return {
                "status": "error",
                "job_id": job_id,
                "error": str(e)
            }


@celery.task(bind=True, name="api.tasks.monitor_bulk_job")
def monitor_bulk_job(self, job_id):
    """
    Monitor the progress of a bulk SMS job and update its status
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import BulkMessageJob, Message
        
        job = BulkMessageJob.query.get(job_id)
        if not job or job.status not in ['processing', 'pending']:
            return
        
        # Count messages by status
        successful = Message.query.filter_by(
            status="sent",
            sim_id=job.sim_id
        ).filter(
            Message.created_at >= job.created_at
        ).count()
        
        failed = Message.query.filter_by(
            status="failed",
            sim_id=job.sim_id
        ).filter(
            Message.created_at >= job.created_at
        ).count()
        
        pending = Message.query.filter_by(
            status="pending",
            sim_id=job.sim_id
        ).filter(
            Message.created_at >= job.created_at
        ).count()
        
        processing = Message.query.filter_by(
            status="processing",
            sim_id=job.sim_id
        ).filter(
            Message.created_at >= job.created_at
        ).count()
        
        # Update job status
        job.successful_messages = successful
        job.failed_messages = failed
        
        # Check if all messages have been processed
        if pending == 0 and processing == 0:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            db.session.commit()
        else:
            # Schedule another check in a few seconds
            db.session.commit()
            monitor_bulk_job.apply_async(args=[job_id], countdown=5)


@celery.task(name="api.tasks.check_adb_connection_task")
def check_adb_connection_task():
    """
    Task to check ADB connection status and update the database
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import DeviceStatus
        
        # Use the existing check_adb_connection function
        connected = main.check_adb_connection()
        
        # Get device details if connected
        device_id = None
        state = None
        
        if connected:
            try:
                result = subprocess.run(
                    ["adb", "devices"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse the first device line
                    device_line = lines[1].strip().split()
                    if len(device_line) >= 2:
                        device_id = device_line[0]
                        state = device_line[1]
            except Exception as e:
                logger.error(f"Error getting device details: {e}")
        
        # Update or create device status
        device_status = DeviceStatus.query.first()
        if not device_status:
            device_status = DeviceStatus()
        
        device_status.device_id = device_id
        device_status.connected = connected
        device_status.state = state
        device_status.last_check = datetime.utcnow()
        
        db.session.add(device_status)
        db.session.commit()
        
        return {
            "connected": connected,
            "device_id": device_id,
            "state": state,
            "last_check": device_status.last_check.isoformat()
        }


@celery.task(bind=True, name="api.tasks.process_csv_upload")
def process_csv_upload(self, temp_file_path, original_filename, sim_id, delay):
    """
    Process an uploaded CSV file for bulk SMS
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import BulkMessageJob
        
        try:
            # Validate CSV file structure
            df = pd.read_csv(
                temp_file_path,
                dtype={
                    'phone_number': str,
                    'message': str
                }
            )
            
            # Check required columns
            if 'phone_number' not in df.columns or 'message' not in df.columns:
                raise ValueError("CSV must have 'phone_number' and 'message' columns")
            
            # Check data integrity
            if df.empty:
                raise ValueError("CSV file is empty")
                
            if df['phone_number'].isna().any() or df['message'].isna().any():
                raise ValueError("CSV contains empty phone numbers or messages")
                
            # Basic validation
            row_count = len(df)
            if row_count > 1000:
                raise ValueError(f"CSV has {row_count} rows, exceeding the 1000 row limit")
            
            # Create a job entry
            job = BulkMessageJob(
                filename=temp_file_path,
                sim_id=sim_id,
                delay=delay,
                status="pending",
                task_id=self.request.id,
                total_messages=row_count
            )
            
            db.session.add(job)
            db.session.commit()
            
            # Start the bulk SMS processing
            process_bulk_sms_job.delay(job.id)
            
            return {
                "status": "accepted",
                "job_id": job.id,
                "total_messages": row_count
            }
        except Exception as e:
            logger.error(f"Error processing CSV upload: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


@celery.task(name="api.tasks.clean_temp_files")
def clean_temp_files():
    """
    Clean up temporary files created by the application
    Run periodically to prevent disk space issues
    """
    # Use the app context to perform database operations
    with flask_app.app_context():
        # Import inside the task to avoid circular imports
        from api.app import db
        from api.models import BulkMessageJob
        
        try:
            # Get all completed jobs older than 24 hours
            cutoff = datetime.utcnow() - pd.Timedelta(days=1)
            old_jobs = BulkMessageJob.query.filter(
                BulkMessageJob.status.in_(['completed', 'failed']),
                BulkMessageJob.created_at < cutoff
            ).all()
            
            count = 0
            for job in old_jobs:
                if job.filename and os.path.exists(job.filename):
                    try:
                        os.remove(job.filename)
                        # Also try to remove parent temp directory if empty
                        parent_dir = os.path.dirname(job.filename)
                        if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
                        count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete {job.filename}: {e}")
                    
            return {
                "status": "success",
                "files_deleted": count
            }
        except Exception as e:
            logger.error(f"Error cleaning temp files: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }