from flask import Flask, abort, render_template, request, redirect, url_for, session, flash, Response, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta, timezone
import sqlite3
import csv
import io
import os
import secrets


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_local_env(path=None):
    if path is None:
        path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def utc_now():
    return datetime.now(timezone.utc)


def utc_iso():
    return utc_now().isoformat()


load_local_env()

APP_NAME = "bOPV E-Portal"
DB_PATH = os.environ.get("PV_DB_PATH") or os.path.join(BASE_DIR, "pv_eportal.db")
DOCUMENT_DIR = os.path.join(BASE_DIR, "static", "documents")
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required. Set it in the environment or a local .env file.")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
PUBLIC_SIGNUP_ENABLED = env_flag("PUBLIC_SIGNUP_ENABLED", True)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=env_flag("SESSION_COOKIE_SECURE", False),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get("SESSION_HOURS", "8"))),
)

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

ALLOWED_DOCUMENTS = {"AEFI_REPORT_UPDATED.docx"}

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
    user_count = cur.fetchone()["count"]
    if user_count == 0:
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            conn.close()
            raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD are required when initializing an empty database.")
        cur.execute(
            "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
            ("Administrator", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), "QPPV / Admin", utc_iso())
        )
    elif ADMIN_EMAIL and ADMIN_PASSWORD:
        existing_admin = cur.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        if existing_admin:
            cur.execute(
                "UPDATE users SET password_hash=?, role=? WHERE email=?",
                (generate_password_hash(ADMIN_PASSWORD), "QPPV / Admin", ADMIN_EMAIL)
            )
        else:
            cur.execute(
                "INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
                ("Administrator", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD), "QPPV / Admin", utc_iso())
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
        (session.get("email", "system"), action, entity, entity_id, details, utc_iso())
    )
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def is_admin_user():
    role = session.get("role", "").lower()
    return "admin" in role or "qppv" in role


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    sent_token = request.form.get("_csrf_token", "")
    stored_token = session.get("_csrf_token", "")
    if not sent_token or not stored_token or not secrets.compare_digest(sent_token, stored_token):
        abort(400)


def form_text(name):
    return request.form.get(name, "").strip()


def csv_safe(value):
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return "'" + value
    return value


PASSWORD_POLICY_MESSAGE = "Password must be exactly 8 digits, or at least 8 letters/numbers with both letters and numbers."


def password_is_allowed(password):
    if password.isdigit():
        return len(password) == 8
    return (
        len(password) >= 8
        and password.isalnum()
        and any(char.isalpha() for char in password)
        and any(char.isdigit() for char in password)
    )


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_csrf():
    if request.method == "POST":
        validate_csrf()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if session.get("user_id"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if not PUBLIC_SIGNUP_ENABLED:
        flash("Self-service registration is disabled. Ask an administrator for access.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = form_text("name")
        email = form_text("email").lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("signup"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        if not password_is_allowed(password):
            flash(PASSWORD_POLICY_MESSAGE, "error")
            return redirect(url_for("signup"))

        conn = db()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered.", "error")
            return redirect(url_for("login"))

        conn.execute(
            """
            INSERT INTO users
            (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                email,
                generate_password_hash(password),
                "PV Officer",
                utc_iso()
            )
        )

        conn.commit()
        conn.close()

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")
@app.route("/")
def public_home():
    return render_template("public_home.html", app_name=APP_NAME, summary=AEFI_SUMMARY, symptoms=SYMPTOM_FREQUENCY)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = form_text("email").lower()
        password = request.form.get("password", "")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]
            log_action("LOGIN", "user", str(user["id"]))
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", signup_enabled=PUBLIC_SIGNUP_ENABLED)

@app.route("/logout", methods=["POST"])
@login_required
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
    if filename not in ALLOWED_DOCUMENTS:
        abort(404)
    log_action("DOWNLOAD", "document", filename, "Source document download")
    return send_from_directory(DOCUMENT_DIR, filename, as_attachment=True)

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
        now_dt = utc_now()
        now = now_dt.isoformat()
        required_fields = [
            ("date_received", "Date received"),
            ("patient_initials", "Patient initials"),
            ("suspected_product", "Suspected product"),
            ("event_term", "Event / reaction term"),
            ("seriousness", "Seriousness"),
            ("reporter_name", "Reporter name / initials"),
        ]
        missing = [label for field, label in required_fields if not form_text(field)]
        if missing:
            flash("Missing required fields: " + ", ".join(missing), "error")
            return redirect(url_for("new_case"))

        case_no = "BOPV-PV-" + now_dt.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3).upper()
        fields = {
            "case_no": case_no,
            "date_received": form_text("date_received"),
            "report_type": form_text("report_type"),
            "source_country": form_text("source_country"),
            "case_status": form_text("case_status"),
            "patient_initials": form_text("patient_initials"),
            "age": form_text("age"),
            "gender": form_text("gender"),
            "special_population": form_text("special_population"),
            "suspected_product": form_text("suspected_product"),
            "batch_no": form_text("batch_no"),
            "dose": form_text("dose"),
            "route": form_text("route"),
            "indication": form_text("indication"),
            "administration_date": form_text("administration_date"),
            "event_term": form_text("event_term"),
            "onset_date": form_text("onset_date"),
            "seriousness": form_text("seriousness"),
            "seriousness_criteria": form_text("seriousness_criteria"),
            "outcome": form_text("outcome"),
            "expectedness": form_text("expectedness"),
            "causality": form_text("causality"),
            "followup_required": form_text("followup_required"),
            "reporter_name": form_text("reporter_name"),
            "reporter_qualification": form_text("reporter_qualification"),
            "reporter_contact": form_text("reporter_contact"),
            "facility_city": form_text("facility_city"),
            "station_name": form_text("station_name"),
            "narrative": form_text("narrative"),
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
    today = utc_now().date().isoformat()
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
    can_view_audit = is_admin_user()
    audit = []
    if can_view_audit:
        conn = db()
        audit = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 30").fetchall()
        conn.close()
    return render_template("reports.html", audit=audit, can_view_audit=can_view_audit)

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
            writer.writerow({key: csv_safe(value) for key, value in dict(row).items()})
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

init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=env_flag("FLASK_DEBUG", False))
