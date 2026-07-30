-- ============================================================================
-- Aegis AI — Database Initialization Script
-- Runs once on first PostgreSQL container startup.
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create test database for CI
SELECT 'CREATE DATABASE aegis_ai_test OWNER aegis'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aegis_ai_test')\gexec

-- Enable vector extension on test database
\c aegis_ai_test
CREATE EXTENSION IF NOT EXISTS "vector";
\c aegis_ai
