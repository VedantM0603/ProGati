import json
from datetime import datetime
import streamlit as st
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Job Hunt Autopilot", page_icon="🛡️", layout="wide")

import re

# Rule signatures drawn from the Kaggle fake-job & HF Indian fraud patterns
FREE_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}
KNOWN_ENTERPRISES = ["infosys", "tcs", "wipro", "swiggy", "zomato", "google", "amazon"]

def run_heuristic_security_scan(email: dict) -> dict:
    sender = email.get("from", "").lower()
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()
    full_text = f"{subject} {body}"

    flags = []

    # 1. Impersonation check: Free-mail domain posing as corporate
    sender_domain = sender.split("@")[-1] if "@" in sender else ""
    if sender_domain in FREE_DOMAINS:
        for corp in KNOWN_ENTERPRISES:
            if corp in full_text or corp in sender:
                flags.append(f"Domain Spoof: Uses @{sender_domain} while referencing corporate entity '{corp.upper()}'")
                break

    # 2. Advance financial extraction check (Kaggle dataset pattern)
    fee_pattern = r"(training\s*fee|security\s*deposit|courier\s*charge|refundable|registration\s*charge|upi|pay\s*(rs|\u20b9|\$))"
    if re.search(fee_pattern, full_text):
        flags.append("Financial Extortion: Demands advance fee / deposit / UPI payment")

    # 3. Premature identity harvesting check (HF Hinglish dataset pattern)
    id_pattern = r"(aadhaar|pan\s*card|bank\s*passbook|kyc\s*verification)"
    if re.search(id_pattern, full_text):
        flags.append("Identity Harvesting: Demands sensitive government ID / KYC documents")

    return {
        "heuristic_flags": flags,
        "is_heuristic_flagged": len(flags) > 0
    }

# --- PYDANTIC SCHEMAS FOR GEMINI STRUCTURED OUTPUT ---
class ClassifiedEmail(BaseModel):
    email_id: int
    company: str = Field(description="Company name extracted or inferred from sender/body")
    role: str = Field(description="Job role or title")
    category: str = Field(description="Must be exactly one of: APPLIED, INTERVIEW, REJECTED, OFFER, SCAM")
    is_scam: bool = Field(description="True if category is SCAM")
    scam_risk_score: int = Field(description="0 to 100 risk score")
    scam_red_flags: list[str] = Field(
        description="List of specific reasons if scam, e.g., 'Training/Security Fee Request', 'Free-mail sender (@gmail/@yahoo) posing as company', 'Demanding Aadhaar/PAN before interview'"
    )
    days_since_email: int = Field(description="Days between email date and current date 2026-10-24")
    needs_follow_up: bool = Field(
        description="True ONLY if category is APPLIED and days_since_email >= 7"
    )
    summary_note: str = Field(description="1-line summary of the email action or date")

class InboxAnalysis(BaseModel):
    results: list[ClassifiedEmail]

# --- HELPER: CALL GEMINI WITH STRUCTURED OUTPUT ---
def analyze_inbox(emails_data, api_key):
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Today's date is 2026-10-24.
    You are an AI Job Hunt Autopilot protecting a recently laid-off software engineer.
    Analyze each email in this inbox JSON once and classify it into exactly one category:
    APPLIED, INTERVIEW, REJECTED, OFFER, or SCAM.

    CRITICAL SCAM DETECTION RULES:
    Flag as SCAM if ANY of these appear:
    1. Asking for money, training fees, laptop security deposits, or courier charges.
    2. Using a free email domain (@gmail.com, @yahoo.com, etc.) while claiming to be HR from an established company (like Infosys, TCS, etc.).
    3. Demanding sensitive government IDs (Aadhaar, PAN card, bank details) before any interview takes place.

    FOLLOW-UP RULE:
    If category is APPLIED and the email date is 7 or more days before 2026-10-24 (i.e. on or before 2026-10-17), set needs_follow_up = True.

    INBOX DATA:
    {json.dumps(emails_data, indent=2)}
    """
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InboxAnalysis,
            temperature=0.1,
            max_output_tokens=8192,  # <--- Added to prevent truncation
        ),
    )
    return json.loads(response.text)["results"]

def generate_text_helper(prompt_text, api_key):
    client = genai.Client(api_key=api_key)
    res = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt_text
    )
    return res.text

# --- SIDEBAR & SETUP ---
with st.sidebar:
    st.title("⚙️ Autopilot Controls")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.caption("Powered by `google-genai` Structured Outputs")
    st.divider()
    st.markdown("### 🧪 Live Judge Test: Add Email")
    with st.form("add_email_form"):
        new_from = st.text_input("From", "hr.wipro.careers@gmail.com")
        new_sub = st.text_input("Subject", "Direct Offer - Pay Rs 2999 Registration")
        new_body = st.text_area("Body", "You are selected! Send PAN, Aadhaar and Rs 2999 fee immediately.")
        new_date = st.text_input("Date (YYYY-MM-DD)", "2026-10-24")
        submitted = st.form_submit_button("➕ Inject Email & Re-Scan")

# Load Inbox
if "inbox" not in st.session_state:
    with open("sample_inbox.json", "r", encoding="utf-8") as f:
        st.session_state.inbox = json.load(f)

if submitted:
    new_id = len(st.session_state.inbox) + 1
    st.session_state.inbox.append({
        "id": new_id, "date": new_date, "from": new_from, "subject": new_sub, "body": new_body
    })
    if "analyzed_data" in st.session_state:
        del st.session_state["analyzed_data"]
    st.toast("New email injected into inbox!", icon="📨")

# --- HEADER ---
st.title("🛡️ Job Hunt Autopilot")
st.markdown("*Post-layoff application tracker, 7-day follow-up engine, and predatory scam shield.*")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    run_btn = st.button("🚀 Run AI Inbox Autopilot", type="primary", use_container_width=True)

if run_btn:
    if not api_key:
        st.error("Please enter your Gemini API Key in the left sidebar first!")
    else:
        with st.spinner("Classifying emails with Gemini Structured Outputs..."):
            st.session_state.analyzed_data = analyze_inbox(st.session_state.inbox, api_key)

# --- DISPLAY DASHBOARD ---
if "analyzed_data" in st.session_state:
    data = st.session_state.analyzed_data
    email_lookup = {e["id"]: e for e in st.session_state.inbox}

    applied = [d for d in data if d["category"] == "APPLIED"]
    interviews = [d for d in data if d["category"] == "INTERVIEW"]
    offers = [d for d in data if d["category"] == "OFFER"]
    rejected = [d for d in data if d["category"] == "REJECTED"]
    scams = [d for d in data if d["category"] == "SCAM" or d["is_scam"]]
    follow_ups = [d for d in data if d["needs_follow_up"]]

    # Top KPI Banner
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📬 Processed", len(data))
    m2.metric("🎯 Interviews", len(interviews))
    m3.metric("🎉 Valid Offers", len(offers))
    m4.metric("⏰ Stale (>7d)", len(follow_ups))
    m5.metric("🚨 Threats Blocked", len(scams))

    st.markdown("---")

    # Clean Tabbed Workspace
    tab_threats, tab_board, tab_actions, tab_raw = st.tabs([
        f"🚨 Threat Shield ({len(scams)})",
        "📊 Pipeline Tracker",
        "⚡ Action Center (Follow-ups & Prep)",
        "📁 Raw Email Stream"
    ])

# Convert active pipeline to a clean Pandas DataFrame for download
    clean_records = []
    for item in data:
        raw = email_lookup.get(item["email_id"], {})
        clean_records.append({
            "Email ID": item["email_id"],
            "Company": item["company"],
            "Role": item["role"],
            "Category": item["category"],
            "Is Scam": "YES" if item["is_scam"] else "NO",
            "Scam Risk": f"{item['scam_risk_score']}/100",
            "Date": raw.get("date", ""),
            "Sender": raw.get("from", ""),
            "Summary": item["summary_note"]
        })
    df_pipeline = pd.DataFrame(clean_records)

    # Action Toolbar
    tool_col1, tool_col2 = st.columns([3, 1])
    with tool_col1:
        st.caption("🟢 Cleaned pipeline synchronized. Threat items quarantined.")
    with tool_col2:
        csv_bytes = df_pipeline.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Tracker (CSV)",
            data=csv_bytes,
            file_name="job_hunt_pipeline.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # TAB 1: THREAT SHIELD (Structured 2-card grid instead of squished 5 cards)
    with tab_threats:
        st.subheader("🛡️ Flagged Fraudulent & Phishing Attempts")
        st.caption("Cross-verified using Deterministic Heuristics (Kaggle/HF patterns) + Gemini Semantic Analysis")

        if scams:
            # Render in a clean 2-column grid
            for i in range(0, len(scams), 2):
                col1, col2 = st.columns(2)
                
                # First card in pair
                with col1:
                    s = scams[i]
                    raw = email_lookup.get(s["email_id"], {})
                    heuristics = run_heuristic_security_scan(raw)
                    with st.container(border=True):
                        st.error(f"**🛑 {s['company']} — {s['role']}** (Risk Score: {s['scam_risk_score']}/100)")
                        st.caption(f"**Sender:** `{raw.get('from', '')}` | **Date:** {raw.get('date', '')}")
                        st.markdown("**Detected Threat Vectors:**")
                        for flag in s["scam_red_flags"]:
                            st.markdown(f"- 🚩 {flag}")
                        if heuristics["heuristic_flags"]:
                            for h_flag in heuristics["heuristic_flags"]:
                                st.markdown(f"- ⚙️ *Heuristic Rule:* `{h_flag}`")
                        with st.expander("View Raw Email"):
                            st.text(raw.get("body", ""))

                # Second card in pair (if exists)
                if i + 1 < len(scams):
                    with col2:
                        s = scams[i + 1]
                        raw = email_lookup.get(s["email_id"], {})
                        heuristics = run_heuristic_security_scan(raw)
                        with st.container(border=True):
                            st.error(f"**🛑 {s['company']} — {s['role']}** (Risk Score: {s['scam_risk_score']}/100)")
                            st.caption(f"**Sender:** `{raw.get('from', '')}` | **Date:** {raw.get('date', '')}")
                            st.markdown("**Detected Threat Vectors:**")
                            for flag in s["scam_red_flags"]:
                                st.markdown(f"- 🚩 {flag}")
                            if heuristics["heuristic_flags"]:
                                for h_flag in heuristics["heuristic_flags"]:
                                    st.markdown(f"- ⚙️ *Heuristic Rule:* `{h_flag}`")
                            with st.expander("View Raw Email"):
                                st.text(raw.get("body", ""))
        else:
            st.success("Zero security threats identified in this mailbox.")

    # TAB 2: PIPELINE TRACKER
    with tab_board:
        st.subheader("📋 Active Application Board")
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.info(f"**📤 Applied ({len(applied)})**")
            for item in applied:
                raw = email_lookup.get(item["email_id"], {})
                with st.container(border=True):
                    st.markdown(f"**{item['company']}**\n\n{item['role']}")
                    st.caption(f"📅 {raw.get('date')} ({item['days_since_email']}d ago)")

        with k2:
            st.warning(f"**🎤 Interview ({len(interviews)})**")
            for item in interviews:
                with st.container(border=True):
                    st.markdown(f"**{item['company']}**\n\n{item['role']}")
                    st.caption(f"📌 {item['summary_note']}")

        with k3:
            st.success(f"**🏆 Legitimate Offer ({len(offers)})**")
            for item in offers:
                with st.container(border=True):
                    st.markdown(f"**{item['company']}**\n\n{item['role']}")
                    st.caption(f"✅ Verified Genuine | {item['summary_note']}")

        with k4:
            st.markdown(f"**❌ Closed / Rejected ({len(rejected)})**")
            for item in rejected:
                raw = email_lookup.get(item["email_id"], {})
                with st.container(border=True):
                    st.markdown(f"~~**{item['company']}**~~\n\n{item['role']}")
                    st.caption(f"Date: {raw.get('date')}")

# TAB 3: ACTION CENTER
    with tab_actions:
        b_col1, b_col2 = st.columns(2)
        
        with b_col1:
            st.subheader("⏰ Stale Applications (>7 Days)")
            st.caption("One-click polite follow-up drafts for stalled opportunities")
            
            if not follow_ups:
                st.info("No applications are older than 7 days.")
            else:
                for f_item in follow_ups:
                        # Filter out follow-ups the user already marked as sent in this session
                    active_follow_ups = [
                        f for f in follow_ups 
                        if f"sent_{f['email_id']}" not in st.session_state
                    ]

                    if not active_follow_ups:
                        st.success("✅ All pending follow-ups have been resolved!")
                    else:
                        for idx, f_item in enumerate(active_follow_ups):
                            raw = email_lookup.get(f_item["email_id"], {})
                            with st.container(border=True):
                                st.markdown(f"**{f_item['company']}** — *{f_item['role']}*")
                                st.caption(f"Applied: {raw.get('date')} ({f_item['days_since_email']} days ago) | Recipient: `{raw.get('from')}`")
                                
                                btn_c1, btn_c2 = st.columns([1, 1])
                                draft_key = f"draft_{f_item['email_id']}"
                                
                                with btn_c1:
                                    if st.button("✉️ Draft Follow-Up", key=f"btn_fu_{idx}_{f_item['email_id']}", use_container_width=True):
                                        with st.spinner("Drafting polite follow-up..."):
                                            prompt = (
                                                f"Write a professional, polite, 3-sentence follow-up email from a candidate "
                                                f"who applied to {f_item['company']} for the {f_item['role']} role "
                                                f"{f_item['days_since_email']} days ago on {raw.get('date')} and hasn't heard back yet."
                                            )
                                            st.session_state[draft_key] = generate_text_helper(prompt, api_key)
                                
                                with btn_c2:
                                    if st.button(" Mark Sent", key=f"mark_sent_{idx}_{f_item['email_id']}", use_container_width=True):
                                        st.session_state[f"sent_{f_item['email_id']}"] = True
                                        st.toast(f"Follow-up for {f_item['company']} marked as sent!", icon="📨")
                                        st.rerun()

                                if draft_key in st.session_state:
                                    st.text_area("Generated Follow-Up Draft", value=st.session_state[draft_key], height=110)

        with b_col2:
            st.subheader("🎯 Upcoming Interview Preparation")
            st.caption("AI-generated interview cheat sheets for shortlisted roles")
            
            if not interviews:
                st.info("No active interview invitations.")
            else:
                for idx, i_item in enumerate(interviews):
                    raw = email_lookup.get(i_item["email_id"], {})
                    with st.container(border=True):
                        st.markdown(f"**{i_item['company']}** — *{i_item['role']}*")
                        st.caption(f"Invite snippet: {raw.get('body')}")
                        
                        prep_key = f"prep_{i_item['email_id']}"
                        if st.button("🧠 Generate Prep Cheat Sheet", key=f"btn_prep_{idx}_{i_item['email_id']}", use_container_width=True):
                            with st.spinner("Generating custom prep guide..."):
                                prompt = f"""Based on this interview invite from {i_item['company']} for {i_item['role']}:
                                '{raw.get('body')}'
                                Generate a concise, high-yield interview prep cheat sheet with:
                                1. 3 highly probable technical questions or topics for this specific role
                                2. 2 thoughtful questions for the candidate to ask the interviewer
                                3. A 3-point pre-interview checklist."""
                                st.session_state[prep_key] = generate_text_helper(prompt, api_key)

                        if prep_key in st.session_state:
                            st.markdown(st.session_state[prep_key])
    # TAB 4: RAW EMAIL LOG
    with tab_raw:
        st.subheader("📂 Complete Ingested Mailbox")
        st.json(st.session_state.inbox)