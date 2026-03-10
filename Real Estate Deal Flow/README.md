# AI-Powered Real Estate Dealflow & Due Diligence Automation

An autonomous n8n workflow that completely automates real estate deal sourcing, AI-driven investment analysis, broker outreach, and preliminary legal document verification. 

This system acts as an autonomous acqusitions team, scraping listings, evaluating them against strict investment criteria, negotiating/requesting documents, and analyzing title documents (C of O, Governor's Consent) for authenticity and red flags using LLMs.

## 🏗 System Architecture

The workflow is built entirely in **n8n** and divided into four core phases:

### Phase 1: Data Ingestion (Scraping & Normalization)
- Recursively fetches paginated property listings from target platforms (e.g., PropertyPro).
- Uses custom JavaScript to parse raw HTML blocks, extracting robust metadata (Price, Location, Bedrooms, Property Type, URL).
- Cleans and normalizes semi-structured descriptions, filtering out marketing fluff.

### Phase 2: AI Investment Evaluation
- **Tech Stack:** LangChain Agent + Llama 3 (via Groq/OpenAI).
- Properties are evaluated by an AI Agent prompted as a Senior Investment Analyst.
- **Strict Logic:** Checks constraints including budget (₦50m - ₦350m) and prime locations (Lekki, Ikoyi, Victoria Island).
- Output is enforced strictly as JSON, returning an investment score (1-10), a recommendation (`BUY`, `WATCH`, `SKIP`), and a technical justification.

### Phase 3: Automated Outreach & Database Routing
- **Routing:** Branching logic filters out `SKIP` properties, routing them to a "Rejected Deals" Airtable base to maintain historical data.
- **Database:** Approved (`BUY`) properties are logged to the primary "Investment Criteria" Airtable base.
- **Outreach:** The system automatically drafts and sends targeted emails (via Gmail API) to the listing agent requesting legal title documents (C of O, Registered Survey, Deed of Assignment).

### Phase 4: Automated Document Verification (Legal AI)
- A webhook/schedule-triggered Gmail node monitors for incoming broker replies containing PDF attachments.
- Text is extracted from attached PDFs and passed to a highly constrained AI Legal Analyst Agent.
- The AI evaluates document authenticity, cross-references location data, and flags anomalies (missing signatures, expired dates).
- **Smart Merge Algorithm:** A custom JS node programmatically handles subset matching, connecting the asynchronous email reply back to the exact initial property row in Airtable, updating the CRM with the Document Verification results.

## 🛠 Tech Stack
- **Orchestration:** n8n
- **AI / LLMs:** LangChain, Llama-3.1-8b-instant, Llama-3.3-70b-versatile
- **Database / CRM:** Airtable
- **Comms:** Gmail API, HTTP Requests

## 🚀 How to Use / Install
1. Clone this repository and import the [Real_Estate_DealFlow_Automation.json](cci:7://file:///Users/divinejude/Real-Estate-Automation/Real_Estate_DealFlow_Automation.json:0:0-0:0) file into your n8n instance.
2. Connect your credentials:
   - `Airtable Personal Access Token`
   - `Gmail API OAuth2`
   - `OpenAI/Groq API Key`
3. Update the Airtable Base/Table IDs in the respective nodes.
4. Activate the schedule trigger or run manually.
