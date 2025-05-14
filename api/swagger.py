"""
Swagger documentation for AdbSms API
"""
from flask import Blueprint, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

# Create a blueprint for API documentation
swagger_bp = Blueprint('swagger', __name__)

# Swagger UI configuration
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI
API_URL = '/api/swagger.json'  # Our API url

# Register Swagger UI blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "AdbSms API Documentation"
    }
)

@swagger_bp.route('/swagger.json')
def swagger_json():
    """Return Swagger specification"""
    return jsonify({
        "swagger": "2.0",
        "info": {
            "title": "AdbSms API",
            "description": "High-performance REST API for sending SMS messages via ADB",
            "version": "0.2.0",
            "contact": {
                "email": "ammlyf@gmail.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://github.com/Ammly/AdbSms/blob/main/LICENSE"
            }
        },
        "host": "localhost:5000",
        "basePath": "/api",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        },
        "security": [
            {
                "ApiKeyAuth": []
            }
        ],
        "tags": [
            {
                "name": "device",
                "description": "Device status operations"
            },
            {
                "name": "sms",
                "description": "SMS message operations"
            },
            {
                "name": "bulk",
                "description": "Bulk SMS operations"
            },
            {
                "name": "stats",
                "description": "API statistics"
            }
        ],
        "paths": {
            "/device/status": {
                "get": {
                    "tags": ["device"],
                    "summary": "Get device connection status",
                    "description": "Returns the current status of connected Android devices",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "$ref": "#/definitions/DeviceStatus"
                            }
                        }
                    }
                }
            },
            "/device/check": {
                "post": {
                    "tags": ["device"],
                    "summary": "Force check device connection",
                    "description": "Initiates a new device check",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "Check initiated",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "task_id": {"type": "string"},
                                    "message": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            "/sms": {
                "post": {
                    "tags": ["sms"],
                    "summary": "Send an SMS message",
                    "description": "Queues a new SMS message for sending",
                    "consumes": ["application/json"],
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "body",
                            "name": "body",
                            "description": "SMS details",
                            "required": True,
                            "schema": {
                                "$ref": "#/definitions/SMSRequest"
                            }
                        }
                    ],
                    "responses": {
                        "202": {
                            "description": "Message queued successfully",
                            "schema": {
                                "$ref": "#/definitions/SMSResponse"
                            }
                        },
                        "400": {
                            "description": "Invalid input"
                        }
                    }
                }
            },
            "/sms/{messageId}": {
                "get": {
                    "tags": ["sms"],
                    "summary": "Find message by ID",
                    "description": "Returns a single SMS message",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "path",
                            "name": "messageId",
                            "description": "ID of message to return",
                            "required": True,
                            "type": "integer",
                            "format": "int64"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "$ref": "#/definitions/Message"
                            }
                        },
                        "404": {
                            "description": "Message not found"
                        }
                    }
                }
            },
            "/sms/bulk": {
                "post": {
                    "tags": ["bulk"],
                    "summary": "Upload CSV for bulk SMS",
                    "description": "Uploads a CSV file with phone numbers and messages",
                    "consumes": ["multipart/form-data"],
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "formData",
                            "name": "file",
                            "type": "file",
                            "description": "CSV file with phone_number and message columns",
                            "required": True
                        },
                        {
                            "in": "formData",
                            "name": "sim_id",
                            "type": "integer",
                            "default": 3,
                            "description": "SIM card ID"
                        },
                        {
                            "in": "formData",
                            "name": "delay",
                            "type": "number",
                            "format": "float",
                            "default": 1.0,
                            "description": "Delay between messages (seconds)"
                        }
                    ],
                    "responses": {
                        "202": {
                            "description": "CSV file queued for processing",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "task_id": {"type": "string"},
                                    "message": {"type": "string"}
                                }
                            }
                        },
                        "400": {
                            "description": "Invalid input"
                        }
                    }
                }
            },
            "/bulk/{jobId}": {
                "get": {
                    "tags": ["bulk"],
                    "summary": "Get bulk job status",
                    "description": "Returns the status of a bulk SMS job",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "path",
                            "name": "jobId",
                            "description": "ID of job to return",
                            "required": True,
                            "type": "integer",
                            "format": "int64"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "$ref": "#/definitions/BulkJob"
                            }
                        },
                        "404": {
                            "description": "Job not found"
                        }
                    }
                }
            },
            "/bulk": {
                "get": {
                    "tags": ["bulk"],
                    "summary": "List bulk jobs",
                    "description": "Returns a list of bulk SMS jobs",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "query",
                            "name": "page",
                            "description": "Page number",
                            "type": "integer",
                            "default": 1
                        },
                        {
                            "in": "query",
                            "name": "per_page",
                            "description": "Items per page",
                            "type": "integer",
                            "default": 10
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "pages": {"type": "integer"},
                                    "current_page": {"type": "integer"},
                                    "per_page": {"type": "integer"},
                                    "jobs": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/definitions/BulkJob"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/stats": {
                "get": {
                    "tags": ["stats"],
                    "summary": "Get API statistics",
                    "description": "Returns statistics about SMS messages and jobs",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "$ref": "#/definitions/Stats"
                            }
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "tags": ["stats"],
                    "summary": "API health check",
                    "description": "Returns health status of the API",
                    "produces": ["application/json"],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "timestamp": {"type": "string"},
                                    "version": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "definitions": {
            "DeviceStatus": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "device_id": {"type": "string"},
                    "connected": {"type": "boolean"},
                    "state": {"type": "string"},
                    "last_check": {"type": "string", "format": "date-time"}
                }
            },
            "SMSRequest": {
                "type": "object",
                "required": ["phone_number", "content"],
                "properties": {
                    "phone_number": {"type": "string"},
                    "content": {"type": "string"},
                    "sim_id": {"type": "integer", "default": 3}
                }
            },
            "SMSResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message_id": {"type": "integer"},
                    "task_id": {"type": "string"},
                    "url": {"type": "string"}
                }
            },
            "Message": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "phone_number": {"type": "string"},
                    "content": {"type": "string"},
                    "sim_id": {"type": "integer"},
                    "status": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "sent_at": {"type": "string", "format": "date-time"}
                }
            },
            "BulkJob": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "filename": {"type": "string"},
                    "sim_id": {"type": "integer"},
                    "delay": {"type": "number"},
                    "status": {"type": "string"},
                    "total_messages": {"type": "integer"},
                    "successful_messages": {"type": "integer"},
                    "failed_messages": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "string", "format": "date-time"},
                    "task_id": {"type": "string"},
                    "progress": {"type": "number"}
                }
            },
            "Stats": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer"},
                            "sent": {"type": "integer"},
                            "failed": {"type": "integer"},
                            "pending": {"type": "integer"},
                            "processing": {"type": "integer"}
                        }
                    },
                    "jobs": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer"},
                            "completed": {"type": "integer"},
                            "failed": {"type": "integer"},
                            "pending": {"type": "integer"},
                            "processing": {"type": "integer"}
                        }
                    },
                    "device": {
                        "$ref": "#/definitions/DeviceStatus"
                    }
                }
            }
        }
    })