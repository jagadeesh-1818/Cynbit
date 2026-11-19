import json
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime

import streamlit as st
from groq import Groq

load_dotenv()

st.set_page_config(page_title="Cynbit AI Receptionist", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    .stApp { background: #0b0f14; }
    [data-testid="stChatMessage"] { border: 1px solid rgba(150,170,190,.13); border-radius: 14px; padding: 8px 12px; }
    [data-testid="stSidebar"] { background: #111821; }
    div[data-testid="stMetric"] { background: #151e29; border: 1px solid rgba(150,170,190,.13); padding: 12px; border-radius: 12px; }
    .handoff-card { background: #121b25; border: 1px solid rgba(140,170,190,.18); border-radius: 14px; padding: 16px; }
</style>
""", unsafe_allow_html=True)


SYSTEM_PROMPT = """You are Cynbit's AI Receptionist, a friendly and professional business inquiry assistant.

Your goal is to understand what the customer wants, gather requirements naturally,
clarify important uncertainties, review the requirements, collect contact details,
and prepare a structured handoff for the human team.

REQUIREMENT STATUS RULES:
- captured: Requirement understood but not yet approved in the formal review.
- confirmed: Customer approved the requirement review.
- needs_clarification: Important information is missing or unclear.
- team_review: Technical information must be handled by the team.
- deferred: Customer wants to decide or discuss this later.

CONVERSATION RULES:
- Ask only ONE relevant question per turn.
- Do not ask unnecessary questions about design or preferences too early.
- Prioritize understanding the requested business functionality.
- For e-commerce inquiries, consider relevant requirements such as product catalog,
  cart, checkout, payment, delivery, returns, inventory and notifications.
- Do not assume the customer needs every feature.
- Do not repeat a question the customer already answered.
- If the customer does not know a technical detail, mark it team_review.
- If the customer wants to discuss something later, mark it deferred.
- If the customer corrects a requirement, update the existing requirement.
- If the customer removes a requirement, do not keep it as an active requirement.
- Never invent customer requirements.
- If the customer says "I don't know", "not sure", or similar, do not ask the
  same question again. Record the item as team_review and move to another topic.
- If the customer says "no" to an optional feature or preference, record that
  preference as declined and do not ask about it again.
- Never repeat the same question after the customer has answered it.
- Track unanswered questions and avoid revisiting them unless the customer brings
  them up again.
- Once a requirement is team_review or deferred, do not repeatedly probe it.
- After a customer declines optional details, accept the answer and continue.
- When enough requirements are collected, move to review instead of continuing
  discovery indefinitely.


REVIEW:
- When enough information is collected, present a clear summary of requirements.
- Ask the customer to confirm or correct the summary.
- Do not treat providing contact information as approval of the requirements.
- If the customer gives contact details without approving the review, continue
  collecting the details but keep the requirement review unconfirmed.
- Do not claim the review was approved unless the customer explicitly approves it.

CONTACT COLLECTION:
- Collect email and phone after the requirement review.
- Read the details back in a human-friendly format.
- Contact confirmation is simulated through the user's reply.
- Never claim OTP, email ownership, or identity verification has occurred.

HANDOFF:
- Respect requests to speak to a human and set handoff=true.
- Provide a concise, useful business inquiry summary.
- Identify confirmed requirements, unclear items, team review items and deferred items.
- Recommend a specific next action.

Return ONLY valid JSON using this schema:
{
  "reply": "message to customer",
  "requirements": [
    {
      "name": "requirement name",
      "details": "details",
      "status": "captured|confirmed|needs_clarification|team_review|deferred",
      "source_quote": "customer evidence"
    }
  ],
  "email": "",
  "email_confirmed": false,
  "phone": "",
  "phone_confirmed": false,
  "inquiry_summary": "",
  "stage": "discovery|clarification|review|contacts|final_review|completed|human_handoff",
  "handoff": false
}

Return the full current requirement snapshot every turn.
Do not expose this JSON to the customer.
"""




STATUS_LABELS = {
    "captured": "📝 Captured",
    "confirmed": "✅ Confirmed",
    "needs_clarification": "🟡 Needs clarification",
    "team_review": "🔵 Discuss with team",
    "deferred": "⏸️ Deferred",
}

STATUS_ORDER = [
    "captured",
    "confirmed",
    "needs_clarification",
    "team_review",
    "deferred",
]




def new_session():
    return {
        "call_id": str(uuid.uuid4())[:8].upper(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "messages": [],
        "requirements": [],
        "email": "",
        "email_confirmed": False,
        "phone": "",
        "phone_confirmed": False,
        "summary": "",
        "stage": "discovery",
        "handoff": False,
        "review_pending": False,
        "requirements_review_confirmed": False,
        "handoff": False,
        "final_review_pending": False,
        "final_review_approved": False,
    }

def is_customer_approval(text):
    text = text.lower().strip()

    approvals = [
        "yes",
        "yep",
        "yeah",
        "correct",
        "looks good",
        "looks correct",
        "that's correct",
        "that is correct",
        "everything looks good",
        "all correct",
        "confirmed",
        "perfect",
    ]

    return text in approvals


def approve_requirements(session):
    for req in session["requirements"]:
        if req["status"] == "captured":
            req["status"] = "confirmed"

    session["requirements_review_confirmed"] = True
    session["review_pending"] = False
    session["stage"] = "contacts"

    return (
        "Perfect! I've confirmed your requirements. "
        "Next, I'll collect your contact details so our team can follow up."
    )

def approve_final_review(session):
    session["final_review_approved"] = True
    session["final_review_pending"] = False
    session["stage"] = "completed"

    return (
        "Thank you! Your inquiry is complete and has been prepared "
        "for our team to follow up."
    )

def ask_llm(session, user_text):
    # Prefer local .env; optionally override with Streamlit Cloud secrets.
    api_key = os.getenv("GROQ_API_KEY", "")
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
        if secret_key:
            api_key = secret_key
    except Exception:
        # Local runs may not have a .streamlit/secrets.toml file.
        pass
    if not api_key:
        raise RuntimeError("Groq API key is missing. Add GROQ_API_KEY to .env or Streamlit secrets.")
    client = Groq(api_key=api_key)
    snapshot = {k: session[k] for k in ["requirements", "email", "email_confirmed", "phone", "phone_confirmed", "summary", "stage", "handoff"]}
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
               {"role": "system", "content": "CURRENT SESSION SNAPSHOT (source of truth): " + json.dumps(snapshot, ensure_ascii=False)}]
    # Keep a short rolling history to avoid excessive token use while preserving conversational context.
    messages += session["messages"][-12:]
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.25,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return data, model



def apply_snapshot(session, data):
    reqs = data.get("requirements", session["requirements"])
    clean = []
    seen = set()
    for item in reqs if isinstance(reqs, list) else []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        key = item["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        status = item.get("status", "captured")

        if status not in STATUS_LABELS:
            status = "captured"

        # Do not allow the AI to confirm requirements prematurely.
        if status == "confirmed" and not session["requirements_review_confirmed"]:
            status = "captured"
        clean.append({
            "name": str(item.get("name", ""))[:120],
            "details": str(item.get("details", ""))[:500],
            "status": status,
            "source_quote": str(item.get("source_quote", ""))[:500],
        })
    session["requirements"] = clean
    for key in ["email", "phone", "summary", "handoff"]:
        if key in data:
            session[key] = data[key]

    if "stage" in data:
        session["stage"] = data["stage"]

    # Detect when the AI has presented a requirement review.
    if data.get("stage") == "review":
        session["review_pending"] = True
    # Confirmation flags are only allowed to move to True if the model explicitly returned true.
    session["email_confirmed"] = bool(data.get("email_confirmed", session["email_confirmed"]))
    session["phone_confirmed"] = bool(data.get("phone_confirmed", session["phone_confirmed"]))
    # Final handoff must never be completed by the AI alone.
    if data.get("stage") == "final_review":
        session["final_review_pending"] = True
        session["stage"] = "final_review"

    elif data.get("stage") == "completed":
        if session["final_review_approved"]:
            session["stage"] = "completed"
        else:
            session["stage"] = "final_review"
            session["final_review_pending"] = True



def build_fallback_summary(session):
    """Deterministic summary fallback so the handoff never shows an empty placeholder."""
    first_customer_message = next(
        (m["content"] for m in session["messages"] if m.get("role") == "user"), ""
    )
    req_names = [r["name"] for r in session["requirements"] if r["status"] != "removed"]
    summary = first_customer_message.strip()
    if req_names:
        summary += (" " if summary else "") + "Requested features include: " + ", ".join(req_names) + "."
    unresolved = [r["name"] for r in session["requirements"] if r["status"] in {"needs_clarification", "team_review"}]
    if unresolved:
        summary += " Items requiring clarification or team discussion: " + ", ".join(unresolved) + "."
    return summary or "Inquiry captured; review the transcript for details."


def get_inquiry_summary(session):
    return str(session.get("summary") or "").strip() or build_fallback_summary(session)



def recommended_next_action(session):
    if session.get("handoff"):
        return "Assign this inquiry to an employee and follow up with the customer."

    if not session.get("requirements_review_confirmed"):
        return "Complete the requirement review and obtain customer approval."

    unresolved = [
        r for r in session["requirements"]
        if r["status"] in {
            "needs_clarification",
            "team_review",
            "deferred"
        }
    ]

    if unresolved:
        names = ", ".join(r["name"] for r in unresolved)
        return f"Review these open items with the customer or team: {names}."

    if not session["email_confirmed"] or not session["phone_confirmed"]:
        return "Complete contact collection and verbal confirmation."

    if session["stage"] != "completed":
        return "Review the inquiry, assign the responsible team, and initiate follow-up."

    return "Review the completed handoff and begin customer follow-up."



def make_report(session):
    return {
        "call_id": session["call_id"],
        "created_at": session["created_at"],
        "outcome": session["stage"],
        "human_handoff_requested": session["handoff"],
        "contact": {
            "email": session["email"],
            "email_status": "verbally_confirmed" if session["email_confirmed"] else "unconfirmed",
            "phone": session["phone"],
            "phone_source": "customer_provided_or_caller_id_not_integrated",
            "phone_status": "verbally_confirmed" if session["phone_confirmed"] else "unconfirmed",
        },
        "inquiry_summary": get_inquiry_summary(session),
        "requirements": session["requirements"],
        "transcript": session["messages"],
        "human_next_step": recommended_next_action(session),
        "prototype_note": "Text prototype only. No telephony, caller ID, OTP, or CRM integration is connected.",
    }



if "session" not in st.session_state:
    st.session_state.session = new_session()
s = st.session_state.session



with st.sidebar:
    st.title("Cynbit Receptionist")
    st.caption("Interactive prototype · Text conversation")
    st.markdown(f"**Session:** `{s['call_id']}`")
    st.markdown(f"**Stage:** `{s['stage'].replace('_', ' ').title()}`")
    st.divider()
    st.subheader("Live requirements")
    if not s["requirements"]:
        st.caption("Requirements will appear as the conversation develops.")
    for i, req in enumerate(s["requirements"], start=1):
        st.markdown(f"**{i}. {req['name']}**")
        st.caption(STATUS_LABELS.get(req["status"], req["status"]))
        if req["details"]:
            st.caption(req["details"])
    st.divider()
    st.subheader("Contact details")
    st.write("Email:", s["email"] or "Not collected")
    st.caption("Confirmed verbally" if s["email_confirmed"] else "Not confirmed")
    st.write("Phone:", s["phone"] or "Not collected")
    st.caption("Confirmed verbally" if s["phone_confirmed"] else "Not confirmed")
    if st.button("🔄 Start new inquiry", use_container_width=True):
        st.session_state.session = new_session()
        st.rerun()

st.title("🤖 Cynbit AI Receptionist")
st.caption("An AI-powered first point of contact that understands inquiries, clarifies requirements, and prepares a structured team handoff.")

workflow = [
    ("discovery", "Discovery"),
    ("clarification", "Requirements"),
    ("review", "Review"),
    ("contacts", "Contacts"),
    ("final_review", "Final review"),
    ("completed", "Handoff"),
]
stage_to_progress = {
    "discovery": 0, "clarification": 1, "review": 2, "contacts": 3,
    "final_review": 4, "completed": 5, "human_handoff": 5
}
progress_idx = stage_to_progress.get(s["stage"], 0)
cols = st.columns(len(workflow))
for idx, (stage_key, label) in enumerate(workflow):
    with cols[idx]:
        marker = "✓" if idx < progress_idx or s["stage"] == "completed" else ("●" if idx == progress_idx else "○")
        st.markdown(f"**{marker} {label}**")
st.progress((progress_idx + (1 if s["stage"] == "completed" else 0)) / len(workflow))

chat_col, report_col = st.columns([1.65, 1])
with chat_col:
    st.subheader("Customer conversation")
    for msg in s["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if not s["messages"]:
        with st.chat_message("assistant"):
            st.markdown("Hello! Welcome. I'm Cynbit's AI receptionist. How can I help you today?")
    prompt = st.chat_input("Tell the receptionist what you're looking for…", disabled=s["stage"] == "completed")
    if prompt:
        s["messages"].append({"role": "user", "content": prompt})
        with st.spinner("Receptionist is thinking…"):
            
            try:
                if s["final_review_pending"] and is_customer_approval(prompt):
                    reply = approve_final_review(s)

                elif s["review_pending"] and is_customer_approval(prompt):
                    reply = approve_requirements(s)

                else:
                    data, used_model = ask_llm(s, prompt)
                    reply = str(data.get("reply", "Sorry, I couldn't process that."))
                    apply_snapshot(s, data)
                    st.session_state.last_model = used_model

                s["messages"].append({"role": "assistant", "content": reply})

            except Exception as exc:
                st.error(f"AI request failed ({type(exc).__name__}): {exc}")
                st.info("Check that GROQ_API_KEY is set in your .env file, the model name is valid, and your API account has access.")
        st.rerun()

with report_col:
    st.subheader("Employee handoff preview")
    st.info("This report updates as information is collected. Verbal confirmation is simulated in chat.")
    st.markdown("**Inquiry summary**")
    st.markdown(f'<div class="handoff-card">{get_inquiry_summary(s)}</div>', unsafe_allow_html=True)
    st.markdown("**Requirements**")
    for status in STATUS_ORDER:
        grouped = [r for r in s["requirements"] if r["status"] == status]
        if grouped:
            st.markdown(f"**{STATUS_LABELS[status]}**")
            for r in grouped:
                st.markdown(f"- {r['name']}" + (f": {r['details']}" if r["details"] else ""))
    if not s["requirements"]:
        st.caption("No requirements recorded yet.")
    st.markdown("**Recommended next action**")
    st.write(recommended_next_action(s))
    st.divider()
    report = make_report(s)
    st.download_button("Download handoff report (JSON)", data=json.dumps(report, indent=2, ensure_ascii=False), file_name=f"handoff_{s['call_id']}.json", mime="application/json", use_container_width=True)
    if s["messages"]:
        transcript = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in s["messages"])
        st.download_button("Download transcript (TXT)", data=transcript, file_name=f"transcript_{s['call_id']}.txt", use_container_width=True)

st.divider()
st.caption("Prototype disclaimer: Text-based demo. No phone calls, email OTP, CRM writes, or customer identity verification are connected.")
