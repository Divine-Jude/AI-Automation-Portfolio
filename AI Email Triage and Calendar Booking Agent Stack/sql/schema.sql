-- Minimal schema: AI Email Triage and Calendar Booking Agent (single-pipeline)
-- Run once on Postgres 14+ (gen_random_uuid requires pgcrypto or use uuid_generate_v4)
--
-- Existing database already on an older schema? Run sql/migrate.sql (idempotent).
--
-- If you are migrating from the old multi-workflow DB (draft_replies, calendar_actions,
-- triage_results, audit_logs, …), use `dev_full_reset.sql` on a **dev** database instead
-- of hand-merging. Fresh installs can run this file as-is.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS emails (
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

CREATE INDEX IF NOT EXISTS emails_status_idx ON emails (status);
CREATE INDEX IF NOT EXISTS emails_created_idx ON emails (created_at DESC);

CREATE TABLE IF NOT EXISTS processing_events (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email_id   UUID REFERENCES emails (id) ON DELETE CASCADE,
  step       TEXT NOT NULL,
  payload    JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS processing_events_email_idx ON processing_events (email_id);
