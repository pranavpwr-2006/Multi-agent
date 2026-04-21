#  Sora Assistant — Multi-Agent Productivity Assistant

> Built for the **Google Gen AI Arcade Edition Hackathon**

Hey! This is my submission for the hackathon. I built a multi-agent AI system using Google ADK and Gemini 2.5 Flash that helps you manage your tasks, schedule events, and save notes — all through natural language.

---

# What does it do?

Just type what you need in plain English and Sora figures out what to do:

- *"Create a task to finish my assignment by Friday"*
- *"Schedule a meeting tomorrow at 3pm"*
- *"Save a note about the project requirements"*
- *"List all my pending tasks"*
- *"Delete the meeting on 25-04-26"*

---

# How it works

The system has a **primary agent** (root agent) that acts like a manager. It reads your request and routes it to the right sub-agent:

```
Sora Assistant (Root Agent)
 ├── Task Agent       → create, list, update, delete to-dos
 ├── Calendar Agent   → create, list, update, delete events
 └── Notes Agent      → create, search, update, delete notes
          ↓
 Google Cloud Datastore
          ↓
 Google Cloud Run (Deployed API)
```

Each sub-agent has its own set of tools (create, list, update, delete) and only gets called when needed.

---

## 🛠️ Tech Stack

| What | How |
|------|-----|
| Agent Framework | Google ADK (Agent Development Kit) |
| LLM | Gemini 2.5 Flash via Vertex AI |
| Database | Google Cloud Datastore |
| Deployment | Google Cloud Run |
| Language | Python 3.12 |

---

# Project Structure

```
sora-assistant/
├── sora_assistant/
│   ├── agent.py        # All agents and tools
│   └── __init__.py
├── main.py             # FastAPI entry point for Cloud Run
├── Dockerfile          # Container config
├── .env                # Environment variables (not pushed)
└── requirements.txt    # Dependencies
```

---

#  Setup :

### Prerequisites
- Google Cloud account with a project
- Vertex AI API enabled
- Python 3.12

### Steps

**1. Clone the repo**
```bash
git clone <your-repo-url>
cd sora-assistant
```

**2. Create virtual environment**
```bash
uv venv --python 3.12
source .venv/bin/activate
```

**3. Install dependencies**
```bash
uv pip install -r requirements.txt
```

**4. Create your `.env` file**
```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL=gemini-2.5-flash
```

**5. Run locally**
```bash
adk web --allow_origins 'regex:https://.*\.cloudshell\.dev'
```

---

#  Deployment

```bash
gcloud run deploy sora-assistant \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

#  What I learned

- How to build multi-agent systems using Google ADK
- How to connect agents to tools and route between them
- How to deploy a containerized AI app to Cloud Run
- How to use Google Cloud Datastore for persistent storage
- Debugging agent behavior and fixing sequential vs intelligent routing

---

#  Demo url :

Try it live: `https://sora-assistant-737849989841.us-central1.run.app`

---

#  Built by :-

Pranav — student , rookie coder '😊
