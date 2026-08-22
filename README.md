# Multi-Agent Cybersecurity Lab Environment

This package upgrades the original local Streamlit teaching kit into a **multi-agent cybersecurity lab environment** built around:

- **Streamlit** for the local teaching interface
- **Ollama** for local model inference
- **CrewAI** for multi-agent orchestration
- **ChromaDB** for local vector storage, with embeddings served by Ollama (`mxbai-embed-large`)
- A lightweight **simulation engine** for scenario-driven labs

## What this package does

It lets students and instructors run a local, scenario-based cybersecurity exercise where multiple AI agents collaborate on an incident:

- SOC Analyst
- Threat Hunter
- Incident Responder
- Security Reviewer / Explainer

The app can:
1. Load a simulated cybersecurity scenario (12 scenarios spanning phishing/credential theft, insider threats, ransomware, cloud misconfiguration, BEC, supply chain, availability, mobile, OT/ICS, leaked secrets, and AI-specific incidents)
2. Present supporting artifacts (logs, emails, configs, notes)
3. Retrieve grounding context from a local knowledge base using RAG
4. Run a CrewAI workflow over the scenario, revealing each agent's findings live as they complete rather than only at the end (**Crew Run** page — fast, good for live demos)
5. Or, run a **Guided Walkthrough** — a granular (~11-15 step) breakdown of the entire pipeline (RAG embedding, similarity search, injection-flag checking, context assembly, each agent's prompt construction and LLM call, final synthesis), pausing after every step with a "what / how / why" teaching card and a real technical-detail readout, before the student advances to the next step
6. Let students ask follow-up questions at any point — grounded in the evidence, RAG-indexed content (including uploaded files), and whatever the crew/walkthrough has found so far — via a chat panel
7. Produce a final incident report and teaching notes
8. Export run artifacts for grading. Both **Crew Run** and **Guided Walkthrough** also offer two standalone documents — a *workflow doc* (every step with its technical detail and any questions asked inline) and an *SOP report* (the same run written up as a narrative procedure) — each downloadable as `.md` or `.html`
9. Log every stage/step completion and every student question/answer to `logs/interactions.jsonl`, viewable in the Instructor Dashboard, so instructors can see what students ask about most — a proxy for where the material is weak

## Core design choices

This project is intentionally **local-first**. It is designed for instructional use and prototype experimentation, not for production SOC operations.

- If `crewai` is available, the app will use a real CrewAI-based orchestration path, running entirely against your local Ollama server (never OpenAI). If CrewAI is not installed or fails mid-run, the app falls back to a built-in sequential orchestrator so the classroom experience still works. CrewAI availability is resolved at import time and reported in the sidebar at startup, so launching from an environment without it is visible *before* a run begins; a warning banner also appears if a run falls back mid-flight. **Guided Walkthrough never uses CrewAI** — it calls Ollama directly — so that page behaves identically either way.
- Ollama must be installed and running locally. The model picker lists local models first; Ollama Cloud (`:cloud`) models are also shown if your account has access to them, but are not required.
- CrewAI's telemetry is disabled by default (`CREWAI_TRACING_ENABLED=false` in `.env`, not committed) — no run data leaves the machine.
- Uploaded RAG documents are scanned for language resembling a prompt-injection attempt and flagged in the UI and in retrieved context; this is a teaching signal, not a security guarantee.

## Recommended setup

1. Install Ollama
2. Pull at least one local chat model, for example:
   - `ollama pull llama3.1:8b`
   - `ollama pull qwen2.5:7b`
3. Pull the embedding model used for RAG: `ollama pull mxbai-embed-large` (required — RAG indexing/retrieval calls this directly via Ollama's `/api/embed`, no separate ML library or model download involved)
4. Clone this repository:
   ```bash
   git clone git@github.com:dabulseco/multi-agent_cyber_lab.git
   cd multi-agent_cyber_lab
   ```
5. Create a **Python 3.11** environment and install dependencies:
   ```bash
   conda create -n cyber python=3.11
   conda activate cyber
   pip install -r requirements.txt
   ```
   Python 3.11 is what this has been tested against. Newer interpreters may install
   without `crewai` resolving, in which case Crew Run drops to the sequential
   fallback — check the sidebar, which reports CrewAI availability at startup.
6. Run the app:
   ```bash
   streamlit run app/main.py
   ```

## Suggested teaching workflow

1. Instructor selects a scenario
2. Students review evidence and scenario injects
3. Students build or update the RAG index
4. Students run the multi-agent crew
5. Students critique:
   - what the agents concluded
   - what they missed
   - what evidence was weak
   - where hallucinations or overclaiming appeared
6. Students export and submit the incident report

## Project layout

- `app/main.py` — Streamlit interface
- `app/core/crew_orchestrator.py` — CrewAI + fallback orchestration, live stage callbacks, Q&A
- `app/core/guided_workflow.py` — step plan, per-step execution, workflow-doc and SOP-report rendering
- `app/core/rag.py` — local retrieval pipeline, upload sanitization, injection flagging
- `app/core/simulation.py` — scenario and artifact loading
- `app/core/ollama_client.py` — Ollama HTTP client (generate, chat, embed, healthcheck)
- `app/core/reporting.py` — run-bundle export and markdown-to-HTML rendering
- `app/core/interaction_log.py` — append-only local log of stage completions and student Q&A (`logs/interactions.jsonl`, gitignored)
- `data/incidents/` — 12 scenario definitions
- `data/logs/`, `data/phishing/`, `data/configs/`, `data/evidence/` — supporting datasets
- `kb/` — knowledge-base documents for local RAG
- `labs/` — lab handouts aligned to the simulation environment
- `.streamlit/config.toml` — disables Streamlit's file watcher (avoids reload churn during long runs)

## Setup notes

- Tested against a conda env with `requirements.txt` installed (Python 3.11); see the setup steps above.
- `.env` (not committed) should contain `CREWAI_TRACING_ENABLED=false`; `OLLAMA_URL`/`OLLAMA_TIMEOUT_S` are also read from environment if you need to point at a non-default Ollama host.

## Notes on current libraries

The app tracks the current recommended patterns for each dependency:

- **CrewAI** — built on its core `Agent` / `Task` / `Crew` abstractions. Each agent runs as its own single-task crew so a result can be revealed the moment that agent finishes, rather than only after the whole crew completes.
- **Streamlit** — multipage navigation via `st.navigation` and `st.Page`, with `st.session_state` carrying run state across pages.
- **Chroma** — local persistence via `PersistentClient(path=...)`.
- **Ollama** — all inference and embedding over the local HTTP API; `chat()` supports structured output via the `format` schema parameter.

## Important limitation

This is a teaching and experimentation platform. It does not:
- isolate malware
- connect to production SIEMs
- guarantee safe handling of live malicious content
- replace formal security tooling or review
