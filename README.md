# HealthBee bOPV E-Portal - Production Ready Prototype

This package includes an updated bOPV PV e-portal with the AEFI statistical details added.

## Added from AEFI_REPORT_UPDATED.docx
- N = 70 immunized children
- 62 active AEFI cases
- 8 afebrile children
- 0 serious AEFI
- Gender distribution
- Age cohort distribution
- Symptom frequency
- Gender crosstab
- Anonymized representative case extract
- Reporter/vaccinator station list
- Secure source document download

## Important Privacy Note
Filled AEFI forms contain child-level identifiable information. They are not included in the public website pages. Keep filled forms in secure controlled storage only. The website shows aggregate and anonymized information.

## First-Run Configuration

The app requires a real secret key before it will start.

Create a local `.env` file from `.env.example`, then set:
- `SECRET_KEY` to a long random value.
- `ADMIN_EMAIL` and `ADMIN_PASSWORD` to create or reset the bootstrap admin account.
- `PUBLIC_SIGNUP_ENABLED=false` for controlled PV access.
- `SESSION_COOKIE_SECURE=true` when deployed behind HTTPS.

If the database is empty and `ADMIN_EMAIL` / `ADMIN_PASSWORD` are missing, startup fails instead of creating a known demo account.

## Run Locally
Copy and edit the environment example first:

```powershell
Copy-Item .env.example .env
```

Install and run:

```powershell
pip install -r requirements.txt
python app.py
```

Then open:
http://127.0.0.1:5000

## Free Hosting Option: PythonAnywhere
PythonAnywhere Beginner plan can host one web app at:
https://your-username.pythonanywhere.com

Basic steps:
1. Create a free PythonAnywhere Beginner account.
2. Upload this unzipped folder.
3. Open Bash console.
4. Run:
   mkvirtualenv --python=/usr/bin/python3.11 pv-env
   pip install -r requirements.txt
5. Set environment variables for `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `PV_DB_PATH`, `PUBLIC_SIGNUP_ENABLED`, and `SESSION_COOKIE_SECURE`.
6. Web tab > Add new web app > Manual configuration > Python 3.11.
7. Set source code path to the uploaded folder.
8. Set virtualenv path to pv-env.
9. Edit WSGI file and add:
   import sys
   path = '/home/YOURUSERNAME/HealthBee_bOPV_EPortal_ProductionReady'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
10. Reload web app.
11. Your live link will be:
    https://YOURUSERNAME.pythonanywhere.com

## Google Search
After deployment:
1. Open Google Search Console.
2. Add your pythonanywhere.com URL or custom domain.
3. Submit sitemap if you add one.
4. Wait for indexing.
