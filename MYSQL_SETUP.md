# MySQL Setup for Agily

This guide will help you set up MySQL as the database for your Agily Django project.

## Prerequisites

1. **Install MySQL Server**
   - **Windows**: Download and install MySQL from [mysql.com](https://dev.mysql.com/downloads/mysql/)
   - **macOS**: `brew install mysql`
   - **Ubuntu/Debian**: `sudo apt-get install mysql-server`
   - **CentOS/RHEL**: `sudo yum install mysql-server`

2. **Install MySQL Python Driver**
   ```bash
   pip install mysqlclient
   ```

## Quick Setup

Run the automated setup script:
```bash
python setup_mysql.py
```

This script will:
- Prompt you for database credentials
- Create a `config/.env` file with the correct database URL
- Provide next steps for database creation and migration

## Manual Setup

### 1. Create MySQL Database

Connect to MySQL and create the database:
```sql
mysql -u root -p
CREATE DATABASE agily CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'agily_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON agily.* TO 'agily_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2. Configure Environment

Create or update `config/.env`:
```env
DJANGO_DEBUG=1
DJANGO_DATABASE_URL=mysql://agily_user:your_password@localhost:3306/agily
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
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Start Development Server

```bash
python manage.py runserver
```

## Troubleshooting

### Common Issues

1. **mysqlclient installation fails**
   - **Windows**: Install Visual Studio Build Tools
   - **macOS**: Install Xcode Command Line Tools
   - **Linux**: Install `python3-dev` and `libmysqlclient-dev`

2. **Connection refused**
   - Ensure MySQL service is running
   - Check if MySQL is listening on the correct port (default: 3306)

3. **Access denied**
   - Verify username and password
   - Check if user has proper privileges on the database

4. **Character set issues**
   - The configuration already includes `utf8mb4` charset
   - If you encounter issues, ensure your MySQL server supports utf8mb4

### MySQL Configuration

For optimal performance, consider adding these to your MySQL configuration:

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
default-storage-engine = InnoDB
innodb_buffer_pool_size = 256M
```

## Production Considerations

For production deployment:

1. **Use environment variables** for sensitive data
2. **Set up proper MySQL backups**
3. **Configure connection pooling** if needed
4. **Use a dedicated MySQL user** with minimal privileges
5. **Enable SSL connections** for security

## Migration from SQLite

If you're migrating from SQLite to MySQL:

1. **Backup your data** from SQLite
2. **Export data** using Django's dumpdata command
3. **Set up MySQL** as described above
4. **Run migrations** to create tables
5. **Import data** using Django's loaddata command

```bash
# Export from SQLite
python manage.py dumpdata > data_backup.json

# After setting up MySQL
python manage.py loaddata data_backup.json
``` 