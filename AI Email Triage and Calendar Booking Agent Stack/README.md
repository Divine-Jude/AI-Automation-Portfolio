# AI Email Triage and Calendar Booking Agent

One n8n workflow that triages Gmail and handles meeting replies using real calendar availability.

The design goal is simple: reduce first-pass inbox work without inventing meeting times.

<img width="1440" height="900" alt="Screenshot 2026-04-20 at 4 59 07 PM" src="https://github.com/user-attachments/assets/dc43c1e3-dcc5-4b36-ae0c-f701859f1764" />


## What this project does

- Classifies each inbound email as `noise`, `operational`, or `meeting`
- Uses confidence thresholds so low-confidence runs do not auto-send
- Splits meeting requests into clear requests versus ambiguous requests
- Blocks calendar checks for ambiguous meeting asks
- Uses Google Calendar busy time plus Postgres booking caps for slot generation
- Sends plain-text Gmail replies
- Uses booking-link fallback when requested time is not viable
- Keeps an audit trail in Postgres
- Supports optional Slack notification after workflow-created events

## Architecture

### Stack

- **Orchestration:** n8n
- **Mail and calendar:** Gmail API + Google Calendar API
- **Database:** PostgreSQL
- **LLM:** Groq via LangChain nodes

This repo intentionally keeps one main workflow, not a multi-workflow stack.

### Diagram

```text
┌────────────────┐
│ Gmail Inbound  │
└───────┬────────┘
        │
        v
┌─────────────────────────────┐
│ n8n Workflow Engine         │
│ - ingest                    │
│ - dedupe                    │
│ - routing                   │
└───────┬─────────────────────┘
        │
        v
┌─────────────────────────────┐
│ Groq via LangChain          │
│ triage + drafts             │
└───────┬─────────────────────┘
        │
        v
┌─────────────────────────────┐
│ Meeting clear?              │
└───┬─────────────────────┬───┘
    │ No                  │ Yes
    v                     v
┌───────────────────┐   ┌─────────────────────────────┐
│ Clarify reply     │   │ Slot Logic                  │
│ no calendar path  │   │ + Google Calendar busy      │
└───────────────────┘   │ + Postgres booking caps     │
                        └───────────┬─────────────────┘
                                    │
                                    v
                        ┌─────────────────────────────┐
                        │ Plain-text Gmail reply      │
                        └───────────┬─────────────────┘
                                    │ optional exact match
                                    v
                        ┌─────────────────────────────┐
                        │ Create one calendar event   │
                        └───────────┬─────────────────┘
                                    │ optional
                                    v
                        ┌─────────────────────────────┐
                        │ Slack notification          │
                        └─────────────────────────────┘

Audit trail across paths: PostgreSQL `emails` + `processing_events`
```

## Before you start

You need:

- A running n8n instance
- Gmail and Google Calendar OAuth credentials in n8n
- A PostgreSQL database
- A Groq API key and Groq credential in n8n
- Optional Slack credential if you want booking notifications

## Quick start

1. Create database objects with `sql/schema.sql`.
2. Import `AI Email Triage and Calendar Booking Agent.json` into n8n.
3. Replace every `CONFIGURE_*` placeholder with real credentials.
4. Start with a Gmail label on the trigger to limit blast radius.
5. Run test messages for each path: noise, operational, meeting clear, meeting ambiguous.

If you are coming from an older schema, use `sql/dev_full_reset.sql` in a dev database and rebuild cleanly.

## Key tuning points

Tuning lives in Code nodes for n8n Cloud compatibility.

- **Parse Triage:** confidence thresholds
- **Compute Free Slots:** timezone, work hours, booking caps, booking page URL, and exact-match auto-book toggle
- **Get Calendar Events:** set horizon to match slot search window
- **Slack node:** optional and should not block workflow completion

`build_workflow.py` centralizes generated workflow output and booking URL injection.

## Expected behavior

- **Noise:** ignored and logged, no outbound reply
- **Operational:** draft and optional send if threshold passes
- **Meeting ambiguous:** clarify reply only, no calendar path
- **Meeting clear:** calendar-aware slot logic and reply
- **Specific requested time unavailable:** booking-link-only reply
- **Exact requested time available + auto-book enabled:** create at most one event

## Verification checklist

- Duplicate Gmail messages do not process twice
- Low-confidence triage does not send
- Ambiguous meetings never call calendar nodes
- Clear meetings use busy time and booking caps
- Plain-text outbound format is preserved
- Processing events are written in Postgres

## Regenerate workflow JSON

```bash
python3 build_workflow.py
```

The output path is defined in `build_workflow.py`.

## Roadmap note

In this repo, `v2` means planned backlog scope in `PRD.md`, not a versioned product name.

## License

Add a license file before public distribution.
