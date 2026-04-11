# 2-hour demo strategy (reference — not the PRD)

Practical way to treat this as a **2-hour demo** (not a full PRD build) and still show understanding of the assignment.

## What they’re really testing

- You can read a PRD, prioritize, and ship something runnable without hand-holding.
- You respect constraints (2 hours, no clarification emails).
- You’re transparent about gaps instead of pretending the PDFs are pixel-perfect.

## Next move (order of operations)

1. Skim the video once (even at 1.5×): focus on timestamps the PRD lists (SACS ~13:08, TCC ~20:52, data list ~29:14). Confirm layout intent, not every field.
2. Lock a **“demo slice”** in writing (3–5 bullets) so you don’t scope-creep.
3. Build the **thinnest vertical path**: some client context → quarterly inputs → math you can defend → one primary output (PDF or strong preview).
4. **Deploy early** (broken deployable app beats perfect localhost).
5. Write a short **“Gaps & assumptions”** section (bullet list).
6. Record Loom (&lt;2 min): problem → what you built → calculations → what’s out of scope for 2h → link.

## What to actually build in ~2 hours

The PRD is a full product; in two hours ship a **credible slice** that mirrors their pain: manual numbers in → deterministic math out → report-shaped artifact.

| Priority | Ship | Defer / stub |
|----------|------|----------------|
| **Must** | Quarterly-style form with a **subset** of fields; live totals using their rules: excess = inflow − outflow; retirement per spouse; non-retirement excluding trust; grand total including trust; liabilities summed but **not** netted | Full CRM, SQLite on Railway volume, report history, every account type |
| **Must** | **Visible calculation breakdown** on the page (so reviewers see business rules) | Pixel-perfect bubble/circle chart PDFs |
| **Should** | **One** PDF (SACS or TCC) with clearly approximate layout **or** print-ready HTML report + note “PDF = same layout via ReportLab/WeasyPrint” | Second PDF, Canva API |
| **Nice** | Second client, “use last quarter” stub | Dropbox, email, auth |

## Stack

PRD suggests HTML/CSS/JS + Python + SQLite on Railway. For a demo, Flask/FastAPI + Jinja + minimal SQLite is fine; even static front + localStorage if you state persistence is stubbed. **Judgment matters**, not matching production stack exactly in 120 minutes.

**Canva:** PRD marks it optional; “PDF download only” is aligned. Skip Canva unless you have a key and ~20 minutes.

## Gaps to document (example bullets)

- No access to sample PDFs or Data Point List image at full resolution—layouts approximate.
- Account bubble counts (1–6 per section) not fully dynamic—fixed demo structure or partial dynamic list.
- Insurance deductibles for private reserve target: assumed 0 or placeholder if not in PRD text.
- Canva export not implemented; report history not implemented.
- Auth / multi-user not in scope for demo.

**Tone:** factual, no apology tour—“here’s what I assumed and what I’d confirm in a real sprint.”

## Loom structure (&lt;2 minutes)

- **10s** – Who the user is and the problem (manual prep → structured entry + math).
- **40s** – Screen: client/context → form → live numbers → explicitly call out liabilities separate from net worth and trust not in non-retirement total.
- **40s** – Output: PDF or print preview; say honestly if layout is simplified.
- **20s** – 2–3 gaps + what you’d do next with more time.

## Practical deployment

Use whatever ships fastest (Railway default, or Render / Fly.io). Single Docker-style or `requirements.txt` + Procfile is enough. Send the public URL; if flaky, mention briefly in email.

## Bottom line

Define the 2-hour slice, prove the math and workflow, ship **one** report output, list gaps, then Loom + link. Matches PRD spirit and time box without asking them questions.

---

_Video timestamps (from PRD): SACS ~13:08, TCC ~20:52, data list ~29:14._
