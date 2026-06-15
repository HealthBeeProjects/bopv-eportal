# Free Deployment Guide

## Recommended free option for this Flask app: PythonAnywhere

Why:
- It supports Flask apps.
- It provides a free subdomain in the format:
  https://your-username.pythonanywhere.com
- It does not require converting the app to a static website.

## Steps
1. Go to PythonAnywhere and create a free Beginner account.
2. Upload the unzipped folder.
3. Open Bash console.
4. Install requirements:
   mkvirtualenv --python=/usr/bin/python3.11 pv-env
   pip install -r requirements.txt
5. Configure environment variables:
   SECRET_KEY=your-long-random-secret
   ADMIN_EMAIL=your-admin-email
   ADMIN_PASSWORD=your-strong-admin-password
   PV_DB_PATH=/home/YOURUSERNAME/pv_eportal.db
   PUBLIC_SIGNUP_ENABLED=false
   SESSION_COOKIE_SECURE=true
6. Create a Web App:
   Web tab > Add new web app > Manual configuration > Python 3.11
7. Set the virtualenv:
   /home/YOURUSERNAME/.virtualenvs/pv-env
8. Edit WSGI file:
   import sys
   path = '/home/YOURUSERNAME/HealthBee_bOPV_EPortal_ProductionReady'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
9. Reload the app.
10. Your live link will be:
   https://YOURUSERNAME.pythonanywhere.com

## Important
Do not put patient-identifiable AEFI forms on public pages.
Use HTTPS, keep self-service signup disabled unless you have an approval workflow, and rotate the admin password through `ADMIN_PASSWORD`.
