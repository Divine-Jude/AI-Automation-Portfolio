-- =============================================================================
-- DEV FULL RESET  -  legacy (multi-workflow) → v2 single-pipeline schema
-- =============================================================================
-- Run ONLY on a disposable / dev database. Review the safety block below.
--
-- v2 workflows (`workflows/01_Triage_Auto_Send_Calendar.json`) expect:
--   • emails (with triage_* columns + status CHECK)
--   • processing_events
--
-- They do NOT use: triage_results, meeting_extractions, draft_replies,
-- calendar_actions, job_runs, audit_logs  -  those were from the old 01-05 design.
-- =============================================================================

-- ============================================================
-- SAFETY CHECK: block dangerous runs by default
-- ============================================================
SET app.allow_destructive_reset = 'on';

DO $$
DECLARE
  db_name   text := current_database();
  db_user   text := current_user;
  app_name  text := coalesce(current_setting('application_name', true), '');
  allow_raw text := coalesce(current_setting('app.allow_destructive_reset', true), 'off');
  allow_destructive boolean := lower(allow_raw) IN ('1','true','on','yes');
BEGIN
  IF NOT allow_destructive THEN
    RAISE EXCEPTION
      'Refusing destructive reset. Enable only for this session: SET app.allow_destructive_reset = ''on'';';
  END IF;

  IF db_name ~* '(prod|production|live|main)' THEN
    RAISE EXCEPTION
      'Refusing destructive reset on production-like database: %', db_name;
  END IF;

  IF db_user IN ('postgres', 'neon_superuser', 'rds_superuser') THEN
    RAISE EXCEPTION
      'Refusing destructive reset with privileged role: %', db_user;
  END IF;

  IF app_name ~* '(prod|production|live)' THEN
    RAISE EXCEPTION
      'Refusing destructive reset from production-like application_name: %', app_name;
  END IF;

  RAISE NOTICE 'Safety check passed (db=%, role=%). Proceeding with reset.', db_name, db_user;
END $$;


-- ============================================================
-- DROP LEGACY + OPTIONAL RAG (order: children before parents)
-- ============================================================

DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS job_runs CASCADE;
DROP TABLE IF EXISTS calendar_actions CASCADE;
DROP TABLE IF EXISTS draft_replies CASCADE;
DROP TABLE IF EXISTS meeting_extractions CASCADE;
DROP TABLE IF EXISTS triage_results CASCADE;

-- If you added pgvector RAG tables, drop them too (uncomment if present):
-- DROP TABLE IF EXISTS owner_kb_chunks CASCADE;

DROP TABLE IF EXISTS processing_events CASCADE;
DROP TABLE IF EXISTS emails CASCADE;


-- ============================================================
-- V2 SCHEMA (matches sql/schema.sql)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE emails (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gmail_message_id  TEXT NOT NULL UNIQUE,
  thread_id         TEXT,
  from_email        TEXT,
  subject           TEXT,
  raw_text          TEXT,
  received_at       TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN (
      'pending', 'processed', 'ignored', 'sent', 'error'
    )),
  triage_category   TEXT,
  triage_confidence DOUBLE PRECISION,
  meeting_clarity   TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX emails_status_idx ON emails (status);
CREATE INDEX emails_created_idx ON emails (created_at DESC);

CREATE TABLE processing_events (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id   UUID REFERENCES emails (id) ON DELETE CASCADE,
  step       TEXT NOT NULL,
  payload    JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX processing_events_email_idx ON processing_events (email_id);


-- Optional: re-enable pgvector + RAG later (not required for v1 triage workflow)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- CREATE TABLE owner_kb_chunks (...);
