# Cynbit AI Receptionist — Conversational Prototype

An LLM-powered conversational prototype for intelligent business inquiry intake, requirement gathering, and structured employee handoff.

## Overview

Traditional inquiry forms often require customers to know exactly what information to provide. This prototype explores a conversational approach where an AI receptionist understands customer requests, progressively collects requirements, clarifies uncertainties, confirms information, and prepares a structured handoff for the business team.

## Features

- Natural-language customer interaction using an LLM
- Progressive requirement extraction and tracking
- Requirement clarification and review
- Customer corrections and confirmation
- Email and phone collection with conversational read-back confirmation
- Live inquiry and requirement status tracking
- Structured employee handoff preview
- Downloadable inquiry report (JSON) and conversation transcript
- Reset functionality for starting a new inquiry

## Tech Stack

- **Language:** Python
- **Frontend:** Streamlit
- **LLM API:** Groq
- **Model:** Configurable through `GROQ_MODEL`
- **State Management:** Streamlit session state
- **Data Format:** JSON
- **Version Control:** Git & GitHub

## Workflow

1. Customer initiates an inquiry.
2. AI understands the business objective.
3. Requirements are progressively collected through conversation.
4. Unclear requirements are clarified or flagged for team review.
5. Customer reviews and confirms the collected requirements.
6. Contact details are collected and verbally confirmed.
7. A structured inquiry report is generated for employee follow-up.

## Prototype Limitations

This is a proof of concept, not a production-ready receptionist.

- No live telephony or voice integration
- No caller ID integration
- No email OTP verification
- No CRM integration or writes
- No customer identity verification
- No production database or persistent storage
- Session data may be lost when the Streamlit session ends

## Setup and Installation

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd cynbit_ai_receptionist
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows:**
```powershell
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```


### 4. Run the application

```bash
streamlit run app.py
```

The app will open in your browser, typically at:

`http://localhost:8501`

## Deployment Configuration

For Streamlit Community Cloud, configure API credentials under the application's **Secrets** settings rather than committing credentials to the repository.

## Security & Data Handling

- API credentials are managed through environment variables or deployment secrets.
- Avoid entering sensitive, confidential, or real customer information into this prototype.
- Inquiry reports are generated for user download and are not automatically transmitted to CRM or email services.
- Customer contact confirmation is conversational only and does not verify identity or ownership.

## Project Status

**Status:** Functional Proof of Concept

This project demonstrates conversational AI for business inquiry intake, structured requirement collection, and employee handoff.

Future improvements may include persistent storage, automated evaluation, CRM integration, secure contact verification, and production deployment infrastructure.
