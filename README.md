# 🤖 AI & Automation Engineering Portfolio

Welcome to my portfolio! This repository showcases production-grade autonomous systems, AI workflows, and business automation software I've developed.
My work focuses on leveraging tools like **n8n, LangChain, LLMs (Groq, OpenAI, Anthropic), and various API integrations** to replace manual processes with resilient, scalable, and intelligent workflows.

### What I build
- Workflow automation: n8n systems for inbound operations, scheduling, CRM updates, and data routing
- AI-assisted logic: LLM-driven classification, drafting, and decision support with guardrails
- Data pipelines: ingestion from unstructured sources, schema validation, dedupe, and audit logging
- API integrations: Gmail, Google Calendar, Apollo, HubSpot, Airtable, and custom REST services

---
## 📂 Projects Directory
*Below is a living index of my major automation projects. Click into any folder for full architectural documentation, workflow JSONs, and implementation guides.*

### [1. AI Email Triage and Calendar Booking Agent](https://github.com/Divine-Jude/AI-Automation-Engineer-Portfolio/tree/main/AI%20Email%20Triage%20and%20Calendar%20Booking%20Agent%20Stack)
Stack: n8n, PostgreSQL, Groq, Gmail API, Google Calendar API, Slack optional

I built one workflow that triages inbound Gmail into noise, operational, and meeting paths.
Meeting requests are split into clear versus ambiguous before any calendar logic runs. Ambiguous requests get a clarify reply. Clear requests use real calendar availability plus booking caps from Postgres.

**Key outcomes**
- Prevents duplicate processing with DB-backed dedupe
- Uses confidence thresholds to avoid low-quality sends
- Keeps outbound mail plain text and auditable
- Supports exact-match auto-booking only when conditions are safe


### [2. Autonomous Real Estate Sourcing & Legal Validation Agent](https://github.com/Divine-Jude/AI-Automation-Portfolio/tree/main/Real%20Estate%20Deal%20Flow)
**Tech Stack:** `n8n`, `Python`, `Airtable API`, `PDF Text Extraction`, `JSON, Web Scraping`, `API Integration`
- **Description:** I built an inbound sales automation flow that enriches and scores leads before CRM progression.
The workflow pulls company context, updates HubSpot records, and applies intent checks so low-quality leads do not inflate pipeline stages.

**Impact**
* Recovered about 25 minutes of manual SDR work per lead

### [3. AI Inbound Sales & CRM Pipeline](https://github.com/Divine-Jude/AI-Automation-Engineer-Portfolio/tree/main/01-Automated-Lead-Capture)
**Tech Stack:** `n8n`, `HubSpot CRM`, `Apollo API`, `Large Language Models (LLMs)`, `Prompt Engineering`, `Vector Databases`.
- **Description:** I built an end-to-end sourcing flow from unstructured listing inputs to structured investment records.
The system validates data against strict schemas, handles pagination and rate limits, and runs document checks on legal title PDFs to flag risks for human review.

---

## 🛠 Core Competencies
- **Workflow Orchestration:** Expert in designing complex, multi-stage workflows in n8n (Webhooks, API Integrations, Error logic).
- **AI/LLM Engineering:** Constructing LangChain agents, refining prompt architecture, and enforcing strict JSON data structures.
- **Data Engineering:** Web scraping, DOM parsing, Regex cleanups, and syncing scalable databases (CRMs, Databases).

## 📫 Contact
- [**LinkedIn:**](https://www.linkedin.com/in/divinejude/)
- **Email:** (mailto:Judedivine9@gmail.com)
- [**X:**](https://x.com/DivAutomation)

If you want help deploying automation systems for sales ops, inbox operations, or data-heavy workflows, send me a message.

