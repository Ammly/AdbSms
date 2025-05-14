"""
Database migration script for AdbSms
"""
import os
import sys

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.app import app, db

migrate = Migrate(app, db)
manager = Manager(app)

# Add the db command
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()