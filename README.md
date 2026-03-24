# 🤖 AI & Automation Engineering Portfolio

Welcome to my portfolio! This repository showcases production-grade autonomous systems, AI workflows, and business automation software I've developed.
My work focuses on leveraging tools like **n8n, LangChain, LLMs (Groq, OpenAI, Anthropic), and various API integrations** to replace manual processes with resilient, scalable, and intelligent workflows.

---
## 📂 Projects Directory
*Below is a living index of my major automation projects. Click into any folder for full architectural documentation, workflow JSONs, and implementation guides.*

### [1. Real Estate Dealflow & Due Diligence Automation](https://github.com/Divine-Jude/AI-Automation-Portfolio/tree/main/Real%20Estate%20Deal%20Flow)
**Tech Stack:** `n8n`, `Python`, `Airtable API`, `PDF Text Extraction`, `JSON, Web Scraping`, `API Integration`
- **Description:** I designed a complete end-to-end pipeline to automate real estate deal-flow evaluation. The system crawls unstructured property data, validates it against strict JSON schemas and handles data ingestion via the Airtable API. I also built a specialized AI compliance agent for this pipeline. It securely reads complex PDF legal title documents and automatically flags missing signatures, expired dates or compliance risks so human reviewers do not have to read them manually. To make this work at scale, I wrote custom logic to handle recursive pagination, regex data sanitisation and API rate-limiting.

### [2. [AI Inbound Sales & CRM Pipeline]](https://github.com/Divine-Jude/AI-Automation-Engineer-Portfolio/tree/main/01-Automated-Lead-Capture)
**Tech Stack:** `n8n`, `HubSpot CRM`, `Apollo API`, `Large Language Models (LLMs)`, `Prompt Engineering`, `Vector Databases`.
- **Description:** I built an autonomous inbound sales pipeline that automatically qualifies leads before sales reps engage. The workflow triggers upon a new lead, uses an AI research agent and vector database to pull real-time corporate news via the Apollo API, and scores the lead. It then updates HubSpot CRM directly. To prevent pipeline inflation, I built an intent analysis safeguard that requires human verification before moving a lead to the "Deal" stage. This automation recovered roughly 25 minutes of manual work per lead for the sales development team.

---

## 🛠 Core Competencies
- **Workflow Orchestration:** Expert in designing complex, multi-stage workflows in n8n (Webhooks, API Integrations, Error logic).
- **AI/LLM Engineering:** Constructing LangChain agents, refining prompt architecture, and enforcing strict JSON data structures.
- **Data Engineering:** Web scraping, DOM parsing, Regex cleanups, and syncing scalable databases (CRMs, Databases).

## 📫 Contact
If you'd like to discuss building out AI automations for your business, feel free to reach out.
- [**LinkedIn:**](https://www.linkedin.com/in/divinejude/)
- **Email:** (mailto:Judedivine9@gmail.com)
- [**X:**](https://x.com/DivAutomation)
