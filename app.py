from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3
import csv
import io
import os

APP_NAME = "bOPV E-Portal"
DB_PATH = os.environ.get("PV_DB_PATH", "pv_eportal.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
app = Flask(__name__)
app.secret_key = SECRET_KEY

DEFAULT_ADMIN_EMAIL = "admin@healthbee.pk"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"

AEFI_SUMMARY = {
    "total_children": 70,
    "active_aefi": 62,
    "active_aefi_percent": 88.6,
    "afebrile": 8,
    "afebrile_percent": 11.4,
    "saefi": 0,
    "classification": "Category A: transient, non-serious, expected bOPV-related reactions",
    "most_prevalent": "Fever / Pyrexia"
}

GENDER_DISTRIBUTION = [
    {"gender": "Male", "n": 43, "percent": 61.4},
    {"gender": "Female", "n": 27, "percent": 38.6},
]

AGE_STATS = [
    ("N Valid", "70", "Full cohort analyzed"),
    ("Mean", "22.29 months", "Average age approximately 1 year 10 months"),
    ("Median", "22.00 months", "Midpoint of distribution"),
    ("Standard Deviation", "10.95 months", "Moderate spread around mean"),
    ("Minimum", "0.50 months", "Youngest immunized child"),
    ("Maximum", "58.00 months", "Oldest immunized child"),
    ("Q1", "16.00 months", "Lower quartile boundary"),
    ("Q3", "28.00 months", "Upper quartile boundary"),
    ("IQR", "12.00 months", "Interquartile range"),
]

AGE_CATEGORIES = [
    ("Infants <= 11 months", 11, 15.7),
    ("Toddlers 12-35 months", 53, 75.7),
    ("Older Pediatric 36-60 months", 5, 7.1),
    ("Missing / Outlier", 1, 1.4),
]

SYMPTOM_FREQUENCY = [
    ("Fever / Pyrexia", 37, 52.9, 59.7),
    ("Vomiting", 11, 15.7, 17.7),
    ("Diarrhea", 10, 14.3, 16.1),
    ("Flu Symptoms / Coryza", 4, 5.7, 6.5),
    ("Afebrile / No Symptoms", 8, 11.4, None),
]

GENDER_CROSSTAB = [
    ("Fever / Pyrexia", 21, 16, 37, 52.9),
    ("Vomiting", 8, 3, 11, 15.7),
    ("Diarrhea", 8, 2, 10, 14.3),
    ("Flu Symptoms / Coryza", 1, 3, 4, 5.7),
    ("Afebrile / No Symptoms", 5, 3, 8, 11.4),
]

STATIONS = [
"District Mianwali EPI Centre","District D.I. Khan EPI Centre","Rawalakot","Rawalakot",
"District EPI Centre, Rawalpindi","Rawalakot","Mansehra, BHU Centre","District EPI Centre, Rawalpindi",
"Karak, BHU Centre","District EPI Centre, Rawalpindi","Karak, BHU Centre","District EPI Centre, Rawalpindi",
"District UC 46 RWP, EPI Centre","School, Charsadda","D.H. Sheikhupura EPI Centre",
"Bakery Chowk UC EPI Centre Punjab RWP","School, Kohat","Vaccination Centre, Dena",
"Sukkur, District Health Centre","District Peshawar, Peshawar Town 1 EPI Centre KPK",
"District WFCU Centre, EPI D.I. Khan","District D.I. Khan, WFCU Centre","D.I. Khan District Centre",
"MCH Model Colony","Union Council Dhaman Siyedan, Rawalpindi EPI Centre","Bajur","Rawalpindi, UC No. 7",
"Bhakkar, District EPI Centre","Malir, Karachi","UC 45 EPI Centre, RWP","District Chakwal, EPI Centre",
"District EPI Centre, Rawalpindi","Bajour","District EPI Centre, Rawalpindi","Nowshera, UC No. 17",
"Committee Chowk EPI Centre, RWP Punjab","District EPI Centre, Rawalpindi","BHU Behial","CD Karim Pura, Peshawar",
"District EPI Centre, Malir","UC-136 Sitara Colony, Nishtar Town, Lahore","D. EPI, RWP","K.V. Site Hospital",
"MCH Saleem Colony","CD Bughdalo, Mardan","UC-99, Gulberg Town","Urban Health Centre, Malir",
"Polio Vaccination Centre, Gulistan Colony","G. Khan 03","UC No. 17, RWP","District EPI Centre, Quetta",
"EPI Centre, Islamabad","Rawalpindi, UC No. 9","MCH Nazimabad","District EPI Centre, Rawalpindi",
"Sialkot, BHU","District EPI Centre, Rawalpindi","District EPI Centre, Chakwal","EPI Centre, District Mianwali",
"District EPI Centre, Rawalpindi","District Khanewal EPI Centre","UC 19, Satellite Town, Rawalpindi EPI Centre",
"District Pakh EPI Centre, Khyber Pakhtunkhwa","D.C. No. 23, EPI Centre, RWP",
"District R.P.K. EPI Centre, D.I. Khan","RWP Town EPI Centre, Punjab","District Nowshera EPI Centre, KPK",
"Khanpur, EPI Centre","Govt. Dispensary, Landhi","District EPI Centre, Rawalpindi"
]

ANON_CASE_EXTRACT = [
    ("Case 001", "M", "28", "Feb-2025", "Fever", "Afebrile"),
    ("Case 002", "F", "0.5", "Nov-2024", "Fever", "Afebrile"),
    ("Case 003", "F", "8.8", "Dec-2024", "Fever", "Afebrile"),
    ("Case 004", "F", "22", "Feb-2025", "Vomiting", "Afebrile"),
    ("Case 005", "M", "16", "Nov-2024", "Diarrhea", "Afebrile"),
    ("Case 006", "F", "22", "Nov-2024", "Flu", "Afebrile"),
    ("Case 007", "M", "28", "Dec-2024", "Fever", "Afebrile"),
    ("Case 008", "M", "28", "Oct-2024", "Vomiting", "Afebrile"),
    ("Case 009", "F", "22", "Oct-2024", "Afebrile", "Afebrile"),
    ("Case 010", "F", "52", "Apr-2025", "Fever", "Afebrile"),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'PV Officer',
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_no TEXT UNIQUE NOT NULL,
        date_received TEXT NOT NULL,
        report_type TEXT,
        source_country TEXT,
        case_status TEXT,
        patient_initials TEXT NOT NULL,
        age TEXT,
        gender TEXT,
        special_population TEXT,
        suspected_product TEXT NOT NULL,
        batch_no TEXT,
        dose TEXT,
        route TEXT,
        indication TEXT,
        administration_date TEXT,
        event_term TEXT NOT NULL,
        onset_date TEXT,
        seriousness TEXT NOT NULL,
        seriousness_criteria TEXT,
        outcome TEXT,
        expectedness TEXT,
        causality TEXT,
        followup_required TEXT,
        reporter_name TEXT NOT NULL,
        reporter_qualification TEXT,
        reporter_contact TEXT,
        facility_city TEXT,
        station_name TEXT,
        narrative TEXT,
        created_by TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        entity TEXT,
        entity_id TEXT,
        details TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rmp_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        safety_concern TEXT NOT NULL,
        category TEXT NOT NULL,
        monitoring_activity TEXT,
        risk_minimization TEXT,
        escalation_trigger TEXT,
        status TEXT DEFAULT 'Active'
    )
    """)
    cur.execute("SELECT COUNT(*) AS count FROM users")
    if cur.fetchone()["count"] == 0:
        cur.execute(
            "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
            ("Administrator", DEFAULT_ADMIN_EMAIL, generate_password_hash(DEFAULT_ADMIN_PASSWORD), "QPPV / Admin", datetime.utcnow().isoformat())
        )
    cur.execute("SELECT COUNT(*) AS count FROM rmp_register")
    if cur.fetchone()["count"] == 0:
        rows = [
            ("Fever / pyrexia", "Important identified risk", "Routine AEFI monitoring and trend review", "HCP awareness, supportive management and follow-up", "Increase in frequency, seriousness or clustering"),
            ("Vomiting / diarrhea", "Important identified risk", "Routine non-serious AEFI review", "Supportive care guidance and monitoring", "Repeated reports from same site/batch"),
            ("Flu-like symptoms / coryza", "Important identified risk", "Routine AEFI review", "Symptomatic management and follow-up if persistent", "Increase in severity or unexpected pattern"),
            ("Serious allergic reaction", "Important potential risk", "Expedited serious case review", "Emergency referral and HCP training", "Anaphylaxis or life-threatening hypersensitivity"),
            ("VAPP surveillance window", "Important potential risk", "Monitor neurological symptoms within 4-40 days following OPV", "Referral and immediate medical review", "Any AFP/paralysis or neurological signal"),
            ("Batch cluster", "Potential signal", "Batch-wise trend and PV-QA review", "Batch traceability and investigation", "Cluster by batch, area or facility"),
            ("Storage excursion / quality complaint", "Important potential risk", "PV-QA complaint linkage", "Cold-chain and temperature record review", "Quality defect associated with AE/AEFI")
        ]
        cur.executemany("INSERT INTO rmp_register (safety_concern,category,monitoring_activity,risk_minimization,escalation_trigger) VALUES (?,?,?,?,?)", rows)
    conn.commit()
    conn.close()

def log_action(action, entity, entity_id="", details=""):
    conn = db()
    conn.execute(
        "INSERT INTO audit_log (username,action,entity,entity_id,details,created_at) VALUES (?,?,?,?,?,?)",
        (session.get("email", "system"), action, entity, entity_id, details, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.before_request
def setup():
    init_db()

@app.route("/")
def public_home():
    return render_template("public_home.html", app_name=APP_NAME, summary=AEFI_SUMMARY, symptoms=SYMPTOM_FREQUENCY)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]
            log_action("LOGIN", "user", str(user["id"]))
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", default_email=DEFAULT_ADMIN_EMAIL, default_password=DEFAULT_ADMIN_PASSWORD)

@app.route("/logout")
def logout():
    log_action("LOGOUT", "user", str(session.get("user_id", "")))
    session.clear()
    return redirect(url_for("public_home"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    total = conn.execute("SELECT COUNT(*) AS c FROM cases").fetchone()["c"]
    serious = conn.execute("SELECT COUNT(*) AS c FROM cases WHERE seriousness='Serious'").fetchone()["c"]
    non_serious = conn.execute("SELECT COUNT(*) AS c FROM cases WHERE seriousness='Non-serious'").fetchone()["c"]
    followup = conn.execute("SELECT COUNT(*) AS c FROM cases WHERE followup_required='Yes' OR case_status='Follow-up Required'").fetchone()["c"]
    recent = conn.execute("SELECT * FROM cases ORDER BY id DESC LIMIT 8").fetchall()
    by_event = conn.execute("SELECT event_term, COUNT(*) AS count FROM cases GROUP BY event_term ORDER BY count DESC").fetchall()
    conn.close()
    return render_template("dashboard.html", total=total, serious=serious, non_serious=non_serious, followup=followup, recent=recent, by_event=by_event, summary=AEFI_SUMMARY)

@app.route("/aefi-analysis")
@login_required
def aefi_analysis():
    return render_template("aefi_analysis.html", summary=AEFI_SUMMARY, gender=GENDER_DISTRIBUTION, age_stats=AGE_STATS, age_categories=AGE_CATEGORIES, symptoms=SYMPTOM_FREQUENCY, crosstab=GENDER_CROSSTAB, stations=STATIONS, cases=ANON_CASE_EXTRACT)

@app.route("/documents")
@login_required
def documents():
    return render_template("documents.html")

@app.route("/documents/<path:filename>")
@login_required
def document_file(filename):
    log_action("DOWNLOAD", "document", filename, "Source document download")
    return send_from_directory("static/documents", filename, as_attachment=True)

@app.route("/cases")
@login_required
def cases():
    q = request.args.get("q", "").strip()
    conn = db()
    if q:
        like = f"%{q}%"
        rows = conn.execute("""
            SELECT * FROM cases WHERE
            case_no LIKE ? OR patient_initials LIKE ? OR event_term LIKE ? OR batch_no LIKE ? OR seriousness LIKE ? OR suspected_product LIKE ? OR station_name LIKE ?
            ORDER BY id DESC
        """, (like, like, like, like, like, like, like)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("cases.html", cases=rows, q=q)

@app.route("/cases/new", methods=["GET", "POST"])
@login_required
def new_case():
    if request.method == "POST":
        now = datetime.utcnow().isoformat()
        case_no = "BOPV-PV-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        fields = {
            "case_no": case_no,
            "date_received": request.form.get("date_received"),
            "report_type": request.form.get("report_type"),
            "source_country": request.form.get("source_country"),
            "case_status": request.form.get("case_status"),
            "patient_initials": request.form.get("patient_initials"),
            "age": request.form.get("age"),
            "gender": request.form.get("gender"),
            "special_population": request.form.get("special_population"),
            "suspected_product": request.form.get("suspected_product"),
            "batch_no": request.form.get("batch_no"),
            "dose": request.form.get("dose"),
            "route": request.form.get("route"),
            "indication": request.form.get("indication"),
            "administration_date": request.form.get("administration_date"),
            "event_term": request.form.get("event_term"),
            "onset_date": request.form.get("onset_date"),
            "seriousness": request.form.get("seriousness"),
            "seriousness_criteria": request.form.get("seriousness_criteria"),
            "outcome": request.form.get("outcome"),
            "expectedness": request.form.get("expectedness"),
            "causality": request.form.get("causality"),
            "followup_required": request.form.get("followup_required"),
            "reporter_name": request.form.get("reporter_name"),
            "reporter_qualification": request.form.get("reporter_qualification"),
            "reporter_contact": request.form.get("reporter_contact"),
            "facility_city": request.form.get("facility_city"),
            "station_name": request.form.get("station_name"),
            "narrative": request.form.get("narrative"),
            "created_by": session.get("email"),
            "created_at": now,
            "updated_at": now
        }
        conn = db()
        columns = ",".join(fields.keys())
        placeholders = ",".join(["?"] * len(fields))
        cur = conn.execute(f"INSERT INTO cases ({columns}) VALUES ({placeholders})", tuple(fields.values()))
        conn.commit()
        conn.close()
        log_action("CREATE", "case", str(cur.lastrowid), case_no)
        flash(f"Case saved successfully: {case_no}", "success")
        return redirect(url_for("cases"))
    today = datetime.utcnow().date().isoformat()
    return render_template("case_form.html", today=today, stations=STATIONS)

@app.route("/cases/<int:case_id>")
@login_required
def case_detail(case_id):
    conn = db()
    c = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    conn.close()
    if not c:
        flash("Case not found.", "error")
        return redirect(url_for("cases"))
    return render_template("case_detail.html", c=c)

@app.route("/rmp")
@login_required
def rmp():
    conn = db()
    rows = conn.execute("SELECT * FROM rmp_register ORDER BY id").fetchall()
    conn.close()
    return render_template("rmp.html", rows=rows)

@app.route("/reports")
@login_required
def reports():
    conn = db()
    audit = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 30").fetchall()
    conn.close()
    return render_template("reports.html", audit=audit)

@app.route("/export/cases.csv")
@login_required
def export_cases_csv():
    conn = db()
    rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    conn.close()
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    else:
        output.write("No cases available\n")
    log_action("EXPORT", "cases", "", "CSV export")
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=pv_case_listing.csv"})

@app.route("/api/cases")
@login_required
def api_cases():
    conn = db()
    rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)