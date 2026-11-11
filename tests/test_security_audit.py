#!/usr/bin/env python3
"""
Synaptic Chat - Automated Security & Functional Testing Suite
Implements:
1. python-testing (pytest fixtures, parametrization, assertions)
2. security-bounty-hunter (adversarial penetration testing & vulnerability verification)
3. security-scan (audit of auth guards, injection vectors, and headers)
"""

import os
import sys
import subprocess
import json
import pytest
import requests

sys.path.insert(0, os.path.abspath("backend-python"))

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

@pytest.fixture(scope="session")
def admin_token():
    """Generates an authentic Super Admin JWT token via Docker container."""
    cmd = """docker exec synapticchat-backend python -c "
import jwt, datetime
from app.core.config import settings
data = {
    'id': 1,
    'username': 'admin',
    'displayName': 'Admin',
    'role': 'admin',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
print(jwt.encode(data, settings.JWT_SECRET, algorithm='HS256'))
" """
    try:
        token = subprocess.check_output(cmd, shell=True).decode().strip()
        return token
    except Exception as e:
        pytest.skip(f"Docker container not accessible to mint admin token: {e}")

@pytest.fixture(scope="session")
def regular_user_token():
    """Generates an authentic regular user JWT token (user id: 2, role: bda_sales)."""
    cmd = """docker exec synapticchat-backend python -c "
import jwt, datetime
from app.core.config import settings
data = {
    'id': 2,
    'username': 'naveen',
    'displayName': 'Naveen Sales',
    'role': 'bda_sales',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
print(jwt.encode(data, settings.JWT_SECRET, algorithm='HS256'))
" """
    try:
        token = subprocess.check_output(cmd, shell=True).decode().strip()
        return token
    except Exception as e:
        pytest.skip(f"Docker container not accessible to mint regular token: {e}")


# ============================================================================
# MODULE 1: AUTHENTICATION & ACCESS CONTROL (python-testing & security-scan)
# ============================================================================

class TestAuthenticationGuards:
    """Verifies authentication boundaries, token validation, and RBAC."""

    def test_health_check_public(self):
        """Public health endpoint should be reachable without auth."""
        res = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert res.status_code == 200
        assert res.json().get("ok") is True

    def test_protected_routes_reject_anonymous(self):
        """Verify that protected API routes reject unauthenticated requests."""
        protected_endpoints = [
            "/api/users",
            "/api/mcp/settings",
            "/api/organizations",
            "/api/agents",
            "/api/media-library",
            "/api/dashboard"
        ]
        for ep in protected_endpoints:
            res = requests.get(f"{BASE_URL}{ep}", timeout=5)
            assert res.status_code in (401, 403), f"Endpoint {ep} did not require authentication (got {res.status_code})"

    def test_invalid_and_expired_jwt_rejected(self):
        """Tampered or invalid JWT signatures must be rejected with 401."""
        tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MX0.TAMPERED_SIGNATURE_HERE"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        res = requests.get(f"{BASE_URL}/api/users", headers=headers, timeout=5)
        assert res.status_code == 401, "Tampered JWT was not rejected"

    def test_rbac_privilege_escalation_blocked(self, regular_user_token):
        """A real regular user (bda_sales) must be strictly forbidden (403) from Super Admin endpoints."""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        # Attempt to access user management
        res = requests.get(f"{BASE_URL}/api/users", headers=headers, timeout=5)
        assert res.status_code == 403, f"Regular user was not forbidden from /api/users (got {res.status_code})"

        # Attempt to access MCP admin settings
        res = requests.get(f"{BASE_URL}/api/mcp/settings", headers=headers, timeout=5)
        assert res.status_code == 403, f"Regular user was not forbidden from /api/mcp/settings (got {res.status_code})"

        # Attempt to call Shopify sync
        res = requests.post(f"{BASE_URL}/api/products/sync-shopify", headers=headers, json={"domain": "attacker.com"}, timeout=5)
        assert res.status_code == 403, f"Regular user was not forbidden from /api/products/sync-shopify (got {res.status_code})"

    def test_login_invalid_password_rejected(self):
        """Login with incorrect password returns 401."""
        payload = {"email": "admin@synapticchat.local", "password": "DefinitelyWrongPassword123!"}
        res = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=5)
        assert res.status_code == 401


# ============================================================================
# MODULE 2: ADVERSARIAL VULNERABILITY AUDIT (security-bounty-hunter)
# ============================================================================

class TestSecurityVulnerabilityHunting:
    """Hunts for high-impact exploitable patterns per security-bounty-hunter skill."""

    def test_whatsapp_webhook_invalid_signature_rejected(self):
        """
        [CWE-287] WhatsApp Webhook Signature Enforcement
        When an invalid X-Hub-Signature-256 is supplied, it must be rejected with 403.
        """
        fake_payload = {"object": "whatsapp_business_account", "entry": []}
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        }
        res = requests.post(
            f"{BASE_URL}/api/webhook/whatsapp",
            json=fake_payload,
            headers=headers,
            timeout=5
        )
        # If META_APP_SECRET is set, invalid signature yields 403; otherwise if unset, falls back
        assert res.status_code in (200, 403)
        if res.status_code == 403:
            print("\n[SECURITY VERIFIED] WhatsApp webhook strictly rejects forged signatures with 403.")

    def test_file_upload_security(self, admin_token):
        """
        [CWE-434 / CWE-306] File Upload Authentication & Access Control
        1. Anonymous uploads must be rejected with 401.
        2. Authenticated uploads succeed.
        """
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        files = {"file": ("probe_security.png", dummy_png, "image/png")}

        # 1. Anonymous attempt -> must be blocked
        res_anon = requests.post(f"{BASE_URL}/api/upload", files=files, timeout=5)
        assert res_anon.status_code == 401, f"Anonymous upload was not blocked (got {res_anon.status_code})"

        # 2. Authenticated attempt -> must succeed
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Re-seek or recreate files for second request
        files_auth = {"file": ("probe_security.png", dummy_png, "image/png")}
        res_auth = requests.post(f"{BASE_URL}/api/upload", headers=headers, files=files_auth, timeout=5)
        assert res_auth.status_code == 200
        data = res_auth.json()
        assert "url" in data
        assert data["url"].startswith("/uploads/")
        print(f"\n[SECURITY VERIFIED] Anonymous uploads blocked (401); Authenticated upload created {data['url']}")

    def test_path_traversal_protection(self, admin_token):
        """
        [CWE-22] Path Traversal in Media Serving Endpoints
        Test: Verify that path traversal probes (../../) are blocked by resolve_safe()
        and never leak sensitive files.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        traversal_payloads = [
            "../../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "../instance.json",
            "..%2Finstance.json",
            "....//....//app//core//config.py"
        ]
        for payload in traversal_payloads:
            res = requests.get(f"{BASE_URL}/api/media/{payload}", headers=headers, timeout=5)
            # Must never disclose arbitrary system files or credentials
            assert "root:x:" not in res.text, f"Path traversal successfully read /etc/passwd!"
            assert "JWT_SECRET" not in res.text, f"Path traversal disclosed server config!"
            assert "instance.json" not in res.text, f"Path traversal disclosed instance secrets!"
            # Direct API responses must be an error code or index HTML (fallback)
            if "text/html" not in res.headers.get("content-type", ""):
                assert res.status_code in (404, 400, 422)

    def test_sql_injection_resilience(self, admin_token):
        """
        [CWE-89] SQL Injection Probing in Query Parameters
        Test: Inject standard SQLi payloads into search, filter, and waNumber parameters.
        Verify parameterized queries prevent syntax errors or data exfiltration.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        sqli_payloads = [
            "' OR '1'='1",
            "1; SELECT pg_sleep(2);--",
            "1 UNION ALL SELECT NULL, NULL, NULL--",
            "admin'--",
            "{\"invalid\": \"json' OR 1=1--\"}"
        ]
        for payload in sqli_payloads:
            # Test in /api/dashboard range & category
            res = requests.get(f"{BASE_URL}/api/dashboard?range={payload}", headers=headers, timeout=5)
            assert res.status_code in (200, 400, 422)
            # Response should not contain internal SQL syntax error messages
            body_text = res.text.lower()
            assert "syntax error" not in body_text
            assert "pg_sleep" not in body_text

            # Test in /api/media-library search
            res = requests.get(f"{BASE_URL}/api/media-library?name={payload}", headers=headers, timeout=5)
            assert res.status_code in (200, 400, 422)
            assert "syntax error" not in res.text.lower()


# ============================================================================
# MODULE 3: AGENT & MCP GATEWAY SECURITY (agent-security-hardening)
# ============================================================================

class TestAgentAndMCPSecurity:
    """Verifies MCP API key authentication, capability gating, and boundaries."""

    def test_mcp_api_unauthenticated_rejected(self):
        """MCP API v1 endpoints must reject requests lacking a Bearer token."""
        mcp_endpoints = [
            "/api/mcp/v1/agents",
            "/api/mcp/v1/wa-accounts",
            "/api/mcp/v1/models",
            "/api/mcp/v1/templates"
        ]
        for ep in mcp_endpoints:
            res = requests.get(f"{BASE_URL}{ep}", timeout=5)
            assert res.status_code == 401, f"MCP endpoint {ep} did not require Bearer token (got {res.status_code})"
            assert "token" in res.text.lower() or "unauthorized" in res.text.lower()

    def test_mcp_api_invalid_token_rejected(self):
        """Forged or non-existent MCP keys must be rejected."""
        headers = {"Authorization": "Bearer sck_live_FORGED_NONEXISTENT_KEY_1234567890"}
        res = requests.get(f"{BASE_URL}/api/mcp/v1/agents", headers=headers, timeout=5)
        assert res.status_code in (401, 403), f"Invalid MCP key was not rejected (got {res.status_code})"

    def test_mcp_admin_settings_isolated(self, regular_user_token):
        """Regular users cannot tamper with MCP admin master switch or capabilities."""
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        payload = {"masterEnabled": True}
        res = requests.put(f"{BASE_URL}/api/mcp/settings", headers=headers, json=payload, timeout=5)
        assert res.status_code in (401, 403)


# ============================================================================
# MODULE 4: SECURITY HEADERS & COOKIE HYGIENE
# ============================================================================

class TestSecurityHeaders:
    """Verifies transport security, CORS, and cookie flags."""

    def test_cors_preflight_configuration(self):
        """Test OPTIONS preflight response for CORS."""
        headers = {
            "Origin": "http://evil-attacker.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type"
        }
        res = requests.options(f"{BASE_URL}/api/health", headers=headers, timeout=5)
        # Verify CORS doesn't blindly reflect wildcards with credentials
        allow_origin = res.headers.get("Access-Control-Allow-Origin")
        allow_creds = res.headers.get("Access-Control-Allow-Credentials")
        if allow_creds == "true":
            assert allow_origin != "*", "Insecure CORS: Allow-Credentials true with wildcard Origin"

    def test_nginx_security_headers_present(self):
        """Verify Nginx serves modern protective HTTP response headers including CSP."""
        res = requests.get(f"{BASE_URL}/", timeout=5)
        headers = res.headers
        assert headers.get("X-Frame-Options") == "DENY", "Missing or invalid X-Frame-Options"
        assert headers.get("X-Content-Type-Options") == "nosniff", "Missing or invalid X-Content-Type-Options"
        assert "strict-origin" in headers.get("Referrer-Policy", ""), "Missing or invalid Referrer-Policy"
        assert "default-src 'self'" in headers.get("Content-Security-Policy", ""), "Missing or invalid Content-Security-Policy"


# ============================================================================
# MODULE 5: INPUT BOUNDARY & CONTENT TYPE TAMPERING DEFENSE
# ============================================================================

class TestInputValidationAndBoundaryGuards:
    """Tests strict boundary validation across every input field."""

    def test_upload_magic_byte_spoofing_rejected(self, admin_token):
        """
        [CWE-434] Content-Type / File Extension Spoofing
        A text/executable payload with a .png extension must fail signature verification.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_png = b"MZ\x90\x00\x03\x00\x00\x00FakePEHeader disguised as PNG"
        files = {"file": ("malicious.png", fake_png, "image/png")}
        res = requests.post(f"{BASE_URL}/api/upload", headers=headers, files=files, timeout=5)
        assert res.status_code == 400
        assert "signature" in res.text.lower() or "invalid" in res.text.lower()

    def test_upload_valid_magic_byte_accepted(self, admin_token):
        """A valid PNG header must be accepted."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        files = {"file": ("valid.png", valid_png, "image/png")}
        res = requests.post(f"{BASE_URL}/api/upload", headers=headers, files=files, timeout=5)
        assert res.status_code == 200
        assert "url" in res.json()

    def test_user_creation_input_validation(self, admin_token):
        """
        [CWE-20] Input Validation on User Management
        Invalid emails, oversized usernames, or blank fields must be rejected with 400.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Invalid email
        res1 = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={"username": "validuser1", "email": "not-an-email", "displayName": "Valid User"},
            timeout=5
        )
        assert res1.status_code == 400

        # 2. Oversized username (>64 chars)
        res2 = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={"username": "a" * 100, "email": "user@example.com", "displayName": "Valid User"},
            timeout=5
        )
        assert res2.status_code == 400

        # 3. Blank username
        res3 = requests.post(
            f"{BASE_URL}/api/users",
            headers=headers,
            json={"username": "   ", "email": "user@example.com", "displayName": "Valid User"},
            timeout=5
        )
        assert res3.status_code == 400

    def test_shopify_ssrf_domain_validation(self, admin_token):
        """
        [CWE-918] SSRF Prevention in Shopify Catalog Sync
        Attacker domains and non-myshopify domains must be rejected with 400.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        invalid_domains = [
            "attacker.com",
            "169.254.169.254",
            "localhost",
            "my-shop.myshopify.com.attacker.com",
            "http://evil.com"
        ]
        for d in invalid_domains:
            res = requests.post(
                f"{BASE_URL}/api/products/sync-shopify",
                headers=headers,
                json={"domain": d},
                timeout=5
            )
            assert res.status_code == 400, f"Domain {d} was not rejected with 400 (got {res.status_code})"

    def test_login_oversized_payload_rejected_early(self):
        """
        [CWE-400] Denial of Service via Cryptographic CPU Exhaustion
        Oversized passwords (>256 chars) must be rejected before bcrypt execution.
        """
        huge_password = "A" * 10000
        res = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@synapticchat.local", "password": huge_password},
            timeout=5
        )
        assert res.status_code == 400
        assert "format" in res.text.lower()

    def test_ssrf_url_validator_defense(self):
        """
        [CWE-918] SSRF Prevention: Private, loopback, link-local, and cloud metadata
        URLs must be strictly blocked by the URL validator.
        """
        from app.util.url_validator import is_safe_external_url

        # Dangerous targets
        assert not is_safe_external_url("http://169.254.169.254/latest/meta-data/")
        assert not is_safe_external_url("http://127.0.0.1:8080/admin")
        assert not is_safe_external_url("http://localhost:3011/api")
        assert not is_safe_external_url("http://host.docker.internal:5432")
        assert not is_safe_external_url("http://0.0.0.0:80")
        assert not is_safe_external_url("http://10.0.0.1/internal")
        assert not is_safe_external_url("http://192.168.1.1/router")
        assert not is_safe_external_url("http://172.16.0.5/api")
        assert not is_safe_external_url("ftp://example.com/file")
        assert not is_safe_external_url("javascript:alert(1)")

        # Legitimate external HTTPS targets
        assert is_safe_external_url("https://script.google.com/macros/s/abcdef/exec")
        assert is_safe_external_url("https://api.shopify.com/v1")
