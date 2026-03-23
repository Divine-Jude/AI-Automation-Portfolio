# AI Inbound Sales Pipeline

A system built to solve one of the most expensive problems in B2B sales: Sales Development Representatives (SDRs) wasting 80% of their day on research and data entry instead of actually talking to prospects.

When someone fills out a contact form, this n8n workflow scores the lead, pulls their company's financial data via Apollo, runs an AI research agent to find live news and case studies, writes everything to HubSpot, and pings the team on Slack. 

It does this before a human ever looks at the submission. It recovers approximately 25 minutes of manual work per lead.

---

## The business problems this solves

**1. CRM data entry waste**
SDRs spend hours manually typing information into HubSpot. This system automatically creates the Company record, links the Contact record, and sets up the follow-up Task. Zero manual keystrokes required.

**2. Wasting time on bad leads**
Sales teams often call unqualified leads simply because they are next on the list. This workflow scores every lead instantly based on job title and company size. Leads that score below a set threshold are dropped immediately. They never reach the CRM and never distract the sales team.

**3. Calling without context**
A fast response time matters, but calling a prospect without knowing anything about their business leads to poor conversion rates. This system uses the Apollo API to find the prospect's annual revenue, tech stack, and HQ location—data they did not provide in the form. The SDR has the full picture before they pick up the phone.

**4. Digging for case studies**
When a prospect raises an objection about implementation risk, SDRs usually have to put them on hold or follow up later while they search a shared drive for a relevant case study. This system uses a vector database to automatically surface the most relevant past project based on the prospect's industry. The case study is waiting in the SDR's HubSpot task before they even make the call.

**5. Pipeline inflation**
Many automation tools create a "Deal" in the CRM the moment a form is submitted. This creates fake pipeline revenue that ruins sales forecasting. This system stops at the Task level. Deals are only created when a human SDR actually speaks to the prospect and verbally qualifies them.

---

## How the architecture maps to business value

| The Technical Layer | The Business Outcome |
|---|---|
| **n8n Webhook & JS Logic** | Captures the lead instantly and normalizes the data so HubSpot does not reject it. Executes the scoring algorithm to filter out bad leads. |
| **Apollo.io API** | Pulls firmographic data (revenue, tech stack, location) so the SDR does not have to hunt for it on LinkedIn and Crunchbase. |
| **LangChain + ChatGPT-5** | Replaces the manual Google search. It reads live company news and retrieves internal case studies, returning exactly 3 talking points for the SDR. |
| **HubSpot API Sync** | Handles all CRM data entry automatically. Creates relationally linked objects (Company -> Contact -> Task) to keep the database perfectly clean. |
| **Slack Integration** | Alerts the team the second a high-value lead is ready to be called, driving response times down to under 90 seconds. |

---

## Setup

1. Clone this repo
2. Import `workflow.json` into n8n
3. Add credentials for Apollo, HubSpot, SerpAPI, Slack, and your LLM
4. Activate the workflow
5. Point your form's action URL to the webhook endpoint

---

**Divine Jude** — AI Automation Engineer
[LinkedIn](https://linkedin.com) · [Medium](https://medium.com)
