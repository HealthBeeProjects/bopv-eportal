import os
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path


DB_FILE = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
DB_FILE.close()

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_EMAIL"] = "admin@example.test"
os.environ["ADMIN_PASSWORD"] = "StrongAdminPass123!"
os.environ["PV_DB_PATH"] = DB_FILE.name
os.environ["PUBLIC_SIGNUP_ENABLED"] = "false"
os.environ["SESSION_COOKIE_SECURE"] = "false"

import app as portal


TOKEN_RE = re.compile(rb'name="_csrf_token" value="([^"]+)"')


class PortalSmokeTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        Path(DB_FILE.name).unlink(missing_ok=True)

    def setUp(self):
        self.client = portal.app.test_client()

    def csrf_from(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = TOKEN_RE.search(response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode("utf-8")

    def login(self, email="admin@example.test", password="StrongAdminPass123!"):
        token = self.csrf_from("/login")
        response = self.client.post(
            "/login",
            data={
                "_csrf_token": token,
                "email": email,
                "password": password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers["Location"])

    def create_officer(self):
        conn = sqlite3.connect(DB_FILE.name)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (id, name, email, password_hash, role, created_at)
                VALUES (
                    COALESCE((SELECT id FROM users WHERE email=?), 1000),
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    "officer@example.test",
                    "PV Officer",
                    "officer@example.test",
                    portal.generate_password_hash("OfficerPass123!"),
                    "PV Officer",
                    portal.utc_iso(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_public_pages_and_auth_redirect(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_login_requires_csrf(self):
        response = self.client.post(
            "/login",
            data={"email": "admin@example.test", "password": "StrongAdminPass123!"},
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_login_and_dashboard(self):
        self.login()
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_audit_trail_is_admin_only(self):
        self.login()
        admin_response = self.client.get("/reports")
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b"Audit Trail", admin_response.data)

        self.create_officer()
        officer_client = portal.app.test_client()
        self.client = officer_client
        self.login("officer@example.test", "OfficerPass123!")
        officer_response = self.client.get("/reports")
        self.assertEqual(officer_response.status_code, 200)
        self.assertNotIn(b"Audit Trail", officer_response.data)
        self.assertNotIn(b"admin@example.test", officer_response.data)

    def test_signup_is_disabled_by_default(self):
        response = self.client.get("/signup")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_signup_password_policy(self):
        self.assertTrue(portal.password_is_allowed("12345678"))
        self.assertTrue(portal.password_is_allowed("Health88"))
        self.assertFalse(portal.password_is_allowed("1234567"))
        self.assertFalse(portal.password_is_allowed("abcdefgh"))
        self.assertFalse(portal.password_is_allowed("Health@8"))

    def test_case_creation(self):
        self.login()
        token = self.csrf_from("/cases/new")
        response = self.client.post(
            "/cases/new",
            data={
                "_csrf_token": token,
                "date_received": "2026-06-15",
                "report_type": "Spontaneous",
                "source_country": "Pakistan",
                "case_status": "New",
                "patient_initials": "AB",
                "suspected_product": "bOPV / Oral Polio Vaccine",
                "event_term": "Fever",
                "seriousness": "Non-serious",
                "reporter_name": "PV Officer",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cases", response.headers["Location"])

        conn = sqlite3.connect(DB_FILE.name)
        try:
            count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
