#!/usr/bin/env python
"""
MySQL Database Setup Script for Agily Django Project

This script helps you set up MySQL database for the Agily project.
"""

import os
import sys
import getpass
from pathlib import Path

def main():
    print("=== Agily MySQL Database Setup ===")
    print()
    
    # Get database configuration
    db_host = input("Database host (default: localhost): ").strip() or "localhost"
    db_port = input("Database port (default: 3306): ").strip() or "3306"
    db_name = input("Database name (default: agily): ").strip() or "agily"
    db_user = input("Database username (default: root): ").strip() or "root"
    db_password = getpass.getpass("Database password: ")
    
    # Create database URL
    database_url = f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Check if .env file exists
    env_file = Path("config/.env")
    if env_file.exists():
        print(f"\nWarning: {env_file} already exists!")
        overwrite = input("Do you want to overwrite it? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Create .env file
    env_content = f"""DJANGO_DEBUG=1
DJANGO_DATABASE_URL={database_url}
ENVIRONMENT=local
DJANGO_ADMIN_URL=admin/
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_SECRET_KEY=CHANGEME
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
WATCHMAN_TOKEN=CHANGEME
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//agily
SENTRY_ENABLED=False
SENTRY_DSN=http://example.com/123
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DJANGO_DEFAULT_FROM_EMAIL="agily <noreply@localhost>"
DJANGO_EMAIL_SUBJECT_PREFIX="[agily] "
DJANGO_SERVER_EMAIL="agily <noreply@localhost>"
DJANGO_ACCOUNT_ALLOW_REGISTRATION=True
USER_AGENT=agily/0.1.0
CELERY_ALWAYS_EAGER=1
"""
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Environment file created: {env_file}")
    print(f"Database URL: {database_url}")
    print()
    print("Next steps:")
    print("1. Install MySQL dependencies: pip install mysqlclient")
    print("2. Create the MySQL database:")
    print(f"   mysql -u {db_user} -p -e 'CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'")
    print("3. Run migrations: python manage.py migrate")
    print("4. Create superuser: python manage.py createsuperuser")
    print("5. Start the development server: python manage.py runserver")

if __name__ == "__main__":
    main() 