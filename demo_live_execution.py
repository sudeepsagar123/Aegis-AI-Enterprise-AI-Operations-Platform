"""
Aegis AI — End-to-End Operational Flow Live Demo Script.

Executes a complete live API lifecycle against the running backend server:
1. Health Check Probe
2. Register Organization & Admin User
3. JWT Login & Token Generation
4. Fetch User Profile & RBAC Role
5. Create a Critical System Incident
6. Fetch Real-Time Dashboard Incident Statistics
7. List Active Incidents
8. Query Prometheus Telemetry Metrics
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "http://127.0.0.1:8000"


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def http_post(endpoint: str, data: dict, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"detail": body}


def http_get(endpoint: str, token: str | None = None) -> tuple[int, dict]:
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"detail": body}


def main():
    # ── 1. System Health ─────────────────────────────────────────────────────
    print_section("1. SYSTEM HEALTH CHECK PROBE")
    status, health = http_get("/health")
    print(f"HTTP Status: {status}")
    print(json.dumps(health, indent=2))

    # ── 2. Register User & Organization ─────────────────────────────────────
    print_section("2. REGISTER ORGANIZATION & ADMIN USER")
    reg_payload = {
        "email": "admin@acme.com",
        "password": "AdminPass123!",
        "full_name": "Sarah Chen",
        "org_name": "Acme Enterprise AI Operations"
    }
    status, reg_res = http_post("/api/v1/auth/register", reg_payload)
    print(f"HTTP Status: {status}")
    if status == 201:
        print(f"Registered User ID: {reg_res['user']['id']}")
        print(f"Organization ID:    {reg_res['organization']['id']}")
        tokens = reg_res["tokens"]
    else:
        print(f"Note: {reg_res.get('detail', 'User already exists')}. Logging in with seeded credentials...")
        status, login_res = http_post("/api/v1/auth/login", {
            "email": "admin@acme.com",
            "password": "Admin@123!"
        })
        if status != 200:
            status, login_res = http_post("/api/v1/auth/login", {
                "email": "admin@acme.com",
                "password": "AdminPass123!"
            })
        tokens = login_res

    access_token = tokens["access_token"]
    print(f"\nJWT Token Type:    {tokens['token_type']}")
    print(f"Expires In:        {tokens['expires_in']} seconds")
    print(f"Access Token:      {access_token[:40]}...[TRUNCATED]")

    # ── 3. Profile & RBAC Role ──────────────────────────────────────────────
    print_section("3. USER PROFILE & RBAC ROLE")
    status, profile = http_get("/api/v1/auth/me", token=access_token)
    print(f"HTTP Status:   {status}")
    print(f"User ID:       {profile['id']}")
    print(f"Full Name:     {profile['full_name']}")
    print(f"Email:         {profile['email']}")
    print(f"Role:          {profile['role']}")
    print(f"Profile Data:  {json.dumps(profile)}")

    # ── 4. Create Incident ───────────────────────────────────────────────────
    print_section("4. CREATE NEW CRITICAL INCIDENT")
    incident_payload = {
        "title": "High Memory Pressure on Kubernetes Node-04",
        "description": "Node-04 memory usage exceeded 94% threshold. Pod eviction imminent.",
        "severity": "critical",
        "source": "prometheus",
        "tags": ["kubernetes", "memory", "node-04"],
        "affected_services": ["k8s-cluster-prod", "node-04"]
    }
    status, incident = http_post("/api/v1/incidents", incident_payload, token=access_token)
    print(f"HTTP Status:   {status}")
    print(f"Incident ID:   {incident['id']}")
    print(f"Title:         {incident['title']}")
    print(f"Severity:      {incident['severity']}")
    print(f"Status:        {incident['status']}")
    print(f"Source:        {incident['source']}")
    print(f"Created At:    {incident['created_at']}")

    # ── 5. Dashboard Metrics ─────────────────────────────────────────────────
    print_section("5. DASHBOARD INCIDENT METRICS")
    status, stats = http_get("/api/v1/incidents/stats", token=access_token)
    print(f"HTTP Status: {status}")
    print(json.dumps(stats, indent=2))

    # ── 6. List Active Incidents ──────────────────────────────────────────────
    print_section("6. LIST ACTIVE INCIDENTS")
    status, incidents_resp = http_get("/api/v1/incidents?limit=5", token=access_token)
    print(f"HTTP Status: {status}")
    incidents = incidents_resp.get("items", incidents_resp)
    print(f"Total Incidents Retrieved: {len(incidents)}")
    for inc in incidents:
        print(f"  - [{inc['severity'].upper():<8}] [{inc['status']:<13}] {inc['title']}")

    # ── 7. Observability Metrics ─────────────────────────────────────────────
    print_section("7. PROMETHEUS TELEMETRY METRICS SAMPLE")
    req = urllib.request.Request(f"{BASE_URL}/metrics")
    with urllib.request.urlopen(req) as resp:
        metrics_raw = resp.read().decode("utf-8")
        metrics_lines = [line for line in metrics_raw.splitlines() if line and not line.startswith("#")]
        for line in metrics_lines[:10]:
            print(f"  {line}")

    print("\n" + "=" * 70)
    print("  LIVE DEMONSTRATION EXECUTED SUCCESSFULLY!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
