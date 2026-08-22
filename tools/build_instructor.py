"""Regenerate instructor_manual.docx at v2.0.

Scenario reference sections are generated from data/incidents/*.json so they cannot
drift from the shipped scenarios again.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render import (EXT, open_template, title_block, h1, h2, h3, body, bullets,
                     numbered, table, callout, terminal, spacer)

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = [json.loads(p.read_text()) for p in sorted((ROOT / "data/incidents").glob("*.json"))]
BY_ID = {s["id"]: s for s in SCENARIOS}

FOCUS = {
    "credential_theft_vpn": "Phishing / account compromise",
    "insider_exfiltration": "Insider threat",
    "insider_sabotage": "Insider threat / offboarding",
    "ransomware_deployment_extortion": "Ransomware",
    "cloud_storage_misconfiguration": "Cloud misconfiguration",
    "leaked_api_key_repo": "Secrets management",
    "bec_invoice_fraud": "Social engineering / fraud",
    "supply_chain_compromise": "Software supply chain",
    "availability_incident_ddos": "Availability",
    "mobile_byod_compromise": "Mobile / BYOD",
    "ot_ics_exposure": "OT / ICS",
    "ai_assistant_prompt_injection_leak": "AI-specific risk",
}

# Display order: the two original scenarios first (they have the most instructor
# support), then the rest grouped roughly by theme.
ORDER = [
    "insider_exfiltration", "credential_theft_vpn", "insider_sabotage",
    "ransomware_deployment_extortion", "cloud_storage_misconfiguration",
    "leaked_api_key_repo", "bec_invoice_fraud", "supply_chain_compromise",
    "availability_incident_ddos", "mobile_byod_compromise", "ot_ics_exposure",
    "ai_assistant_prompt_injection_leak",
]

NOTES = {
    "insider_exfiltration":
        "This scenario is designed to resist simple conclusions. The log shows escalating transfer sizes from one "
        "host, but also one much smaller transfer from a second host to a different IP. Students should notice that "
        "the evidence is consistent with both insider exfiltration and compromised service account misuse. The "
        "agents will often overclaim motive — use this as your primary critique target.",
    "credential_theft_vpn":
        "This is the most evidence-rich scenario and is well suited to advanced students or second runs. The "
        "phishing email is clearly suspicious but does not confirm credential capture. Students should flag that "
        "the VPN login from a foreign IP is consistent with compromise but could theoretically be a legitimate "
        "remote login. The agents often overstate certainty about data exfiltration without evidence of what files "
        "were actually accessed.",
    "insider_sabotage":
        "The critique target here is intent. Deleted backup jobs during an unrevoked-access window look damning, "
        "but the same evidence is consistent with an honest configuration mistake by someone whose account was "
        "still active. Watch for agents that treat the process failure (late revocation) and the alleged act "
        "(sabotage) as the same finding — they are separate, and only one is clearly established.",
    "ransomware_deployment_extortion":
        "Students should build a sequence — initial access, lateral movement, encryption — and mark which links in "
        "that chain the evidence actually supports. Agents frequently assert double extortion (data stolen as well "
        "as encrypted) on the strength of the ransom note alone; the note is the attacker's claim, not evidence of "
        "exfiltration. That distinction is the strongest single teaching moment in this scenario.",
    "cloud_storage_misconfiguration":
        "A good scenario for teaching proportionate response. Anonymous requests during a public-access window "
        "prove possible exposure, not confirmed exfiltration, and the audit log genuinely cannot settle the "
        "question. Reward students who say the evidence is inconclusive and specify what would resolve it, rather "
        "than those who pick a side confidently.",
    "leaked_api_key_repo":
        "Blast radius is the analytical core here: what could this key actually reach? Agents tend to jump to "
        "cleanup steps (rewrite git history, delete the commit) ahead of the action that actually stops the "
        "bleeding, which is rotation. Ask students to order the response actions and defend the ordering.",
    "bec_invoice_fraud":
        "The technical indicator (a lookalike sender domain) is easy to spot; the harder question is the process "
        "failure that let a payment change proceed on the strength of an email. Students who only critique the "
        "email headers have done half the analysis. Agents often recommend email controls and never mention "
        "out-of-band verification of bank detail changes.",
    "supply_chain_compromise":
        "This scenario turns on a distinction students routinely collapse: a compromised package being present in "
        "the build is exposure; evidence of it executing against this environment is compromise. They require "
        "different evidence and different responses. Expect agents to slide from one to the other mid-paragraph — "
        "have students find the exact sentence where it happens.",
    "availability_incident_ddos":
        "The most useful scenario for practising 'the evidence does not decide this'. The traffic pattern is "
        "compatible with both an attack and a legitimate surge, and the on-call decision has to be made anyway. "
        "Grade on whether students separate the operational decision from the causal claim, rather than on which "
        "cause they pick.",
    "mobile_byod_compromise":
        "Evidence quality is deliberately weaker here than on a managed endpoint, and MDM telemetry on a personal "
        "device has real limits. Strong students will note both the investigative constraint and the privacy and "
        "legal boundaries that apply to a personal phone. Agents rarely raise the privacy dimension unprompted — a "
        "good gap to point out during debrief.",
    "ot_ics_exposure":
        "Safety-versus-security tradeoffs make OT different from IT, and the standard containment reflex — cut the "
        "connection — may not be available on a live plant network. Watch for agents recommending IT-style "
        "remediation with no acknowledgement of process safety. Unexplained access is also not the same as a "
        "confirmed unauthorized control action.",
    "ai_assistant_prompt_injection_leak":
        "This scenario asks students to review another AI system's design failure, which pairs directly with the "
        "prompt-injection material in kb/03 and kb/05. The instructive irony is that the reviewing agents are "
        "themselves susceptible to the same class of flaw — a point worth making explicitly during debrief, and "
        "one you can demonstrate live using the injection flagging on the RAG Control page.",
}

doc = open_template(str(ROOT / "instructor_manual.docx"))

title_block(
    doc,
    "Instructor Manual",
    "Multi-Agent Cybersecurity Lab",
    "AI + Cybersecurity — Course Facilitator Reference",
    "Multi-Agent Cybersecurity Lab Environment",
    "Version 2.0 — August 2026",
)

# ---------------------------------------------------------------- 1. Overview
h1(doc, "1. Overview")
body(doc, "This document covers everything you need to deploy, run, and extend the Multi-Agent Cybersecurity Lab in a "
          "course setting. The lab is designed for courses at the intersection of AI and cybersecurity, where a "
          "central learning objective is teaching students to critically evaluate AI-generated analysis rather than "
          "accept it uncritically.")
body(doc, "The system is intentionally local-first: all inference, retrieval, and storage runs on the instructor or "
          "student machine. No internet connection is required after initial setup. No student data leaves the local "
          "environment.")
callout(doc, "🎯  Pedagogical purpose:",
        "The AI agents in this system are calibrated to be useful but imperfect. They will overclaim, hallucinate, "
        "and occasionally draw unjustified conclusions. This is by design. The lab succeeds when students catch "
        "these errors — not when the agents are correct.")

h2(doc, "1.1 System Architecture")
body(doc, "The platform consists of seven integrated components:")
table(doc, ["Component", "Role"], [
    ["Streamlit (app/main.py)", "Local web interface. Six pages: Home, Scenario Lab, Crew Run, Guided Walkthrough, "
                                "RAG Control, Instructor Dashboard."],
    ["Ollama", "Local LLM inference engine. Serves both the chat models and the embedding model. Runs on CPU or "
               "GPU. No cloud API required."],
    ["CrewAI", "Multi-agent orchestration for the Crew Run page. Optional — the app falls back to a built-in "
               "sequential orchestrator if it is unavailable."],
    ["ChromaDB", "Local vector database for RAG retrieval, persisted to .chromadb/ in the project root. Embeddings "
                 "are produced by Ollama, not by a separate ML library."],
    ["Simulation engine (core/simulation.py)", "Loads scenario definitions, artifact paths, and preview rendering."],
    ["Guided workflow engine (core/guided_workflow.py)", "Breaks a run into 11–17 inspectable steps, and renders "
                                                          "the workflow document and SOP report."],
    ["Evidence metrics (core/evidence_metrics.py)", "A fixed registry of pandas analyzers that compute timing "
                                                     "regularity, off-hours share, outcome rates, volume "
                                                     "escalation and entity cardinality over the CSV evidence."],
    ["Interaction log (core/interaction_log.py)", "Append-only local record of every step completion and student "
                                                   "question, written to logs/interactions.jsonl."],
])

h2(doc, "1.2 The Four Agents")
table(doc, ["Agent", "System prompt focus"], [
    ["SOC Analyst", "Evidence triage, timeline reconstruction, separating observed facts from inference."],
    ["Threat Hunter", "Attacker behavior, plausible techniques, lateral movement, detection gaps, alternative "
                      "hypotheses."],
    ["Incident Responder", "Containment, eradication, recovery, operational prioritization."],
    ["Security Reviewer", "Uncertainty, overclaiming, teaching clarity, whether conclusions are justified by "
                          "evidence."],
])
body(doc, "A final synthesis pass runs after the four agents, using a separate system prompt instructed to produce: "
          "Confirmed Facts, Likely Inferences, Remaining Unknowns, Recommended Immediate Actions, Recommended "
          "Longer-Term Controls, and Notes for Students.")

h2(doc, "1.3 Two Ways to Run a Scenario")
body(doc, "The same underlying pipeline is exposed through two pages with different classroom purposes. Both run "
          "the same agents over the same evidence and produce the same kind of final report.")
table(doc, ["", "Crew Run", "Guided Walkthrough"], [
    ["Pace", "Continuous. Each agent's findings appear the moment that agent finishes.",
     "Paused after every step. The student clicks to advance."],
    ["Granularity", "Five stages: four agents plus synthesis.",
     "11–17 steps, including deterministic metric computation over the log evidence, RAG embedding, similarity "
     "search, injection scanning, context assembly, and every "
     "prompt construction."],
    ["Teaching material", "Technical detail per stage in an expander.",
     "A what / how / why card plus a real technical readout for every step."],
    ["Orchestration", "CrewAI when available, sequential fallback otherwise.",
     "Always calls Ollama directly. CrewAI is not involved."],
    ["Best for", "Live demonstration, second and third runs, assessment.",
     "First exposure, explaining how RAG and agent prompting actually work."],
])

# ------------------------------------------------------- 2. Environment Setup
h1(doc, "2. Environment Setup")
h2(doc, "2.1 Prerequisites")
bullets(doc, [
    "macOS, Linux, or Windows 10/11 with WSL2",
    "Python 3.11 — this is the tested version, and requirements.txt pins the dependency versions it was tested with",
    "Ollama installed: https://ollama.ai",
    "At least 8 GB RAM; 16 GB recommended for 7–8B models",
    "~4 GB disk space for model weights (varies by model), plus ~700 MB for the embedding model",
])

h2(doc, "2.2 Installation Steps")
body(doc, "Install Ollama, then pull one chat model and the embedding model:")
terminal(doc, "ollama pull llama3.1:8b        # or: ollama pull qwen2.5:7b\nollama pull mxbai-embed-large  # required for RAG")
body(doc, "Clone the repository:")
terminal(doc, "git clone git@github.com:dabulseco/multi-agent_cyber_lab.git\ncd multi-agent_cyber_lab")
body(doc, "Create and activate a Python 3.11 environment:")
terminal(doc, "conda create -n cyber python=3.11\nconda activate cyber")
body(doc, "Install Python dependencies:")
terminal(doc, "pip install -r requirements.txt")
body(doc, "Start the app:")
terminal(doc, "streamlit run app/main.py")
body(doc, "On first run, go to RAG Control and click Build / refresh index to populate the knowledge base.")
callout(doc, "⚠️  Environment warning:",
        "The embedding model must be pulled before indexing will work — RAG calls Ollama directly for embeddings, "
        "so a missing mxbai-embed-large produces an indexing error rather than a silent fallback. Likewise, "
        "installing into a Python version other than 3.11 may leave crewai unresolved, in which case Crew Run uses "
        "the sequential path. The sidebar reports both conditions.")

h2(doc, "2.3 Installed Dependencies")
body(doc, "requirements.txt pins exact versions of the direct dependencies to the tested environment. Transitive "
          "dependencies are left to resolve normally so the install stays portable across platforms.")
table(doc, ["Package", "Purpose"], [
    ["streamlit==1.57.0", "Web interface and multi-page navigation"],
    ["pandas==3.0.2", "CSV artifact parsing and tabular display"],
    ["tabulate==0.10.0", "Markdown table rendering for CSV previews"],
    ["requests==2.33.1", "HTTP calls to the Ollama API"],
    ["chromadb==1.5.8", "Local vector database for RAG"],
    ["pypdf==6.10.2", "PDF extraction for RAG indexing"],
    ["python-docx==1.2.0", "Word document extraction for RAG indexing"],
    ["crewai==0.193.2", "Multi-agent orchestration for the Crew Run page"],
    ["python-dotenv==1.2.2", "Reads .env for CrewAI telemetry and Ollama host settings"],
    ["markdown==3.10.3", "Renders the HTML versions of the workflow and SOP documents"],
])
body(doc, "Embeddings require no Python package: they are served by Ollama over its local HTTP API.")

h2(doc, "2.4 Verifying the Environment Before Class")
body(doc, "The sidebar reports the two conditions that most often break a session. Check both before students "
          "arrive:")
bullets(doc, [
    "Ollama reachable — must read Yes. If No, Ollama is not running.",
    "CrewAI available — reads Yes with a version number when the environment is correct. If it reads No, the "
    "sidebar names the import error and the interpreter path in use, and Crew Run will use the sequential "
    "fallback for the whole session.",
])
body(doc, "Guided Walkthrough never uses CrewAI, so that page is unaffected by a CrewAI problem and remains a "
          "reliable teaching path even in a broken environment.")

# --------------------------------------------- 3. Running a Classroom Session
h1(doc, "3. Running a Classroom Session")
h2(doc, "3.1 Recommended Classroom Flow")
table(doc, ["Phase", "Activity"], [
    ["Pre-class (instructor)", "Verify Ollama is running, a model is loaded, and the sidebar reports CrewAI "
                               "available. Build the RAG index. Run your chosen scenario once to confirm outputs "
                               "are coherent with the selected model."],
    ["Opening (10–15 min)", "Introduce the scenario on the Home page. Review the initial situation and learning "
                            "goals. Ask students to form initial hypotheses before seeing agent output."],
    ["Artifact review (10–15 min)", "Walk through Scenario Lab. Read each artifact together. Highlight what is and "
                                    "is not in the evidence."],
    ["RAG setup (5 min)", "Have students open RAG Control and build the index. Briefly explain what RAG does and "
                          "why it matters."],
    ["Pipeline teaching (20–40 min, optional)", "Run the Guided Walkthrough on the projector, pausing at the RAG "
                                                 "steps and one agent prompt. This is where students see what the "
                                                 "agents actually receive."],
    ["Crew run (10–20 min)", "Students set their objective and student notes, then run the crew. Agents may take "
                             "several minutes on CPU-only hardware."],
    ["Analysis (20–30 min)", "Students read agent outputs and the final synthesis. Identify at least one claim per "
                             "agent that is unsupported. Compare to their pre-run hypothesis."],
    ["Debrief (15–20 min)", "Use the Instructor Dashboard grading prompts to drive discussion. Which agent "
                            "overclaimed? Which evidence was weakest? Review the questions students asked."],
    ["Export and submit", "Students export the run bundle and begin their written critique."],
])

h2(doc, "3.2 Model Selection Guidance")
body(doc, "The quality and coherence of agent outputs depends heavily on the model selected. Recommendations:")
table(doc, ["Model", "Notes"], [
    ["llama3.1:8b", "Good balance of quality and speed on consumer hardware. Recommended default."],
    ["qwen2.5:7b", "Strong instruction following, slightly faster than llama3.1 on some hardware."],
    ["mistral:7b", "Reasonable quality, widely available, good fallback."],
    ["llama3.1:70b (quantized)", "Higher quality outputs but requires 32+ GB RAM or GPU. Not suitable for most "
                                 "student machines."],
])
callout(doc, "⚠️  Note:",
        "Smaller models (3–4B) may produce incoherent or very short agent outputs. Test your chosen model on the "
        "scenario you plan to teach before class and confirm the synthesis report is readable. The model picker "
        "also lists any Ollama Cloud (:cloud) models your account can reach; these are not required, and a run "
        "against one will fail with a subscription error if your plan does not cover it.")

h2(doc, "3.3 Choosing Between Crew Run and Guided Walkthrough")
body(doc, "For a first encounter with the material, run the Guided Walkthrough. Students who have only seen Crew "
          "Run tend to treat the pipeline as a black box that emits opinions; the walkthrough shows them the "
          "embedding call, the retrieved chunks, the injection scan, and the exact prompt each agent receives.")
body(doc, "For assessment and for second or third scenarios, use Crew Run. It is faster, it produces the export "
          "bundle used for grading, and by that point the mechanics are no longer the lesson.")

# ------------------------------------------------------ 4. Scenario Reference
h1(doc, "4. Scenario Reference")
body(doc, f"The lab ships with {len(SCENARIOS)} scenarios. All appear automatically in the scenario dropdowns; none "
          "requires configuration. Each has three timed injects that simulate new information arriving during the "
          "incident.")
table(doc, ["Scenario", "Focus area", "Artifacts"],
      [[BY_ID[sid]["title"], FOCUS[sid], str(len(BY_ID[sid]["artifacts"]))] for sid in ORDER])

for n, sid in enumerate(ORDER, start=1):
    s = BY_ID[sid]
    h2(doc, f"4.{n} {s['title']}")
    body(doc, f"File: data/incidents/{sid}.json")
    body(doc, f"Summary: {s['summary']}")
    body(doc, "Learning goals:")
    bullets(doc, s["learning_goals"])
    body(doc, "Artifacts linked to this scenario:")
    bullets(doc, s["artifacts"])
    body(doc, "Simulation injects:")
    bullets(doc, [f"{i['time']} — {i['message']}" for i in s["injects"]])
    callout(doc, "Instructor note:", NOTES[sid])

# -------------------------------------------------------- 5. Extending the Lab
h1(doc, "5. Extending the Lab")
h2(doc, "5.1 Adding a New Scenario")
body(doc, "Scenarios are JSON files in data/incidents/. Create a new file following this structure:")
callout(doc, "Schema:",
        '{\n  "id": "unique_scenario_id",\n  "title": "Scenario Display Title",\n'
        '  "summary": "One-paragraph summary for the Home page.",\n'
        '  "learning_goals": ["Goal 1", "Goal 2"],\n'
        '  "initial_situation": "What the responder knows at time 0.",\n'
        '  "injects": [\n    { "time": "HH:MM", "message": "New information arriving at this time." }\n  ],\n'
        '  "artifacts": [\n    "data/logs/your_log.csv",\n    "data/configs/your_config.txt"\n  ],\n'
        '  "default_objective": "The default crew mission for this scenario."\n}')
body(doc, "The new scenario appears automatically in the scenario dropdowns on the Home, Scenario Lab, Crew Run, "
          "and Guided Walkthrough pages. No code changes are required.")

h2(doc, "5.2 Adding Artifacts")
body(doc, "Place artifact files in the appropriate subdirectory:")
bullets(doc, [
    "data/logs/ — CSV log files (auth logs, network logs, web access logs, cloud audit logs)",
    "data/phishing/ — email text files",
    "data/configs/ — configuration notes, access reviews, policy documents",
    "data/evidence/ — mixed supporting evidence: incident notes, transcripts, commit diffs, advisories, ransom "
    "notes, billing exports",
])
body(doc, "Supported artifact types for preview: .md, .txt, .log, .conf, .json (rendered as a code block), .csv "
          "(rendered as a markdown table, first 20 rows).")

h2(doc, "5.3 Adding Knowledge Base Content")
body(doc, "Knowledge base files live in kb/. Drop any supported file type into that directory:")
bullets(doc, [
    ".md, .txt, .py, .csv, .json, .yaml, .yml, .log — read as plain text",
    ".pdf — extracted page by page via pypdf",
    ".docx — extracted paragraph by paragraph via python-docx",
])
body(doc, "After adding files, go to RAG Control > Build / refresh index. New content is chunked into "
          "900-character segments with 150-character overlap and embedded with mxbai-embed-large through the local "
          "Ollama server.")
callout(doc, "Tip:",
        "Add your course slides, reading summaries, or reference documents to kb/ before class. The agents will "
        "draw on them during retrieval, grounding their analysis in material students have studied.")

h2(doc, "5.4 Adding Lab Handout Files")
body(doc, "Lab markdown files in labs/ are included in the RAG index when Build / refresh index is run with the "
          "Include built-in KB and labs checkbox enabled. Place new lab handouts (as .md files) in labs/ to make "
          "them retrievable.")

# -------------------------------------------------- 6. Assessment and Grading
h1(doc, "6. Assessment and Grading")
h2(doc, "6.1 Required Deliverables")
table(doc, ["Deliverable", "Description"], [
    ["Exported run bundle", "JSON file from Crew Run > Export current run. Confirms the student ran the lab and "
                            "records the full agent output. File: exports/<scenario_id>_<timestamp>.json."],
    ["One-page critique", "Written analysis of agent output quality. Must answer four structured questions (see "
                          "below)."],
    ["Corrected human summary", "Student-authored revision of the final synthesis that removes unsupported claims, "
                                "adds uncertainty language, and proposes additional verification steps."],
])
body(doc, "If you teach with the Guided Walkthrough, the workflow document is a useful optional fifth deliverable: "
          "it captures every step the student advanced through along with every question they asked, which makes "
          "engagement visible in a way the JSON bundle does not.")

h2(doc, "6.2 Critique Rubric")
body(doc, "The four required critique questions and what strong answers look like:")
table(doc, ["Question", "Strong answer criteria"], [
    ["Which findings were strongly evidence-supported?", "Cites a specific log row or artifact line. Names the "
                                                          "agent. Explains why the evidence directly supports the "
                                                          "claim."],
    ["Which findings were weakly supported or inferred?", "Names at least two inferences presented as facts. "
                                                           "Explains what evidence would be needed to confirm "
                                                           "them."],
    ["Which agent was most cautious?", "Goes beyond “the Security Reviewer.” Compares hedging language across "
                                       "agents with examples. May identify a surprising second choice."],
    ["Did any agent contradict a measured metric?", "Names a specific claim and the metric it conflicts with. "
                                                    "Notes whether the final synthesis caught the contradiction "
                                                    "or repeated it."],
    ["What would you verify next?", "Proposes concrete investigative steps. Specifies what system, log, or "
                                    "artifact to query. Does not propose generic steps like “check more logs.”"],
])

h2(doc, "6.3 Suggested Grading Weights")
table(doc, ["Component", "Weight"], [
    ["Run bundle submitted and valid", "10%"],
    ["Critique question 1 (evidence support)", "20%"],
    ["Critique question 2 (weak inferences)", "20%"],
    ["Critique question 3 (agent caution)", "15%"],
    ["Critique question 4 (next verification)", "15%"],
    ["Corrected human summary", "20%"],
])

h2(doc, "6.4 Common Student Errors to Watch For")
bullets(doc, [
    "Submitting the AI synthesis as their own corrected summary (verbatim or near-verbatim)",
    "Critique answers that do not cite any specific artifact or log data",
    "Accepting the agents’ motive claims (insider, attacker) without noting these are unconfirmed",
    "Failing to notice when the Security Reviewer itself overclaims",
    "Conflating “the crew concluded X” with “X is true” in their own writing",
    "Treating an answer from the in-app chat panel as verified fact — it is another model output, grounded in the "
    "evidence but not authoritative",
])

# ---------------------------------------------------- 7. Instructor Dashboard
h1(doc, "7. Instructor Dashboard")
body(doc, "The Instructor Dashboard page is available to both instructors and students. It serves three functions.")
body(doc, "First, it displays suggested grading prompts and a reflection structure that mirrors the deliverable "
          "requirements. You can use this in class to prime discussion before students read the synthesis.")
body(doc, "Second, it shows the runs completed in the current browser session. Each is expandable and shows the "
          "execution mode and full final synthesis. This is useful for live demonstration: run the same scenario "
          "twice with different objectives or student notes and compare the outputs. This list is session state "
          "only and resets when the app restarts.")
body(doc, "Third, and independently of session state, it renders the interaction log — a persistent record across "
          "all sessions and all students who have used this installation.")
table(doc, ["Panel", "What it shows"], [
    ["Summary metrics", "Runs and walkthroughs started, crew stage completions, guided steps completed, and total "
                        "questions asked."],
    ["Student questions", "Every question asked in Crew Run or Guided Walkthrough, with the scenario, the step it "
                          "was asked at, an answer preview, and a truncated session id."],
])
callout(doc, "Classroom use:",
        "The question log is the most direct feedback signal in the system. Questions cluster where the material is "
        "weak — if six students ask what RAG poisoning is at the same walkthrough step, that concept needs more "
        "time in lecture, not more time in the lab. Review it after each session.")
body(doc, "The log is written to logs/interactions.jsonl, one JSON object per line, appended as events occur. It is "
          "gitignored and never leaves the machine. Delete the file to reset the dashboard.")

# ------------------------------------------------------ 8. Technical Reference
h1(doc, "8. Technical Reference")
h2(doc, "8.1 Execution Modes")
body(doc, "The Crew Run page has two execution paths. Guided Walkthrough always uses direct Ollama calls and is not "
          "affected by either.")
h3(doc, "CrewAI (preferred)")
body(doc, "When crewai imports successfully, each of the four agents runs as its own single-task Crew, executed one "
          "at a time, with an explicitly configured Ollama LLM (CrewAI would otherwise default to an OpenAI-backed "
          "model through LiteLLM and fail, since this app never configures an OpenAI key). Agents are created with "
          "allow_delegation=False to prevent recursive delegation.")
body(doc, "Running one crew per agent rather than a single four-task crew is deliberate: it returns a real result "
          "the instant each agent finishes, which is what makes the live stage-by-stage reveal possible. The tasks "
          "never shared CrewAI-managed context between roles, so nothing is lost by separating them. All three "
          "execution paths — CrewAI, sequential, and Guided Walkthrough — build their prompts with the same "
          "function, so they ask the model the same thing.")
h3(doc, "Sequential fallback")
body(doc, "If crewai is missing or raises during a run, the system falls back to a built-in loop that calls the "
          "Ollama generate endpoint once per agent. Output quality is similar; the difference is that the CrewAI "
          "orchestration layer is not involved. Availability is resolved when the app starts and shown in the "
          "sidebar, and the execution mode recorded in the run summary and the export bundle tells you which path "
          "actually ran, including the exception type if a fallback occurred.")

h2(doc, "8.2 RAG Pipeline")
table(doc, ["Setting", "Value"], [
    ["Embedding model", "mxbai-embed-large:latest, served by the local Ollama instance via /api/embed"],
    ["Vector store", "ChromaDB PersistentClient at .chromadb/ in the project root"],
    ["Collection name", "course_kb"],
    ["Chunking", "900 characters with 150-character overlap"],
    ["Chunk IDs", "MD5 hash of source path + chunk index + first 100 characters (stable across re-indexing)"],
    ["Injection scanning", "Regex scan of retrieved chunks; matches are labelled [UNTRUSTED / FLAGGED CONTENT] in "
                           "the assembled context and flagged in the UI"],
])
body(doc, "Build / refresh index upserts chunks: existing chunks with the same ID are replaced and new chunks are "
          "added, so re-indexing after adding a file is safe and non-destructive.")
callout(doc, "⚠️  Portability note:",
        "Chunk IDs incorporate the absolute source path, so an index built on one machine does not match paths on "
        "another. If you distribute the project folder, have students rebuild the index rather than shipping "
        ".chromadb/ — it is gitignored for this reason.")

h2(doc, "8.3 Ollama Integration")
body(doc, "The system calls Ollama at http://localhost:11434 unless OLLAMA_URL is set. Relevant settings:")
bullets(doc, [
    "Timeout: 300 seconds per call, overridable with OLLAMA_TIMEOUT_S. Long runs on CPU may approach this limit.",
    "Temperature: 0.2 for agent runs, 0.15 for final synthesis. Lower temperature is more deterministic, less "
    "creative.",
    "Streaming: disabled. The app waits for the full response before displaying it.",
])

h2(doc, "8.4 Guided Walkthrough Step Sequence")
body(doc, "The walkthrough builds its plan at run time. A scenario with tabular evidence and RAG enabled "
          "produces 17 steps; without RAG the four retrieval steps are omitted, leaving 13. The four scenarios "
          "that ship no CSV artifacts omit the two metrics steps as well, giving 15 and 11.")
table(doc, ["#", "Step", "Type"], [
    ["1", "Load scenario casefile and evidence", "load_casefile"],
    ["2", "Select deterministic analyses for the tabular evidence", "metrics_plan"],
    ["3", "Compute deterministic metrics over the tabular evidence", "metrics_compute"],
    ["4", "Embed the retrieval query", "rag_embed_query"],
    ["5", "Search the knowledge base", "rag_similarity_search"],
    ["6", "Scan retrieved content for injection signals", "rag_flag_check"],
    ["7", "Assemble the RAG context block", "rag_assemble_context"],
    ["8–15", "Construct prompt and run analysis, for each of the four agents in turn",
     "agent_prompt_construct, agent_llm_call"],
    ["16", "Construct final synthesis prompt", "synthesis_prompt_construct"],
    ["17", "Generate final incident report", "synthesis_llm_call"],
])
body(doc, "Each step carries a fixed what / how / why teaching card filled in with the real values captured when "
          "that step ran — embedding dimensions, chunk counts, prompt character counts, call durations. The cards "
          "require no LLM call, so they are instant and cannot fail mid-demonstration.")

h2(doc, "8.5 Deterministic Evidence Metrics")
body(doc, "Eight of the twelve scenarios ship CSV log evidence. Before any agent reasons about it, a fixed "
          "registry of pandas analyzers computes measurements over it, and those measurements are injected into "
          "every agent prompt alongside the retrieved context.")
table(doc, ["Analyzer", "What it measures"], [
    ["interval_regularity", "Mean, median, spread and coefficient of variation of the gaps between events. A CV "
                            "below 0.05 is machine-regular; above 0.35 is consistent with human jitter."],
    ["off_hours_share", "Proportion of events outside business hours, with the timezone assumption printed."],
    ["outcome_breakdown", "Success, failure and action counts; HTTP status buckets; longest failure run."],
    ["volume_escalation", "Totals, max/min ratio, longest monotonic increase, top contributors by share."],
    ["entity_cardinality", "Distinct values per categorical column and the unique-to-row ratio."],
    ["actor_source_pivot", "Per actor: distinct sources and geographies, and the shortest interval between a "
                           "switch — impossible travel as a measured number."],
    ["client_tooling", "Share of non-browser user agents. A heuristic, and labelled as one."],
])
body(doc, "No model-generated code is executed. Selection is rule-based, driven by mapping each CSV's columns onto "
          "analytical roles, and the executed source of every analyzer is displayed to students in the step output "
          "so the calculation can be checked line by line. Values are reproducible: the same file and the same "
          "code return the same numbers on every run.")
body(doc, "Agents are instructed to cite measured numbers and to state explicitly when their reading of the raw "
          "evidence disagrees with one. This is a gradeable critique target — see the rubric note in section 6.2.")
callout(doc, "⚠️  Sample size:",
        "Analyzers attach a caveat whenever fewer than five intervals were measured. Several artifacts are small "
        "by design, and a coefficient of variation over three intervals describes that sample rather than any "
        "stable pattern. Point students at the caveat rather than letting them quote the number bare.")

h2(doc, "8.6 Two Teaching Traps in the Measured Data")
body(doc, "Both are deliberate and both reward the habit this course is built around — refusing to treat a number "
          "as a finding until it has been interpreted.")
body(doc, "The traffic-spike log (availability_incident_ddos) measures an interval coefficient of variation well "
          "above the machine-regular band, with a unique-source-to-row ratio around 0.65. Read carelessly, high "
          "unique-IP counts look like a distributed attack. Read with the timing figure, the evidence leans toward "
          "a genuine crowd — which is exactly what that scenario's learning goal about inconclusive evidence asks "
          "students to articulate.")
body(doc, "The cloud billing export (leaked_api_key_repo) measures a coefficient of variation of 0.000 — perfect "
          "machine regularity. It is not an attacker. It is the billing meter's own fifteen-minute sampling "
          "cadence. A metric without interpretation is not a finding, and this is the cleanest demonstration of "
          "that in the whole set.")

h2(doc, "8.7 Export Formats")
body(doc, "Each exported run bundle is a JSON file in exports/ with the following fields:")
table(doc, ["Field", "Contents"], [
    ["scenario_id", "Identifier from the scenario JSON file"],
    ["scenario_title", "Display title"],
    ["model", "The Ollama model used for this run"],
    ["execution_mode", "CrewAI, or Sequential fallback with the exception type"],
    ["objective", "The mission text used for this run"],
    ["student_notes", "Student notes injected into the prompt"],
    ["rag_context_used", "The full RAG context string passed to agents"],
    ["agent_outputs", "Dict of agent name to output string"],
    ["final_report", "The synthesis markdown"],
    ["raw_crewai_output", "Raw CrewAI output (or the traceback, in fallback mode)"],
    ["step_results", "Per-step technical detail captured during the run"],
])
body(doc, "Both Crew Run and Guided Walkthrough additionally offer two rendered documents, each downloadable as "
          "markdown or HTML:")
table(doc, ["Document", "Contents"], [
    ["Workflow doc", "Every step with its what / how / why card and captured technical detail, with any student "
                     "questions shown inline under the step where they were asked."],
    ["SOP report", "The same run rewritten as a narrative standard operating procedure, with each step's purpose, "
                   "analytical method, findings, and connection to the next step."],
])

h2(doc, "8.8 Interaction Log Format")
body(doc, "logs/interactions.jsonl records one JSON object per line. Every record carries a timestamp, session_id, "
          "and scenario_id; the remaining fields depend on event_type.")
table(doc, ["event_type", "Emitted when"], [
    ["run_complete", "A Crew Run finishes, with the execution mode"],
    ["stage_complete", "An individual agent or the synthesis finishes in Crew Run"],
    ["guided_walkthrough_started", "A student begins a Guided Walkthrough"],
    ["guided_step_complete", "A walkthrough step finishes, with step id, type, and duration"],
    ["question_asked", "A question is asked from the Crew Run chat panel"],
    ["guided_question_asked", "A question is asked during a walkthrough, with the step it was asked at"],
])

# ---------------------------------------------------------- 9. Troubleshooting
h1(doc, "9. Troubleshooting")
table(doc, ["Symptom", "Diagnosis and fix"], [
    ["Ollama reachable: No", "Ollama is not running. Run ollama serve in a separate terminal and keep it running "
                             "during the session."],
    ["CrewAI available: No", "The active environment does not have crewai. The sidebar shows the import error and "
                             "the interpreter path — usually the app was launched from the wrong environment. "
                             "Activate the 3.11 env and relaunch."],
    ["No model found", "No models are pulled. Run ollama pull llama3.1:8b. The app auto-detects after a refresh."],
    ["Indexing fails with an embedding error", "mxbai-embed-large has not been pulled. Run "
                                                "ollama pull mxbai-embed-large, then rebuild the index."],
    ["Crew run spinner runs indefinitely", "Generation timed out (over 300 s) or Ollama crashed. Check the Ollama "
                                            "terminal for errors, or try a smaller model."],
    ["403 or subscription error on a run", "A :cloud model was selected that your Ollama account's plan does not "
                                            "cover. Pick a local model in the sidebar."],
    ["Scenario does not appear in dropdown", "The scenario JSON may be malformed. Validate the JSON syntax."],
    ["RAG returns empty results", "The index was not built or is empty. Go to RAG Control > Build / refresh index."],
    ["Retrieved chunks cite unfamiliar file paths", "The index was built on another machine. Rebuild it locally."],
    ["CrewAI falls back to sequential mid-run", "A crewai API changed or an exception occurred. The execution mode "
                                                 "field names the exception type. Run pip install -r "
                                                 "requirements.txt to restore the pinned version."],
])

# ------------------------------------------------ 10. Course Integration Notes
h1(doc, "10. Course Integration Notes")
h2(doc, "10.1 Where This Lab Fits in a Course")
body(doc, "This lab is designed for the applied phase of an AI + cybersecurity course, after students have "
          "covered:")
bullets(doc, [
    "How LLMs generate text (token prediction, temperature, hallucination risk)",
    "Multi-agent systems and how agents coordinate",
    "Incident response fundamentals (the PICERL cycle or equivalent)",
    "Prompt injection and model risk",
])
body(doc, "It works well as a capstone for a unit on AI in security operations, or as a recurring exercise where "
          "students run different scenarios as the course progresses. With twelve scenarios, a different one can "
          "anchor each week of a term without repetition.")

h2(doc, "10.2 Calibrating Agent Quality")
body(doc, "If you find the agents are too accurate (students cannot find errors) or too incoherent (outputs are "
          "not useful), adjust:")
bullets(doc, [
    "Model: smaller models hallucinate more; larger models are more coherent",
    "Temperature: increase slightly (to 0.4–0.5) to introduce more variability and more hallucination for critique "
    "exercises",
    "Objective: a vague objective produces vaguer agent outputs; a very specific objective produces tighter, "
    "harder-to-critique output",
    "RAG: disabling RAG grounding increases hallucination and can produce interesting “without grounding vs. with "
    "grounding” comparison exercises",
])
callout(doc, "Exercise idea:",
        "Run the same scenario twice: once with RAG disabled, once with it enabled. Have students compare the agent "
        "outputs and identify specific claims that changed. This makes the value of retrieval augmentation "
        "concrete — and the Guided Walkthrough makes it sharper still, because the four retrieval steps disappear "
        "from the plan entirely when RAG is off.")

h2(doc, "10.3 Important Limitations to Communicate to Students")
bullets(doc, [
    "This is a teaching and experimentation platform, not a production SOC tool.",
    "It does not isolate malware, connect to real SIEMs, or guarantee safe handling of live malicious content.",
    "Agent outputs should never be treated as authoritative security guidance.",
    "The local model has no access to current threat intelligence or live vulnerability databases.",
    "The prompt-injection scanning on uploaded documents is a regex-based teaching signal, not a security control.",
])

h2(doc, "10.4 Extending to New Topics")
body(doc, "The lab can be extended to cover additional AI + security topics by:")
bullets(doc, [
    "Adding KB files on prompt injection, adversarial ML, or supply chain attacks and running the crew against "
    "scenarios that reference those topics",
    "Uploading a document containing deliberate injection language on the RAG Control page, then showing the "
    "flagged chunk and tracing it into the assembled context in the Guided Walkthrough",
    "Running the crew with and without student notes to show how human framing changes AI output",
    "Assigning students to add their own scenario JSON and present it to the class",
])

out = ROOT / f"instructor_manual{EXT}"
doc.save(str(out))
print(f"wrote {out}")
