"""
Celery configuration for AdbSms - High-performance implementation
"""
import os
from celery import Celery
from kombu import Exchange, Queue

# Define default queue
default_exchange = Exchange('default', type='direct')
priority_exchange = Exchange('priority', type='direct')

# Define queues with their priorities
task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('priority', priority_exchange, routing_key='priority'),
    Queue('bulk', default_exchange, routing_key='bulk'),
    Queue('monitor', default_exchange, routing_key='monitor'),
    Queue('maintenance', default_exchange, routing_key='maintenance'),
)

# Initialize Celery
celery = Celery(
    'adbsms',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    include=['api.tasks']
)

# Configuration
celery.conf.update(
    # Result backend settings
    result_expires=3600,  # results expire after 1 hour
    
    # Task execution settings
    worker_prefetch_multiplier=1,  # Fetch only one task at a time
    task_acks_late=True,  # Acknowledge task after execution, not before
    task_time_limit=300,  # Kill task if it runs longer than 5 minutes
    task_soft_time_limit=240,  # Raise exception if task runs longer than 4 minutes
    
    # Queue settings
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    task_queues=task_queues,
    
    # Concurrency settings - adjusted for ADB operations
    worker_concurrency=4,  # Limit concurrent tasks
    
    # Task routes for different task types
    task_routes={
        # Device check tasks (higher priority)
        'api.tasks.check_adb_connection_task': {
            'queue': 'priority',
            'routing_key': 'priority',
        },
        # Single SMS tasks
        'api.tasks.send_sms_task': {
            'queue': 'default',
            'routing_key': 'default',
        },
        # Bulk tasks (lower priority)
        'api.tasks.process_bulk_sms_job': {
            'queue': 'bulk',
            'routing_key': 'bulk',
        },
        'api.tasks.process_csv_upload': {
            'queue': 'bulk',
            'routing_key': 'bulk',
        },
        # Job monitoring tasks
        'api.tasks.monitor_bulk_job': {
            'queue': 'monitor',
            'routing_key': 'monitor',
        },
        # Maintenance tasks
        'api.tasks.clean_temp_files': {
            'queue': 'maintenance',
            'routing_key': 'maintenance',
        },
    },
)

# Beat schedule for periodic tasks
celery.conf.beat_schedule = {
    'check-adb-connection-every-hour': {
        'task': 'api.tasks.check_adb_connection_task',
        'schedule': 3600.0,  # seconds (1 hour)
    },
    'clean-temp-files-daily': {
        'task': 'api.tasks.clean_temp_files',
        'schedule': 86400.0,  # seconds (24 hours)
    },
}

if __name__ == '__main__':
    celery.start()