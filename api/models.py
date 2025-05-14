"""
Database models for AdbSms API
"""
from datetime import datetime
from api.app import db


class Message(db.Model):
    """Model for SMS messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sim_id = db.Column(db.Integer, default=3)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Message {self.id}: {self.phone_number}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'content': self.content,
            'sim_id': self.sim_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }


class BulkMessageJob(db.Model):
    """Model for tracking bulk SMS jobs"""
    __tablename__ = 'bulk_message_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=True)
    sim_id = db.Column(db.Integer, default=3)
    delay = db.Column(db.Float, default=1.0)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    total_messages = db.Column(db.Integer, default=0)
    successful_messages = db.Column(db.Integer, default=0)
    failed_messages = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    task_id = db.Column(db.String(36), nullable=True)  # Celery task ID
    
    def __repr__(self):
        return f"<BulkMessageJob {self.id}: {self.status}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'sim_id': self.sim_id,
            'delay': self.delay,
            'status': self.status,
            'total_messages': self.total_messages,
            'successful_messages': self.successful_messages,
            'failed_messages': self.failed_messages,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'task_id': self.task_id
        }


class DeviceStatus(db.Model):
    """Model for tracking ADB device connection status"""
    __tablename__ = 'device_status'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=True)
    connected = db.Column(db.Boolean, default=False)
    state = db.Column(db.String(20), nullable=True)  # device, unauthorized, offline
    last_check = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeviceStatus {self.device_id}: {self.state}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'connected': self.connected,
            'state': self.state,
            'last_check': self.last_check.isoformat()
        }