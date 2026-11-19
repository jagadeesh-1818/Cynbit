# Cynbit AI Receptionist — Conversational Prototype

A text-based prototype for AI-assisted business inquiry intake. It demonstrates natural conversation, progressive requirement capture, contact read-back confirmation, and a structured handoff preview.


## Features
- Natural LLM-driven customer inquiry conversation
- Progressive requirements snapshot with statuses (`confirmed`, `needs_clarification`, `team_review`)
- Email/phone collection and verbal confirmation flags
- Live handoff preview
- Downloadable JSON report and transcript
- New inquiry reset

## Prototype boundaries
This is not a production receptionist. No live telephony, caller ID integration, email OTP, CRM writes, identity verification, or production persistence is connected. Session state currently lives in Streamlit session memory and may reset when the session ends.

## Run locally
1. Install Python 3.10+.
2. Create/activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your Groq API key.
5. Start: `streamlit run app.py`


## API configuration
The app reads `GROQ_API_KEY` and optional `GROQ_MODEL` from environment variables. Streamlit Cloud deployments should use App Settings → Secrets.


## Safety and data handling
Avoid entering real personal or confidential information in this demo. Reports are downloadable by the user and are not sent to a CRM or email system.
