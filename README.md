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

## Demo Login
Email: admin@healthbee.pk
Password: ChangeMe123!

Change this before production use.

## Run Locally
pip install -r requirements.txt
python app.py

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
5. Web tab > Add new web app > Manual configuration > Python 3.11.
6. Set source code path to the uploaded folder.
7. Set virtualenv path to pv-env.
8. Edit WSGI file and add:
   import sys
   path = '/home/YOURUSERNAME/HealthBee_bOPV_EPortal_ProductionReady'
   if path not in sys.path:
       sys.path.insert(0, path)
   from app import app as application
9. Reload web app.
10. Your live link will be:
    https://YOURUSERNAME.pythonanywhere.com

## Google Search
After deployment:
1. Open Google Search Console.
2. Add your pythonanywhere.com URL or custom domain.
3. Submit sitemap if you add one.
4. Wait for indexing.
