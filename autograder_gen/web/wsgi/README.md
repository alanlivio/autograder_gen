# WSGI Deployment Guide

This directory provides WSGI integration for deploying the AutograderGen Web UI using production WSGI servers such as **Apache mod_wsgi**, **Gunicorn**, or **uWSGI**.

## 1. Production Deployment from Installed Package (Recommended)

When `autograder_gen` is installed via `pip install autograder_gen`, all web components and WSGI scripts are installed into the Python environment.

### Option A: Gunicorn (Standalone WSGI Server)

Run `gunicorn` directly with the application callable:

```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 autograder_gen.web:app
```

### Option B: Apache with `mod_wsgi`

1. **Configure Apache VirtualHost:**

   Add the following directives to your Apache site configuration (e.g. `/etc/apache2/sites-available/autograder.conf`):

   ```apache
   <VirtualHost *:80>
       ServerName autograder.example.com

       # Virtual environment (if used)
       WSGIDaemonProcess autograder processes=2 threads=15 python-home=/path/to/venv
       WSGIProcessGroup autograder

       # Point directly to the installed WSGI script
       WSGIScriptAlias / /path/to/venv/lib/python3.X/site-packages/autograder_gen/web/wsgi/autograder.wsgi

       # Serve static files directly via Apache
       Alias /static /path/to/venv/lib/python3.X/site-packages/autograder_gen/web/static
       <Directory /path/to/venv/lib/python3.X/site-packages/autograder_gen/web/static>
           Require all granted
       </Directory>

       <Directory /path/to/venv/lib/python3.X/site-packages/autograder_gen/web/wsgi>
           <Files autograder.wsgi>
               Require all granted
           </Files>
       </Directory>

       ErrorLog ${APACHE_LOG_DIR}/autograder_error.log
       CustomLog ${APACHE_LOG_DIR}/autograder_access.log combined
   </VirtualHost>
   ```

3. **Alternative: Standalone `/var/www/autograder/autograder.wsgi` file**

   If you prefer having a dedicated WSGI file in `/var/www/autograder/`, simply create `/var/www/autograder/autograder.wsgi` containing:

   ```python
   import logging
   import sys

   logging.basicConfig(stream=sys.stderr)

   from autograder_gen.web.app import app as application
   ```

## 2. Local Development & Workspace Deployment

For testing the WSGI setup inside this repository without a global installation:

```bash
make -C autograder_gen/web serve
```

This target creates the local `/var/www/autograder` symlinks and runs the development Gunicorn server on `127.0.0.1:8000`.
