# 🛡️ Job Hunt Autopilot

> Automated pipeline tracker, 7-day follow-up engine, and predatory scam shield for job seekers navigating high-volume applications.

[![Live Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://progati-yuxdn4kmiceashkweuzupa.streamlit.app/)

---

## 📌 Problem Context
Following corporate and tech layoffs, candidates routinely apply to 100+ roles simultaneously. In the ensuing influx of responses, applicants struggle with two critical bottlenecks:
1. **Pipeline Disorganization:** Stalled applications slip through the cracks, causing candidates to miss polite, timely follow-up opportunities.
2. **Predatory Hiring Fraud:** Vulnerable candidates are targeted by sophisticated scams demanding upfront "training/laptop fees", spoofing corporate domains, or harvesting sensitive government IDs before scheduling interviews.

---

## 🚀 Key Features

### 1. 🚨 Dual-Layer Hybrid Threat Shield
- **Deterministic Heuristic Pre-Filter:** Real-time Python regex and domain verification derived from enterprise hiring fraud patterns (Kaggle) and Indian scam templates (Hugging Face). Detects free-mail spoofing (`@gmail`, `@yahoo`), upfront fee extortion, and premature document harvesting.
- **Semantic Analysis with Gemini Structured Outputs:** Leverages Gemini Flash via Pydantic schemas (`response_schema`) to evaluate context, tone, and intent with guaranteed deterministic JSON parsing.
- **Explainable Threat Cards:** Quarantines malicious emails with granular risk scoring (0–100) and actionable threat badge breakdowns.

### 2. 📋 Automated Pipeline Tracker
- Consolidates incoming communications into structured hiring stages: `Applied`, `Interview`, `Offer`, and `Rejected`.
- Zero manual input required—populates dynamically from raw inbox streams.

### 3. ⚡ Action Center: 7-Day Follow-Up Queue
- Automatically calculates staleness against the application date.
- Surfaces opportunities with $\ge 7$ days of silence.
- Features **1-Click AI Follow-Up Generation** to draft concise, professional follow-up emails, along with a **Mark Sent** workflow.

### 4. 🎯 Stretch Goal: Technical Interview Copilot
- Extracts verified interview invitations.
- Produces tailored preparation cheat sheets containing high-probability technical questions, strategic candidate talking points, and pre-interview checklists.

### 5. 📥 1-Click Pipeline Export
- Instant CSV export to synchronize sanitized job tracking records with Notion, Google Sheets, or Excel.

---

## 🛠️ Architecture & Tech Stack

```text
[Incoming Mailbox JSON / Stream]
               │
       ┌───────┴───────┐
       ▼               ▼
[Layer 1: Heuristics]  [Layer 2: Gemini Flash]
• Domain Spoof Check    • Pydantic Schema Enforcement
• Keyword Regex Vectors • Semantic Intent & Tone
       │               │
       └───────┬───────┘
               ▼
   [Unified Scored Pipeline]
               │
  ┌────────────┼────────────┐
  ▼            ▼            ▼
[Threat Hub] [Tracker]  [Action Center]
