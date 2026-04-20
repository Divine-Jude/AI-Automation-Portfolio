#!/usr/bin/env python3
"""Generate the n8n workflow JSON next to this script (single-pipeline AI email agent)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "AI Email Triage and Calendar Booking Agent.json"

# Public booking page (same value as BOOKING_PAGE_URL inside Compute Free Slots / SLOT_CODE).
BOOKING_PAGE_URL = "https://calendar.app.google/nV7E9Yx59Z5nG9og6"


def uid() -> str:
    return str(uuid.uuid4())


# --- Slot finder: calendar busy + DB booking caps + weekday preferences (edit constants below) ---
# n8n Cloud: no $env. Tune MAX_* , WORK_TZ, SEARCH_DAYS, bookingUrl here (and Get Calendar timeMax).
SLOT_CODE = r"""const WORK_TZ = 'Africa/Lagos';
const SEARCH_DAYS = 21;
const SLOT_MIN = 30;
const WORK_START = 9 * 60;
const WORK_END = 17 * 60;
const MAX_BOOKINGS_PER_DAY = 3;
const MAX_BOOKINGS_PER_WEEK = 3;
const WINDOW_DAYS_FIRST = 7;
const WINDOW_DAYS_TOTAL = 14;
const BOOKING_PAGE_URL = '__BOOKING_PAGE_URL__';
/** When true: if the sender named a specific day+time and that slot is free, create one calendar event for that slot after send. No auto-book for vague meeting asks or substitute times. */
const AUTO_BOOK_ON_EXACT_MATCH = true;

const email = $('Store Email Record ID').first().json;
const prep = $('Prepare Email Fields').first().json;
const combinedText = (String(prep.subject || '') + ' ' + String(prep.raw_text || '')).trim();

let bookedRaw = $('Postgres: Booked Slot Times').first().json.booked_starts;
if (bookedRaw == null) bookedRaw = [];
if (typeof bookedRaw === 'string') {
  try { bookedRaw = JSON.parse(bookedRaw); } catch (e) { bookedRaw = []; }
}
const bookedMs = (Array.isArray(bookedRaw) ? bookedRaw : [])
  .map((s) => new Date(s).getTime())
  .filter((x) => Number.isFinite(x));

function dayKey(ms) {
  return new Date(ms).toLocaleDateString('en-CA', { timeZone: WORK_TZ });
}
function weekKeyUtc(ms) {
  const date = new Date(ms);
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const year = d.getUTCFullYear();
  const week1 = new Date(Date.UTC(year, 0, 4));
  const weekNo = Math.ceil((((d - week1) / 86400000) + 1) / 7);
  return year + '-W' + String(weekNo).padStart(2, '0');
}
function countBookedDay(ms) {
  const k = dayKey(ms);
  return bookedMs.filter((t) => dayKey(t) === k).length;
}
function countBookedWeek(ms) {
  const k = weekKeyUtc(ms);
  return bookedMs.filter((t) => weekKeyUtc(t) === k).length;
}
function canBookSlot(ms) {
  return countBookedDay(ms) < MAX_BOOKINGS_PER_DAY && countBookedWeek(ms) < MAX_BOOKINGS_PER_WEEK;
}

function parsePreferredWeekdays(text) {
  const t = String(text || '').toLowerCase();
  const pairs = [
    ['sunday', 0], ['monday', 1], ['tuesday', 2], ['wednesday', 3],
    ['thursday', 4], ['friday', 5], ['saturday', 6],
    ['sun', 0], ['mon', 1], ['tue', 2], ['tues', 2], ['wed', 3], ['thu', 4], ['thur', 4], ['thurs', 4], ['fri', 5], ['sat', 6]
  ];
  const found = new Set();
  for (const [word, d] of pairs) {
    const re = new RegExp('\\b' + word + '\\b', 'i');
    if (re.test(t)) found.add(d);
  }
  return found;
}

function parseTimeWindowMins(text) {
  const t = String(text || '').toLowerCase();
  const wantsAfternoon = /\bafternoon\b|after\s*noon|after\s+noon/i.test(t);
  const wantsMorning = /\bmorning\b|before\s*noon|before\s+noon/i.test(t);
  let minStartMins = WORK_START;
  let maxStartMins = WORK_END - SLOT_MIN;
  if (wantsAfternoon && !wantsMorning) {
    minStartMins = Math.max(WORK_START, 12 * 60);
  } else if (wantsMorning && !wantsAfternoon) {
    maxStartMins = Math.min(12 * 60 - SLOT_MIN, WORK_END - SLOT_MIN);
  }
  if (minStartMins > maxStartMins) {
    minStartMins = WORK_START;
    maxStartMins = WORK_END - SLOT_MIN;
  }
  return { minStartMins, maxStartMins };
}

function localWeekday(ms) {
  const wp = new Intl.DateTimeFormat('en-US', { timeZone: WORK_TZ, weekday: 'short' }).formatToParts(new Date(ms))
    .find((p) => p.type === 'weekday');
  const w = wp && wp.value ? wp.value : 'Mon';
  const map = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return map[w.slice(0, 3)] ?? 0;
}

function localParts(ms) {
  const fmt = new Intl.DateTimeFormat('en-GB', { timeZone: WORK_TZ, hour: '2-digit', minute: '2-digit', hour12: false, weekday: 'short' });
  const p = Object.fromEntries(fmt.formatToParts(new Date(ms)).filter((x) => x.type !== 'literal').map((x) => [x.type, x.value]));
  const h = parseInt(p.hour, 10);
  const m = parseInt(p.minute, 10);
  return { mins: h * 60 + m };
}
function isWeekend(ms) {
  const w = new Intl.DateTimeFormat('en-US', { timeZone: WORK_TZ, weekday: 'short' }).format(new Date(ms));
  return w === 'Sat' || w === 'Sun';
}

const items = $input.all();
const busy = [];
for (const it of items) {
  const j = it.json;
  if (!j.start || j.status === 'cancelled') continue;
  if (j.transparency === 'transparent') continue;
  if (j.start.dateTime && j.end?.dateTime) {
    const a = new Date(j.start.dateTime).getTime();
    const b = new Date(j.end.dateTime).getTime();
    if (Number.isFinite(a) && Number.isFinite(b) && b > a) busy.push([a, b]);
  }
}
busy.sort((x, y) => x[0] - y[0]);

function overlaps(t0, t1) {
  return busy.some(([a, b]) => t0 < b && t1 > a);
}

const dur = SLOT_MIN * 60000;
const preferSet = parsePreferredWeekdays(combinedText);
const strictPreferred = preferSet.size > 0;
let { minStartMins, maxStartMins } = parseTimeWindowMins(combinedText);

function scanRange(fromMs, toMs, weekdaySet, twMin, twMax) {
  const lo = twMin != null ? twMin : minStartMins;
  const hi = twMax != null ? twMax : maxStartMins;
  const found = [];
  let t = fromMs;
  while (t < toMs && found.length < 8) {
    if (isWeekend(t)) { t += 30 * 60000; continue; }
    const c = localParts(t);
    if (c.mins % 30 !== 0) { t += 60000; continue; }
    if (c.mins < lo || c.mins > hi || c.mins + SLOT_MIN > WORK_END) { t += 30 * 60000; continue; }
    if (weekdaySet && !weekdaySet.has(localWeekday(t))) { t += 30 * 60000; continue; }
    const te = t + dur;
    if (overlaps(t, te)) { t += 30 * 60000; continue; }
    if (!canBookSlot(t)) { t += 30 * 60000; continue; }
    found.push(t);
    t += 30 * 60000;
  }
  return found;
}

function toSlotObjs(timestamps) {
  return timestamps.slice(0, 6).map((t) => ({
    start: new Date(t).toISOString(),
    end: new Date(t + dur).toISOString(),
    display: new Date(t).toLocaleString('en-US', { weekday: 'long', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: WORK_TZ })
  }));
}

function slotViable(t) {
  if (isWeekend(t)) return false;
  const lp = localParts(t);
  if (lp.mins < WORK_START || lp.mins + SLOT_MIN > WORK_END) return false;
  if (overlaps(t, t + dur)) return false;
  if (!canBookSlot(t)) return false;
  return true;
}

function parseExplicitDayAndTime(text) {
  const lower = String(text || '').toLowerCase();
  const pairs = [
    ['sunday', 0], ['monday', 1], ['tuesday', 2], ['wednesday', 3],
    ['thursday', 4], ['friday', 5], ['saturday', 6],
    ['sun', 0], ['mon', 1], ['tue', 2], ['wed', 3], ['thu', 4], ['thur', 4], ['thurs', 4], ['fri', 5], ['sat', 6]
  ];
  let dow = -1;
  for (const [word, d] of pairs) {
    if (new RegExp('\\b' + word + '\\b', 'i').test(lower)) { dow = d; break; }
  }
  let wantMins = null;
  let mm = lower.match(/\b(\d{1,2}):(\d{2})\s*(am|pm)\b/);
  if (mm) {
    let h = parseInt(mm[1], 10);
    const mi = parseInt(mm[2], 10);
    const ap = mm[3];
    if (ap === 'pm' && h < 12) h += 12;
    if (ap === 'am' && h === 12) h = 0;
    wantMins = h * 60 + mi;
  } else {
    mm = lower.match(/\b(\d{1,2})\s*(am|pm)\b/);
    if (mm) {
      let h = parseInt(mm[1], 10);
      const ap = mm[2];
      if (ap === 'pm' && h < 12) h += 12;
      if (ap === 'am' && h === 12) h = 0;
      wantMins = h * 60;
    }
  }
  if (dow < 0 || wantMins == null) return { parseable: false };
  return { parseable: true, dow, wantMins };
}

function findStartMsForDayAndTime(dow, wantMins, fromMs, toMs) {
  const snapped = Math.round(wantMins / 30) * 30;
  if (snapped < WORK_START || snapped > WORK_END - SLOT_MIN) return null;
  let t = Math.ceil(fromMs / (30 * 60000)) * (30 * 60000);
  while (t < toMs) {
    if (isWeekend(t)) { t += 30 * 60000; continue; }
    if (localWeekday(t) !== dow) { t += 30 * 60000; continue; }
    if (localParts(t).mins !== snapped) { t += 30 * 60000; continue; }
    return t;
  }
  return null;
}

function formatRequestedSummary(dow, wantMins) {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  let h = Math.floor(wantMins / 60);
  const m = wantMins % 60;
  const ap = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const mm = m === 0 ? '' : ':' + String(m).padStart(2, '0');
  return days[dow] + ' at ' + h12 + mm + ' ' + ap;
}

const now = Date.now();
const startScan = now + 5 * 60000;
const endTotal = startScan + WINDOW_DAYS_TOTAL * 86400000;
const splitA = startScan + WINDOW_DAYS_FIRST * 86400000;

let availability_hint = '';
let tsMs = [];
let used_next_segment = false;

if (strictPreferred) {
  let ts = scanRange(startScan, splitA, preferSet, minStartMins, maxStartMins);
  if (ts.length === 0) {
    ts = scanRange(splitA, endTotal, preferSet, minStartMins, maxStartMins);
    if (ts.length > 0) used_next_segment = true;
  }
  if (ts.length === 0) {
    ts = scanRange(startScan, splitA, null, minStartMins, maxStartMins);
    if (ts.length === 0) {
      ts = scanRange(splitA, endTotal, null, minStartMins, maxStartMins);
      if (ts.length > 0) used_next_segment = true;
    }
    if (ts.length > 0) {
      availability_hint = 'Their preferred weekdays (and time of day) are fully booked or blocked in the search window. The times below are on other weekdays  -  say that clearly and ask them to confirm.';
    }
  }
  if (ts.length === 0) {
    availability_hint = 'There is no slot matching their weekday and time-of-day preferences in the next two weeks (or limits are full). Apologize briefly, invite them to use the booking link, and offer to follow up manually.';
  } else if (used_next_segment && !availability_hint) {
    availability_hint = 'Earlier days did not have a matching slot (preferences or booking limits). The times below are in a later week  -  say that clearly.';
  }
  tsMs = ts;
} else {
  let ts = scanRange(startScan, splitA, null, minStartMins, maxStartMins);
  if (ts.length === 0) {
    ts = scanRange(splitA, endTotal, null, minStartMins, maxStartMins);
    if (ts.length > 0) {
      used_next_segment = true;
      availability_hint = 'Nothing was available in the first week (busy calendar or 3/day or 3/week limits). The times below are in the following week  -  explain that politely.';
    }
  }
  if (ts.length === 0) {
    availability_hint = 'No 30-minute openings in the next two weeks within work hours, or automated booking limits are full. Say you are fully booked for now, offer the booking link, and suggest checking next week.';
  }
  tsMs = ts;
}

let slots = toSlotObjs(tsMs);
let has_slots = slots.length > 0;

let booking_link_only = false;
let auto_book_eligible = false;
let requested_summary = '';
const explicit = parseExplicitDayAndTime(combinedText);
if (explicit.parseable) {
  requested_summary = formatRequestedSummary(explicit.dow, explicit.wantMins);
  const reqMs = findStartMsForDayAndTime(explicit.dow, explicit.wantMins, startScan, endTotal);
  const ok = reqMs != null && slotViable(reqMs);
  if (!ok) {
    booking_link_only = true;
    slots = [];
    has_slots = false;
    auto_book_eligible = false;
    availability_hint = 'BOOKING_LINK_ONLY: They named a specific day and time that you cannot honor from this inbox (conflict, outside work hours, or booking limits). Do not list alternative times. One short paragraph + booking link only.';
  } else {
    const rest = tsMs.filter((x) => Math.abs(x - reqMs) >= 60000);
    const merged = [reqMs, ...rest].slice(0, 6);
    slots = toSlotObjs(merged);
    has_slots = slots.length > 0;
    auto_book_eligible = AUTO_BOOK_ON_EXACT_MATCH === true;
    booking_link_only = false;
    if (!availability_hint) {
      availability_hint = AUTO_BOOK_ON_EXACT_MATCH
        ? 'Their requested time is free; lead with that slot. You may list other options as bullets. A calendar hold may be created for the first slot after send when automation is on.'
        : 'Their requested time appears free. Put that time first; you may add a few other options as bullets. Ask them to reply to confirm, or use the booking link so the calendar invite is created automatically.';
    }
  }
}

function senderFirstFromFrom(s) {
  const from = String(s || '');
  const q = from.match(/^([^<]+)</);
  let n = '';
  if (q) n = q[1].trim().replace(/^["']+|["']+$/g, '').split(/\\s+/)[0];
  if (!n) n = from.split('@')[0].split(/[._+-]/)[0];
  return n || 'there';
}

const bookingUrl = BOOKING_PAGE_URL;
return [{
  json: {
    email_id: email.email_id,
    msg_id: prep.msg_id,
    thread_id: prep.thread_id,
    from_email: prep.from_email,
    subject: prep.subject,
    raw_text: prep.raw_text,
    slots,
    booking_url: bookingUrl,
    has_slots: has_slots,
    availability_hint,
    preferred_weekdays: strictPreferred ? Array.from(preferSet).sort().join(',') : '',
    booking_link_only,
    auto_book_eligible,
    requested_summary,
    sender_first_name: senderFirstFromFrom(prep.from_email)
  }
}];"""

SLOT_CODE = SLOT_CODE.replace("__BOOKING_PAGE_URL__", BOOKING_PAGE_URL)

# Decode &quot; etc. + optional HTML strip so DB stores human-readable text (job alerts, newsletters).
DECODE_EMAIL_CODE = r"""const j = $input.first().json;

function decodeHtmlEntities(input) {
  let s = String(input ?? '');
  s = s.replace(/&#(\d+);/g, (_, n) => String.fromCharCode(parseInt(n, 10)));
  s = s.replace(/&#x([\da-fA-F]+);/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
  const map = {
    '&quot;': '"',
    '&apos;': "'",
    '&#39;': "'",
    '&lt;': '<',
    '&gt;': '>',
    '&nbsp;': ' ',
    '&ndash;': '\u2013',
    '&mdash;': '\u2014',
    '&amp;': '&'
  };
  for (const [k, v] of Object.entries(map)) {
    s = s.split(k).join(v);
  }
  return s;
}

function stripHtml(html) {
  return String(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

const subject = decodeHtmlEntities(j.subject);
let raw = decodeHtmlEntities(j.raw_text || '');
if (/<[a-z][\s\S]*>/i.test(raw)) {
  raw = stripHtml(raw);
}

return [{ json: { ...j, subject, raw_text: raw } }];"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Node definitions (order = rough canvas left-to-right)
    nodes: list[dict] = []

    nodes.append(
        {
            "parameters": {
                "content": """## How this workflow runs

**1  -  Ingest**  
Gmail → **Prepare Email Fields** → **Decode Email Text** (readable body for DB) → **Postgres Insert** → **Is New Email?** (duplicate → **Skip Duplicate**).

**2  -  Triage**  
**LLM: Triage** + **Groq Chat: Triage** → **Parse Triage** (confidence + category) → **Save Triage To DB** → **Log Triage Event**.

**3  -  Route**  
**Low Triage Confidence?** → yes: mark processed, log skip, stop.  
**Is Noise?** → yes: ignored + log, stop.  
**Is Operational?** → yes: draft → **Operational Send OK?** → Gmail send or processed.  
→ no (meeting category): **Meeting: Scheduling Ready?** (`meeting` + `meeting_clarity: clear`)  
 • **No** (ambiguous / vague meeting): **LLM: Meeting Clarify** → clarify reply only  -  **no Google Calendar**, no slot engine.  
 • **Yes**: **Postgres: Booked Slot Times** → **Get Calendar Events** → **Compute Free Slots** → booking-link-only OR **LLM: Draft Meeting** → **Merge Meeting Draft** → **Meeting Send OK?** → **Gmail Send Meeting** (plain text) → **Has Valid Slots?** (`auto_book_eligible` when exact requested slot is free and `AUTO_BOOK_ON_EXACT_MATCH` is true) → optional create + Slack → DB + log.

**Edit numbers in Code:** **Parse Triage** (thresholds), **Compute Free Slots** (timezone, hours, caps; `BOOKING_PAGE_URL` via placeholder). No `$env` in expressions (n8n Cloud).

**Slack:** native **Slack** node  -  OAuth credential + channel (placeholder `#meetings`; change in UI).""",
                "height": 640,
                "width": 460,
                "color": 7,
            },
            "id": uid(),
            "name": "How this workflow runs",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [-600, 200],
        }
    )
    nodes.append(
        {
            "parameters": {
                "content": """### Rule: Noise
If triage returns `noise`, do not reply.
Mark email as ignored and log `noise_ignored` for audit.""",
                "height": 140,
                "width": 320,
                "color": 5,
            },
            "id": uid(),
            "name": "Rule Note: Noise",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [2300, -120],
        }
    )
    nodes.append(
        {
            "parameters": {
                "content": """### Rule: Operational
If triage returns `operational`, draft a normal professional reply.
Send only when confidence passes send threshold.
No calendar slot engine on this branch.""",
                "height": 170,
                "width": 340,
                "color": 4,
            },
            "id": uid(),
            "name": "Rule Note: Operational",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [2860, -120],
        }
    )
    nodes.append(
        {
            "parameters": {
                "content": """### Rule: Meeting Ambiguous
If `meeting_clarity` is `ambiguous`, send booking-link-first reply.
Do not propose slots.
Do not run Google Calendar checks.
Do not run slot computation.""",
                "height": 190,
                "width": 360,
                "color": 6,
            },
            "id": uid(),
            "name": "Rule Note: Meeting Ambiguous",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [2860, 540],
        }
    )
    nodes.append(
        {
            "parameters": {
                "content": """### Rule: Meeting Clear
If `meeting_clarity` is `clear`, run booked-times query + calendar busy check + slot logic.
If requested time is unavailable, send booking-link-only reply.
If exact requested time is free and auto-book is enabled, create event and send Slack notice.""",
                "height": 220,
                "width": 390,
                "color": 3,
            },
            "id": uid(),
            "name": "Rule Note: Meeting Clear",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [3360, 520],
        }
    )

    nodes.append(
        {
            "parameters": {
                "pollTimes": {"item": [{"mode": "everyX", "value": 5, "unit": "minutes"}]},
                "filters": {"readStatus": "unread"},
            },
            "id": uid(),
            "name": "Gmail Trigger",
            "type": "n8n-nodes-base.gmailTrigger",
            "typeVersion": 1.3,
            "position": [0, 300],
            "credentials": {"gmailOAuth2": {"id": "CONFIGURE_GMAIL", "name": "Gmail account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "a1", "name": "msg_id", "type": "string", "value": "={{ $json.id }}"},
                        {"id": "a2", "name": "thread_id", "type": "string", "value": "={{ $json.threadId }}"},
                        {
                            "id": "a3",
                            "name": "from_email",
                            "type": "string",
                            "value": "={{ ($json.from?.value?.[0]?.address) || (($json.From || '').match(/<([^>]+)>/)?.[1]) || ($json.From || '').trim() || 'unknown@example.com' }}",
                        },
                        {"id": "a4", "name": "subject", "type": "string", "value": "={{ $json.subject || $json.Subject || '' }}"},
                        {"id": "a5", "name": "received_at", "type": "string", "value": "={{ $json.date ? new Date($json.date).toISOString() : new Date().toISOString() }}"},
                        {"id": "a6", "name": "raw_text", "type": "string", "value": "={{ $json.textPlain || $json.textHtml || $json.snippet || '' }}"},
                    ]
                },
                "options": {},
            },
            "id": uid(),
            "name": "Prepare Email Fields",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [220, 300],
        }
    )

    nodes.append(
        {
            "parameters": {"jsCode": DECODE_EMAIL_CODE},
            "id": uid(),
            "name": "Decode Email Text",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [330, 300],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO emails (
  gmail_message_id, thread_id, from_email, subject, received_at, raw_text, status
) VALUES ($1, $2, $3, $4, $5, $6, 'pending')
ON CONFLICT (gmail_message_id) DO NOTHING
RETURNING id;""",
                "options": {
                    "queryReplacement": "={{ [\n  $json.msg_id,\n  $json.thread_id,\n  $json.from_email,\n  $json.subject,\n  $json.received_at,\n  $json.raw_text\n] }}"
                },
            },
            "id": uid(),
            "name": "Postgres Insert Email",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [440, 300],
            "alwaysOutputData": True,
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {
                            "id": "c1",
                            "leftValue": "={{ $json.id !== undefined && $json.id !== null }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Is New Email?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [660, 300],
        }
    )

    nodes.append(
        {
            "parameters": {},
            "id": uid(),
            "name": "Skip Duplicate",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [880, 480],
        }
    )

    nodes.append(
        {
            "parameters": {
                "assignments": {
                    "assignments": [{"id": "s1", "name": "email_id", "type": "string", "value": "={{ $json.id }}"}]
                },
                "options": {},
            },
            "id": uid(),
            "name": "Store Email Record ID",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [880, 180],
        }
    )

    nodes.append(
        {
            "parameters": {
                "model": "llama-3.1-8b-instant",
                "options": {"temperature": 0.2},
            },
            "id": uid(),
            "name": "Groq Chat: Triage",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "position": [1100, 340],
            "credentials": {"groqApi": {"id": "CONFIGURE_GROQ", "name": "Groq account"}},
        }
    )
    nodes.append(
        {
            "parameters": {
                "promptType": "define",
                "text": """=You classify inbound email for an assistant. Reply with ONLY valid JSON, no markdown, no code fences.

Categories (pick exactly one):
- noise = newsletters, receipts, automated updates, FYI, no reply needed
- operational = needs a written reply but not scheduling a live conversation
- meeting = they want to schedule a call, video meeting, or in-person sync

When category is "meeting", you MUST also set meeting_clarity:
- clear = they gave enough to act on scheduling: a specific day and/or time, OR a concrete window (e.g. "Tuesday 3pm", "next Wed morning", "week of April 20", "are you free Thursday afternoon CET?"). Short questions like "30 min Thursday?" count as clear.
- ambiguous = scheduling vibe only: "let's sync", "grab coffee", "we should connect", "can we find time?", forwarding threads with no proposed slot, or no timeframe at all.

If you are unsure, prefer ambiguous (safer: no calendar automation).

Return exactly this JSON shape:
{"category":"noise|operational|meeting","meeting_clarity":"n_a|clear|ambiguous","confidence":0.0,"reason":"short"}
Use meeting_clarity "n_a" when category is not meeting.

Subject: {{ $('Prepare Email Fields').first().json.subject }}
From: {{ $('Prepare Email Fields').first().json.from_email }}
Body:
{{ $('Prepare Email Fields').first().json.raw_text }}""",
                "batching": {},
            },
            "id": uid(),
            "name": "LLM: Triage",
            "type": "@n8n/n8n-nodes-langchain.chainLlm",
            "typeVersion": 1.9,
            "position": [1100, 180],
        }
    )

    nodes.append(
        {
            "parameters": {
                "jsCode": (
                    """const T_TRIAGE_MIN = 0.65;
const T_SEND_MIN = 0.7;
const raw = $input.first().json;
const content = raw.text || raw.output || raw.response || raw.choices?.[0]?.message?.content || raw.message?.content || '{}';
let triage = { category: 'noise', confidence: 0, reason: 'parse_error', meeting_clarity: 'n_a' };
try {
  const cleaned = String(content).replace(/```json\\s*/g, '').replace(/```/g, '').trim();
  triage = JSON.parse(cleaned);
} catch (e) {}
let cat = String(triage.category || 'noise').toLowerCase();
if (!['noise', 'operational', 'meeting'].includes(cat)) cat = 'noise';
let mc = String(triage.meeting_clarity || '').toLowerCase();
if (!['clear', 'ambiguous', 'n_a'].includes(mc)) mc = 'n_a';
if (cat !== 'meeting') {
  mc = 'n_a';
} else if (mc === 'n_a' || mc === '') {
  mc = 'ambiguous';
}
const conf = Math.min(1, Math.max(0, parseFloat(triage.confidence) || 0));
const prep = $('Prepare Email Fields').first().json;
const emailId = $('Store Email Record ID').first().json.email_id;
const meeting_scheduling_ready = cat === 'meeting' && mc === 'clear';
return [{
  json: {
    email_id: emailId,
    msg_id: prep.msg_id,
    thread_id: prep.thread_id,
    from_email: prep.from_email,
    subject: prep.subject,
    raw_text: prep.raw_text,
    category: cat,
    meeting_clarity: mc,
    confidence: conf,
    reason: String(triage.reason || ''),
    below_triage_min: conf < T_TRIAGE_MIN,
    send_threshold_met: conf >= T_SEND_MIN,
    triage_min: T_TRIAGE_MIN,
    send_min: T_SEND_MIN,
    meeting_scheduling_ready: meeting_scheduling_ready,
    booking_page_url: '__BOOKING_PAGE_URL__'
  }
}];""".replace(
                        "__BOOKING_PAGE_URL__", BOOKING_PAGE_URL
                    )
                )
            },
            "id": uid(),
            "name": "Parse Triage",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1320, 180],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails
SET triage_category = $1,
    triage_confidence = $2,
    meeting_clarity = $3,
    updated_at = now()
WHERE id = $4::uuid
RETURNING id;""",
                "options": {
                    "queryReplacement": "={{ [\n  $json.category,\n  $json.confidence,\n  $json.meeting_clarity,\n  $json.email_id\n] }}"
                },
            },
            "id": uid(),
            "name": "Save Triage To DB",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [1540, 180],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload)
VALUES ($1::uuid, $2, $3::jsonb);""",
                "options": {
                    "queryReplacement": "={{ [\n  $('Parse Triage').item.json.email_id,\n  'triage',\n  JSON.stringify({ category: $('Parse Triage').item.json.category, meeting_clarity: $('Parse Triage').item.json.meeting_clarity, confidence: $('Parse Triage').item.json.confidence, reason: $('Parse Triage').item.json.reason })\n] }}"
                },
            },
            "id": uid(),
            "name": "Log Triage Event",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [1760, 180],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "lc",
                            "leftValue": "={{ $('Parse Triage').item.json.below_triage_min === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Low Triage Confidence?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [1980, 180],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'processed', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Parse Triage').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Processed No Send",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [2200, 400],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload) VALUES ($1::uuid, $2, $3::jsonb);""",
                "options": {
                    "queryReplacement": "={{ [\n  $('Parse Triage').item.json.email_id,\n  'skipped_low_confidence',\n  JSON.stringify({ triage_min: $('Parse Triage').item.json.triage_min })\n] }}"
                },
            },
            "id": uid(),
            "name": "Log Skip Low Conf",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [2420, 400],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {
                            "id": "n1",
                            "leftValue": "={{ $('Parse Triage').item.json.category === 'noise' }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Is Noise?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [2200, 120],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'ignored', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Parse Triage').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Ignored",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [2420, 0],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload) VALUES ($1::uuid, 'noise_ignored', '{}'::jsonb);""",
                "options": {"queryReplacement": "={{ [$('Parse Triage').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Log Noise",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [2640, 0],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {
                            "id": "o1",
                            "leftValue": "={{ $('Parse Triage').item.json.category === 'operational' }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Is Operational?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [2420, 200],
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "msr",
                            "leftValue": "={{ $('Parse Triage').item.json.meeting_scheduling_ready === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Meeting: Scheduling Ready?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [2520, 220],
        }
    )

    # Operational: LLM draft
    nodes.append(
        {
            "parameters": {
                "model": "llama-3.1-8b-instant",
                "options": {"temperature": 0.4},
            },
            "id": uid(),
            "name": "Groq Chat: Operational",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "position": [2640, 280],
            "credentials": {"groqApi": {"id": "CONFIGURE_GROQ", "name": "Groq account"}},
        }
    )
    nodes.append(
        {
            "parameters": {
                "promptType": "define",
                "text": """=You write professional email replies. Output ONLY the reply body (no subject line).

Use a blank line between greeting, body, and sign-off. Do not send one dense paragraph.

Subject: {{ $('Parse Triage').first().json.subject }}
From: {{ $('Parse Triage').first().json.from_email }}

Their message:
{{ $('Parse Triage').first().json.raw_text }}""",
                "batching": {},
            },
            "id": uid(),
            "name": "LLM: Draft Operational",
            "type": "@n8n/n8n-nodes-langchain.chainLlm",
            "typeVersion": 1.9,
            "position": [2640, 120],
        }
    )

    nodes.append(
        {
            "parameters": {
                "jsCode": """const r = $input.first().json;
const body = r.text || r.output || r.response || r.choices?.[0]?.message?.content || '';
const p = $('Parse Triage').first().json;
return [{ json: { ...p, draft_body: String(body || '').trim() } }];"""
            },
            "id": uid(),
            "name": "Extract Operational Draft",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2860, 120],
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "sok",
                            "leftValue": "={{ $json.send_threshold_met === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Operational Send OK?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [3080, 120],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "reply",
                "emailType": "text",
                "messageId": "={{ $json.msg_id }}",
                "message": "={{ $json.draft_body }}",
                "options": {},
            },
            "id": uid(),
            "name": "Gmail Send Operational",
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 2.2,
            "position": [3300, 40],
            "credentials": {"gmailOAuth2": {"id": "CONFIGURE_GMAIL", "name": "Gmail account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'sent', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Extract Operational Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Sent Operational",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3520, 40],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload) VALUES ($1::uuid, 'sent_operational', $2::jsonb);""",
                "options": {
                    "queryReplacement": "={{ [\n  $('Extract Operational Draft').item.json.email_id,\n  JSON.stringify({ auto: true })\n] }}"
                },
            },
            "id": uid(),
            "name": "Log Sent Operational",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3740, 40],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'processed', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Extract Operational Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Processed Op No Send",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3300, 200],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "model": "llama-3.1-8b-instant",
                "options": {"temperature": 0.35},
            },
            "id": uid(),
            "name": "Groq Chat: Meeting Clarify",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "position": [2640, 520],
            "credentials": {"groqApi": {"id": "CONFIGURE_GROQ", "name": "Groq account"}},
        }
    )
    nodes.append(
        {
            "parameters": {
                "promptType": "define",
                "text": (
                    """=You write short, professional plain-text email replies. Output ONLY the reply body (no subject line).

This message is an **ambiguous meeting request**: the sender has not given enough detail to schedule directly. Your job is to send a **booking-link-first** reply.

Rules:
- Greet using a natural line with their first name if you can infer it from the From line context; otherwise "Hi,".
- Keep it short: one to three short paragraphs, no bullet list.
- Explicitly say they can book a suitable time using the booking link below.
- Do not ask for 2-3 time windows.
- Do not list proposed availability.
- Do not promise unverified times.
- Never use placeholders like [Name].

Booking link (include it in the reply): __BOOKING_PAGE_URL__

Subject: {{ $('Parse Triage').first().json.subject }}
From: {{ $('Parse Triage').first().json.from_email }}

Their message:
{{ $('Parse Triage').first().json.raw_text }}""".replace(
                        "__BOOKING_PAGE_URL__", BOOKING_PAGE_URL
                    )
                ),
                "batching": {},
            },
            "id": uid(),
            "name": "LLM: Meeting Clarify",
            "type": "@n8n/n8n-nodes-langchain.chainLlm",
            "typeVersion": 1.9,
            "position": [2640, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "jsCode": """const r = $input.first().json;
const body = r.text || r.output || r.response || r.choices?.[0]?.message?.content || '';
const p = $('Parse Triage').first().json;
return [{ json: { ...p, draft_body: String(body || '').trim() } }];"""
            },
            "id": uid(),
            "name": "Extract Clarify Draft",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2860, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "cok",
                            "leftValue": "={{ $json.send_threshold_met === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Clarify Send OK?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [3080, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "reply",
                "emailType": "text",
                "messageId": "={{ $json.msg_id }}",
                "message": "={{ $json.draft_body }}",
                "options": {},
            },
            "id": uid(),
            "name": "Gmail Send Clarify",
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 2.2,
            "position": [3300, 280],
            "credentials": {"gmailOAuth2": {"id": "CONFIGURE_GMAIL", "name": "Gmail account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'sent', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Extract Clarify Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Sent Clarify",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3520, 280],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload) VALUES ($1::uuid, $2, $3::jsonb);""",
                "options": {
                    "queryReplacement": "={{ [\n  $('Extract Clarify Draft').item.json.email_id,\n  'sent_meeting_clarify',\n  JSON.stringify({ meeting_clarity: 'ambiguous', reason: $('Extract Clarify Draft').item.json.reason })\n] }}"
                },
            },
            "id": uid(),
            "name": "Log Sent Clarify",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3740, 280],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'processed', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Extract Clarify Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Processed Clarify No Send",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3300, 440],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    # Meeting: prior auto-bookings (for per-day / per-week caps)
    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """SELECT COALESCE(
  json_agg(elem ORDER BY elem),
  '[]'::json
) AS booked_starts
FROM (
  SELECT DISTINCT trim(payload->>'slot_start') AS elem
  FROM processing_events
  WHERE step = 'sent_meeting'
    AND nullif(trim(payload->>'slot_start'), '') IS NOT NULL
) sub;""",
                "options": {},
            },
            "id": uid(),
            "name": "Postgres: Booked Slot Times",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [2520, 360],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    # Meeting: Calendar get all
    nodes.append(
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "primary",
                    "mode": "list",
                    "cachedResultName": "primary",
                },
                "returnAll": True,
                "timeMin": "={{ new Date().toISOString() }}",
                "timeMax": "={{ new Date(Date.now() + 21 * 86400000).toISOString() }}",
                "options": {"orderBy": "startTime", "recurringEventHandling": "expand"},
            },
            "id": uid(),
            "name": "Get Calendar Events",
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [2640, 360],
            "credentials": {"googleCalendarOAuth2Api": {"id": "CONFIGURE_CAL", "name": "Google Calendar account"}},
        }
    )

    nodes.append(
        {
            "parameters": {"jsCode": SLOT_CODE},
            "id": uid(),
            "name": "Compute Free Slots",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2860, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "blo",
                            "leftValue": "={{ $json.booking_link_only === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Meeting: Booking Link Only?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [2970, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "model": "llama-3.1-8b-instant",
                "options": {"temperature": 0.35},
            },
            "id": uid(),
            "name": "Groq Chat: Meeting",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "position": [3080, 520],
            "credentials": {"groqApi": {"id": "CONFIGURE_GROQ", "name": "Groq account"}},
        }
    )
    nodes.append(
        {
            "parameters": {
                "promptType": "define",
                "text": """=You write concise professional email replies as plain text. Output ONLY the reply body (no subject line). Never use placeholders like [Name].

Formatting (required):
- Greeting on its own line using the sender first name below (if it is literally "there", use "Hi," instead of a name).
- Blank line, then short paragraphs with blank lines between them.
- If you list more than one time, each time must be its own line starting with "- " (bullet list). Never put all times in one line.

Content:
- This workflow does not create calendar events from your reply. Propose times for them to confirm, or point them to the booking page for self-serve booking.
- If "Offered times" is non-empty: put the best option first using each slot's "display" text; then optional bullets for other slots.
- If "Availability instructions" is non-empty, follow them.
- If there are no offered times: apologize briefly, share the booking URL only, do not invent times.

Sender first name (for greeting): {{ $('Compute Free Slots').first().json.sender_first_name }}
Subject: {{ $('Compute Free Slots').first().json.subject }}
From: {{ $('Compute Free Slots').first().json.from_email }}

Their message:
{{ $('Compute Free Slots').first().json.raw_text }}

Availability instructions (may be empty):
{{ $('Compute Free Slots').first().json.availability_hint }}

Offered times (JSON): {{ JSON.stringify($('Compute Free Slots').first().json.slots || []) }}
Booking page: {{ $('Compute Free Slots').first().json.booking_url }}""",
                "batching": {},
            },
            "id": uid(),
            "name": "LLM: Draft Meeting",
            "type": "@n8n/n8n-nodes-langchain.chainLlm",
            "typeVersion": 1.9,
            "position": [3080, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "jsCode": """const slot = $('Compute Free Slots').first().json;
const p = $('Parse Triage').first().json;
const from = String(slot.from_email || '');
let senderFirst = String(slot.sender_first_name || '').trim();
if (!senderFirst) {
  const q = from.match(/^([^<]+)</);
  if (q) senderFirst = q[1].trim().replace(/^["']+|["']+$/g, '').split(/\\s+/)[0];
  if (!senderFirst) senderFirst = from.split('@')[0].split(/[._+-]/)[0] || 'there';
}
function buildLinkOnlyBody() {
  const when = slot.requested_summary || 'the time you asked for';
  const url = String(slot.booking_url || '').trim();
  const greet = (senderFirst && senderFirst !== 'there') ? ('Hi ' + senderFirst + ',') : 'Hi,';
  return greet + '\\n\\nThanks for suggesting ' + when + '. That time does not work on my side from this inbox (calendar conflict, outside my working hours, or I am at my limit for automated holds).\\n\\nPlease pick a time using my booking page. Completing the booking creates the calendar invite:\\n' + url + '\\n\\nIf you prefer, reply with a few alternatives and we will align manually.\\n\\nBest regards';
}
let draft_body;
if (slot.booking_link_only === true) {
  draft_body = buildLinkOnlyBody();
} else {
  const r = $input.first().json;
  draft_body = String(r.text || r.output || r.response || r.choices?.[0]?.message?.content || '').trim();
}
const sl = (slot.slots || [])[0];
return [{ json: {
  email_id: slot.email_id,
  msg_id: slot.msg_id,
  thread_id: slot.thread_id,
  from_email: slot.from_email,
  subject: slot.subject,
  confidence: p.confidence,
  send_threshold_met: p.send_threshold_met === true,
  draft_body,
  slots: slot.slots || [],
  has_slots: slot.has_slots === true,
  availability_hint: String(slot.availability_hint || ''),
  first_slot_display: sl && sl.display ? sl.display : '',
  auto_book_eligible: slot.auto_book_eligible === true,
  booking_link_only: slot.booking_link_only === true,
  sender_first_name: senderFirst
} }];"""
            },
            "id": uid(),
            "name": "Merge Meeting Draft",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [3300, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                    "conditions": [
                        {
                            "id": "ms",
                            "leftValue": "={{ $json.send_threshold_met === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Meeting Send OK?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [3520, 360],
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "reply",
                "emailType": "text",
                "messageId": "={{ $json.msg_id }}",
                "message": "={{ $json.draft_body }}",
                "options": {},
            },
            "id": uid(),
            "name": "Gmail Send Meeting",
            "type": "n8n-nodes-base.gmail",
            "typeVersion": 2.2,
            "position": [3740, 280],
            "credentials": {"gmailOAuth2": {"id": "CONFIGURE_GMAIL", "name": "Gmail account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {
                            "id": "hs",
                            "leftValue": "={{ $('Merge Meeting Draft').item.json.auto_book_eligible === true }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
            "id": uid(),
            "name": "Has Valid Slots?",
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.3,
            "position": [3960, 280],
        }
    )

    nodes.append(
        {
            "parameters": {
                "calendar": {
                    "__rl": True,
                    "value": "primary",
                    "mode": "list",
                    "cachedResultName": "primary",
                },
                "start": "={{ $('Merge Meeting Draft').item.json.slots[0].start }}",
                "end": "={{ $('Merge Meeting Draft').item.json.slots[0].end }}",
                "additionalFields": {
                    "summary": "={{ 'Meeting: ' + ($('Merge Meeting Draft').item.json.subject || 'Guest').slice(0, 80) }}",
                    "description": "={{ 'Guest: ' + $('Merge Meeting Draft').item.json.from_email + '\\n\\n(AI triage auto-booked from free slot.)' }}",
                },
            },
            "id": uid(),
            "name": "Create Calendar Event",
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [4180, 200],
            "credentials": {"googleCalendarOAuth2Api": {"id": "CONFIGURE_CAL", "name": "Google Calendar account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "select": "channel",
                "channelId": {
                    "__rl": True,
                    "value": "#meetings",
                    "mode": "name",
                },
                "text": """={{ '*Meeting booked (auto)*\\n' + 'With: ' + $('Merge Meeting Draft').first().json.from_email + '\\nTopic: ' + ($('Merge Meeting Draft').first().json.subject || '') + '\\nWhen: ' + (($('Merge Meeting Draft').first().json.slots[0] || {}).display || ($('Merge Meeting Draft').first().json.slots[0] || {}).start || 'n/a') }}""",
                "otherOptions": {},
            },
            "id": uid(),
            "name": "Slack: Meeting Booked",
            "type": "n8n-nodes-base.slack",
            "typeVersion": 2.2,
            "position": [4340, 200],
            "webhookId": uid(),
            "continueOnFail": True,
            "credentials": {"slackApi": {"id": "CONFIGURE_SLACK", "name": "Slack account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'sent', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Merge Meeting Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Sent Meeting",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [4520, 280],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """INSERT INTO processing_events (email_id, step, payload) VALUES ($1::uuid, $2, $3::jsonb);""",
                "options": {
                    "queryReplacement": "={{ [\n  $('Merge Meeting Draft').item.json.email_id,\n  'sent_meeting',\n  JSON.stringify({\n    calendar_created: $('Merge Meeting Draft').item.json.auto_book_eligible === true,\n    slot_start: ($('Merge Meeting Draft').item.json.slots[0] || {}).start || null,\n    slot_display: ($('Merge Meeting Draft').item.json.slots[0] || {}).display || null,\n    from_email: $('Merge Meeting Draft').item.json.from_email,\n    subject: $('Merge Meeting Draft').item.json.subject\n  })\n] }}"
                },
            },
            "id": uid(),
            "name": "Log Sent Meeting",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [4740, 280],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    nodes.append(
        {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE emails SET status = 'processed', updated_at = now() WHERE id = $1::uuid;""",
                "options": {"queryReplacement": "={{ [$('Merge Meeting Draft').item.json.email_id] }}"},
            },
            "id": uid(),
            "name": "Mark Processed Meeting No Send",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": [3740, 480],
            "credentials": {"postgres": {"id": "CONFIGURE_POSTGRES", "name": "Postgres account"}},
        }
    )

    # --- Connections ---
    def edge(dst: str) -> dict:
        return {"node": dst, "type": "main", "index": 0}

    conn = {
        "Gmail Trigger": {"main": [[edge("Prepare Email Fields")]]},
        "Prepare Email Fields": {"main": [[edge("Decode Email Text")]]},
        "Decode Email Text": {"main": [[edge("Postgres Insert Email")]]},
        "Postgres Insert Email": {"main": [[edge("Is New Email?")]]},
        "Is New Email?": {
            "main": [
                [edge("Store Email Record ID")],
                [edge("Skip Duplicate")],
            ]
        },
        "Store Email Record ID": {"main": [[edge("LLM: Triage")]]},
        "LLM: Triage": {"main": [[edge("Parse Triage")]]},
        "Parse Triage": {"main": [[edge("Save Triage To DB")]]},
        "Save Triage To DB": {"main": [[edge("Log Triage Event")]]},
        "Log Triage Event": {"main": [[edge("Low Triage Confidence?")]]},
        "Low Triage Confidence?": {
            "main": [
                [edge("Mark Processed No Send")],
                [edge("Is Noise?")],
            ]
        },
        "Mark Processed No Send": {"main": [[edge("Log Skip Low Conf")]]},
        "Is Noise?": {
            "main": [
                [edge("Mark Ignored")],
                [edge("Is Operational?")],
            ]
        },
        "Mark Ignored": {"main": [[edge("Log Noise")]]},
        "Is Operational?": {
            "main": [
                [edge("LLM: Draft Operational")],
                [edge("Meeting: Scheduling Ready?")],
            ]
        },
        "Meeting: Scheduling Ready?": {
            "main": [
                [edge("Postgres: Booked Slot Times")],
                [edge("LLM: Meeting Clarify")],
            ]
        },
        "LLM: Meeting Clarify": {"main": [[edge("Extract Clarify Draft")]]},
        "Extract Clarify Draft": {"main": [[edge("Clarify Send OK?")]]},
        "Clarify Send OK?": {
            "main": [
                [edge("Gmail Send Clarify")],
                [edge("Mark Processed Clarify No Send")],
            ]
        },
        "Gmail Send Clarify": {"main": [[edge("Mark Sent Clarify")]]},
        "Mark Sent Clarify": {"main": [[edge("Log Sent Clarify")]]},
        "Postgres: Booked Slot Times": {"main": [[edge("Get Calendar Events")]]},
        "LLM: Draft Operational": {"main": [[edge("Extract Operational Draft")]]},
        "Extract Operational Draft": {"main": [[edge("Operational Send OK?")]]},
        "Operational Send OK?": {
            "main": [
                [edge("Gmail Send Operational")],
                [edge("Mark Processed Op No Send")],
            ]
        },
        "Gmail Send Operational": {"main": [[edge("Mark Sent Operational")]]},
        "Mark Sent Operational": {"main": [[edge("Log Sent Operational")]]},
        "Get Calendar Events": {"main": [[edge("Compute Free Slots")]]},
        "Compute Free Slots": {"main": [[edge("Meeting: Booking Link Only?")]]},
        "Meeting: Booking Link Only?": {
            "main": [
                [edge("Merge Meeting Draft")],
                [edge("LLM: Draft Meeting")],
            ]
        },
        "LLM: Draft Meeting": {"main": [[edge("Merge Meeting Draft")]]},
        "Merge Meeting Draft": {"main": [[edge("Meeting Send OK?")]]},
        "Meeting Send OK?": {
            "main": [
                [edge("Gmail Send Meeting")],
                [edge("Mark Processed Meeting No Send")],
            ]
        },
        "Gmail Send Meeting": {"main": [[edge("Has Valid Slots?")]]},
        "Has Valid Slots?": {
            "main": [
                [edge("Create Calendar Event")],
                [edge("Mark Sent Meeting")],
            ]
        },
        "Create Calendar Event": {"main": [[edge("Slack: Meeting Booked")]]},
        "Slack: Meeting Booked": {"main": [[edge("Mark Sent Meeting")]]},
        "Mark Sent Meeting": {"main": [[edge("Log Sent Meeting")]]},
        "Groq Chat: Triage": {
            "ai_languageModel": [[{"node": "LLM: Triage", "type": "ai_languageModel", "index": 0}]]
        },
        "Groq Chat: Operational": {
            "ai_languageModel": [[{"node": "LLM: Draft Operational", "type": "ai_languageModel", "index": 0}]]
        },
        "Groq Chat: Meeting": {
            "ai_languageModel": [[{"node": "LLM: Draft Meeting", "type": "ai_languageModel", "index": 0}]]
        },
        "Groq Chat: Meeting Clarify": {
            "ai_languageModel": [[{"node": "LLM: Meeting Clarify", "type": "ai_languageModel", "index": 0}]]
        },
    }

    names = {n["name"] for n in nodes}
    for src, d in conn.items():
        assert src in names, src
        for key, branches in d.items():
            if key == "main":
                for branch in branches:
                    for link in branch:
                        assert link["node"] in names, (src, link)
            elif key == "ai_languageModel":
                for branch in branches:
                    for link in branch:
                        assert link["node"] in names, (src, link)

    wf = {
        "name": "AI Email Triage and Calendar Booking Agent",
        "nodes": nodes,
        "pinData": {},
        "connections": conn,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "callerPolicy": "workflowsFromSameOwner",
            "timezone": "Africa/Lagos",
        },
        "versionId": uid(),
        "meta": {"templateCredsSetupCompleted": False},
        "id": uid(),
        "tags": [],
    }

    OUT.write_text(json.dumps(wf, indent=2), encoding="utf-8")
    print(f"Wrote {OUT} ({len(nodes)} nodes)")


if __name__ == "__main__":
    main()
