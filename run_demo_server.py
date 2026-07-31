"""
Aegis AI — Live Demo Server Launcher.

Initializes an SQLite database, seeds demo data, and launches the FastAPI server
with live interactive documentation at http://localhost:8000/docs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add services/api to python path
api_dir = Path(__file__).parent / "services" / "api"
sys.path.insert(0, str(api_dir))

# Configure environment for local SQLite demo
os.environ["DATABASE_HOST"] = "sqlite+aiosqlite:///./aegis_demo.db"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./aegis_demo.db"
os.environ["APP_ENV"] = "development"
os.environ["APP_DEBUG"] = "true"
os.environ["JWT_SECRET_KEY"] = "demo-secret-key-aegis-ai-2026"

import asyncio
from app.db.seed import seed_database
import uvicorn


async def main():
    print("=" * 70)
    print("[AEGIS AI] Enterprise AI Operations Platform Demo Server")
    print("=" * 70)
    print("\n1. Initializing local database and seeding demo data...")
    try:
        await seed_database()
    except Exception as e:
        print(f"   Database initialization note: {e}")

    print("\n2. Starting FastAPI server at http://127.0.0.1:8000")
    print("   - API Interactive Docs:  http://127.0.0.1:8000/docs")
    print("   - Health Check:          http://127.0.0.1:8000/health")
    print("   - Readiness Probe:       http://127.0.0.1:8000/readiness")
    print("   - Prometheus Metrics:    http://127.0.0.1:8000/metrics")
    print("\n" + "=" * 70 + "\n")

    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
