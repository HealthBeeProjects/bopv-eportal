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
5. Create a Web App:
   Web tab > Add new web app > Manual configuration > Python 3.11
6. Set the virtualenv:
   /home/YOURUSERNAME/.virtualenvs/pv-env
7. Edit WSGI file:
   import sys
   path = '/home/YOURUSERNAME/HealthBee_bOPV_EPortal_ProductionReady'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
8. Reload the app.
9. Your live link will be:
   https://YOURUSERNAME.pythonanywhere.com

## Important
Do not put patient-identifiable AEFI forms on public pages.
Use HTTPS and change the demo password before real use.
