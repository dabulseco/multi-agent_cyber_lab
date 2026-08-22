# Instructor Manual

**Multi-Agent Cybersecurity Lab**

*AI + Cybersecurity — Course Facilitator Reference*

Multi-Agent Cybersecurity Lab Environment  
Version 2.0 — August 2026

---

## 1. Overview

This document covers everything you need to deploy, run, and extend the Multi-Agent Cybersecurity Lab in a course setting. The lab is designed for courses at the intersection of AI and cybersecurity, where a central learning objective is teaching students to critically evaluate AI-generated analysis rather than accept it uncritically.

The system is intentionally local-first: all inference, retrieval, and storage runs on the instructor or student machine. No internet connection is required after initial setup. No student data leaves the local environment.

> **🎯  Pedagogical purpose:** The AI agents in this system are calibrated to be useful but imperfect. They will overclaim, hallucinate, and occasionally draw unjustified conclusions. This is by design. The lab succeeds when students catch these errors — not when the agents are correct.

### 1.1 System Architecture

The platform consists of seven integrated components:

| Component | Role |
|---|---|
| Streamlit (app/main.py) | Local web interface. Six pages: Home, Scenario Lab, Crew Run, Guided Walkthrough, RAG Control, Instructor Dashboard. |
| Ollama | Local LLM inference engine. Serves both the chat models and the embedding model. Runs on CPU or GPU. No cloud API required. |
| CrewAI | Multi-agent orchestration for the Crew Run page. Optional — the app falls back to a built-in sequential orchestrator if it is unavailable. |
| ChromaDB | Local vector database for RAG retrieval, persisted to .chromadb/ in the project root. Embeddings are produced by Ollama, not by a separate ML library. |
| Simulation engine (core/simulation.py) | Loads scenario definitions, artifact paths, and preview rendering. |
| Guided workflow engine (core/guided_workflow.py) | Breaks a run into 11–15 inspectable steps, and renders the workflow document and SOP report. |
| Interaction log (core/interaction_log.py) | Append-only local record of every step completion and student question, written to logs/interactions.jsonl. |

### 1.2 The Four Agents

| Agent | System prompt focus |
|---|---|
| SOC Analyst | Evidence triage, timeline reconstruction, separating observed facts from inference. |
| Threat Hunter | Attacker behavior, plausible techniques, lateral movement, detection gaps, alternative hypotheses. |
| Incident Responder | Containment, eradication, recovery, operational prioritization. |
| Security Reviewer | Uncertainty, overclaiming, teaching clarity, whether conclusions are justified by evidence. |

A final synthesis pass runs after the four agents, using a separate system prompt instructed to produce: Confirmed Facts, Likely Inferences, Remaining Unknowns, Recommended Immediate Actions, Recommended Longer-Term Controls, and Notes for Students.

### 1.3 Two Ways to Run a Scenario

The same underlying pipeline is exposed through two pages with different classroom purposes. Both run the same agents over the same evidence and produce the same kind of final report.

|   | Crew Run | Guided Walkthrough |
|---|---|---|
| Pace | Continuous. Each agent's findings appear the moment that agent finishes. | Paused after every step. The student clicks to advance. |
| Granularity | Five stages: four agents plus synthesis. | 11–15 steps, including RAG embedding, similarity search, injection scanning, context assembly, and every prompt construction. |
| Teaching material | Technical detail per stage in an expander. | A what / how / why card plus a real technical readout for every step. |
| Orchestration | CrewAI when available, sequential fallback otherwise. | Always calls Ollama directly. CrewAI is not involved. |
| Best for | Live demonstration, second and third runs, assessment. | First exposure, explaining how RAG and agent prompting actually work. |

## 2. Environment Setup

### 2.1 Prerequisites

- macOS, Linux, or Windows 10/11 with WSL2
- Python 3.11 — this is the tested version, and requirements.txt pins the dependency versions it was tested with
- Ollama installed: https://ollama.ai
- At least 8 GB RAM; 16 GB recommended for 7–8B models
- ~4 GB disk space for model weights (varies by model), plus ~700 MB for the embedding model

### 2.2 Installation Steps

Install Ollama, then pull one chat model and the embedding model:

```bash
ollama pull llama3.1:8b        # or: ollama pull qwen2.5:7b
ollama pull mxbai-embed-large  # required for RAG
```

Clone the repository:

```bash
git clone git@github.com:dabulseco/multi-agent_cyber_lab.git
cd multi-agent_cyber_lab
```

Create and activate a Python 3.11 environment:

```bash
conda create -n cyber python=3.11
conda activate cyber
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app/main.py
```

On first run, go to RAG Control and click Build / refresh index to populate the knowledge base.

> **⚠️  Environment warning:** The embedding model must be pulled before indexing will work — RAG calls Ollama directly for embeddings, so a missing mxbai-embed-large produces an indexing error rather than a silent fallback. Likewise, installing into a Python version other than 3.11 may leave crewai unresolved, in which case Crew Run uses the sequential path. The sidebar reports both conditions.

### 2.3 Installed Dependencies

requirements.txt pins exact versions of the direct dependencies to the tested environment. Transitive dependencies are left to resolve normally so the install stays portable across platforms.

| Package | Purpose |
|---|---|
| streamlit==1.57.0 | Web interface and multi-page navigation |
| pandas==3.0.2 | CSV artifact parsing and tabular display |
| tabulate==0.10.0 | Markdown table rendering for CSV previews |
| requests==2.33.1 | HTTP calls to the Ollama API |
| chromadb==1.5.8 | Local vector database for RAG |
| pypdf==6.10.2 | PDF extraction for RAG indexing |
| python-docx==1.2.0 | Word document extraction for RAG indexing |
| crewai==0.193.2 | Multi-agent orchestration for the Crew Run page |
| python-dotenv==1.2.2 | Reads .env for CrewAI telemetry and Ollama host settings |
| markdown==3.10.3 | Renders the HTML versions of the workflow and SOP documents |

Embeddings require no Python package: they are served by Ollama over its local HTTP API.

### 2.4 Verifying the Environment Before Class

The sidebar reports the two conditions that most often break a session. Check both before students arrive:

- Ollama reachable — must read Yes. If No, Ollama is not running.
- CrewAI available — reads Yes with a version number when the environment is correct. If it reads No, the sidebar names the import error and the interpreter path in use, and Crew Run will use the sequential fallback for the whole session.

Guided Walkthrough never uses CrewAI, so that page is unaffected by a CrewAI problem and remains a reliable teaching path even in a broken environment.

## 3. Running a Classroom Session

### 3.1 Recommended Classroom Flow

| Phase | Activity |
|---|---|
| Pre-class (instructor) | Verify Ollama is running, a model is loaded, and the sidebar reports CrewAI available. Build the RAG index. Run your chosen scenario once to confirm outputs are coherent with the selected model. |
| Opening (10–15 min) | Introduce the scenario on the Home page. Review the initial situation and learning goals. Ask students to form initial hypotheses before seeing agent output. |
| Artifact review (10–15 min) | Walk through Scenario Lab. Read each artifact together. Highlight what is and is not in the evidence. |
| RAG setup (5 min) | Have students open RAG Control and build the index. Briefly explain what RAG does and why it matters. |
| Pipeline teaching (20–40 min, optional) | Run the Guided Walkthrough on the projector, pausing at the RAG steps and one agent prompt. This is where students see what the agents actually receive. |
| Crew run (10–20 min) | Students set their objective and student notes, then run the crew. Agents may take several minutes on CPU-only hardware. |
| Analysis (20–30 min) | Students read agent outputs and the final synthesis. Identify at least one claim per agent that is unsupported. Compare to their pre-run hypothesis. |
| Debrief (15–20 min) | Use the Instructor Dashboard grading prompts to drive discussion. Which agent overclaimed? Which evidence was weakest? Review the questions students asked. |
| Export and submit | Students export the run bundle and begin their written critique. |

### 3.2 Model Selection Guidance

The quality and coherence of agent outputs depends heavily on the model selected. Recommendations:

| Model | Notes |
|---|---|
| llama3.1:8b | Good balance of quality and speed on consumer hardware. Recommended default. |
| qwen2.5:7b | Strong instruction following, slightly faster than llama3.1 on some hardware. |
| mistral:7b | Reasonable quality, widely available, good fallback. |
| llama3.1:70b (quantized) | Higher quality outputs but requires 32+ GB RAM or GPU. Not suitable for most student machines. |

> **⚠️  Note:** Smaller models (3–4B) may produce incoherent or very short agent outputs. Test your chosen model on the scenario you plan to teach before class and confirm the synthesis report is readable. The model picker also lists any Ollama Cloud (:cloud) models your account can reach; these are not required, and a run against one will fail with a subscription error if your plan does not cover it.

### 3.3 Choosing Between Crew Run and Guided Walkthrough

For a first encounter with the material, run the Guided Walkthrough. Students who have only seen Crew Run tend to treat the pipeline as a black box that emits opinions; the walkthrough shows them the embedding call, the retrieved chunks, the injection scan, and the exact prompt each agent receives.

For assessment and for second or third scenarios, use Crew Run. It is faster, it produces the export bundle used for grading, and by that point the mechanics are no longer the lesson.

## 4. Scenario Reference

The lab ships with 12 scenarios. All appear automatically in the scenario dropdowns; none requires configuration. Each has three timed injects that simulate new information arriving during the incident.

| Scenario | Focus area | Artifacts |
|---|---|---|
| Possible Insider Data Exfiltration | Insider threat | 2 |
| Credential Theft and Suspicious VPN Access | Phishing / account compromise | 5 |
| Insider Sabotage by a Departing Administrator | Insider threat / offboarding | 2 |
| Ransomware Deployment and Extortion | Ransomware | 2 |
| Cloud Storage Bucket Misconfiguration | Cloud misconfiguration | 2 |
| Leaked Cloud API Key in a Public Repository | Secrets management | 3 |
| Business Email Compromise and Invoice Fraud | Social engineering / fraud | 2 |
| Software Supply Chain Compromise | Software supply chain | 3 |
| Traffic Spike: Possible DDoS or Legitimate Surge | Availability | 2 |
| BYOD Smishing and Attempted App Sideload | Mobile / BYOD | 3 |
| OT/ICS Network Segmentation Exposure | OT / ICS | 3 |
| Internal AI Assistant Prompt-Injection Data Leak | AI-specific risk | 3 |

### 4.1 Possible Insider Data Exfiltration

File: data/incidents/insider_exfiltration.json

Summary: Outbound traffic from a finance host increased sharply late in the day, and a service account appears to retain excessive permissions.

Learning goals:

- Analyze egress anomalies
- Compare insider-threat and external-compromise hypotheses
- Propose evidence-driven next steps instead of assuming motive

Artifacts linked to this scenario:

- data/logs/egress_exfiltration.csv
- data/configs/fileshare_access_review.txt

Simulation injects:

- 16:20 — Manager asks whether an employee intentionally exported records.
- 16:24 — Analyst notes the transfers used HTTPS to an unfamiliar destination.
- 16:32 — A broad service account was used during the transfer window.

> **Instructor note:** This scenario is designed to resist simple conclusions. The log shows escalating transfer sizes from one host, but also one much smaller transfer from a second host to a different IP. Students should notice that the evidence is consistent with both insider exfiltration and compromised service account misuse. The agents will often overclaim motive — use this as your primary critique target.

### 4.2 Credential Theft and Suspicious VPN Access

File: data/incidents/credential_theft_vpn.json

Summary: A staff member reports mailbox access issues shortly after receiving a password-reset email. Security operations sees unusual VPN activity.

Learning goals:

- Distinguish phishing indicators from confirmed account compromise
- Correlate email, VPN, and file access artifacts
- Separate containment actions from longer-term control improvements

Artifacts linked to this scenario:

- data/phishing/credential_reset_email.txt
- data/logs/web_log_credential_theft.csv
- data/logs/auth_log_ransomware_lab.csv
- data/configs/vpn_gateway_notes.txt
- data/configs/fileshare_access_review.txt

Simulation injects:

- 08:35 — Help desk confirms the user clicked a reset link in an email.
- 08:42 — VPN logs show successful login from a foreign IP followed by fileshare access.
- 08:47 — Leadership asks whether regulated data was likely exposed.

> **Instructor note:** This is the most evidence-rich scenario and is well suited to advanced students or second runs. The phishing email is clearly suspicious but does not confirm credential capture. Students should flag that the VPN login from a foreign IP is consistent with compromise but could theoretically be a legitimate remote login. The agents often overstate certainty about data exfiltration without evidence of what files were actually accessed.

### 4.3 Insider Sabotage by a Departing Administrator

File: data/incidents/insider_sabotage.json

Summary: A former systems administrator's access was not revoked promptly after resignation, and backup jobs were deleted using a newly created service account during the gap.

Learning goals:

- Identify privileged-access review and offboarding process gaps
- Distinguish malicious sabotage from an honest configuration mistake
- Prioritize access revocation as the primary immediate control

Artifacts linked to this scenario:

- data/evidence/offboarding_notes.txt
- data/logs/auth_log_sabotage.csv

Simulation injects:

- 07:30 — IT confirms t.walker's access was still active three days after their last day due to a delayed offboarding ticket.
- 07:38 — The new service account svc-backup-temp was created and used within minutes of t.walker's login, then never used again.
- 07:45 — Leadership asks whether this was intentional sabotage or a mistake during a rushed handover.

> **Instructor note:** The critique target here is intent. Deleted backup jobs during an unrevoked-access window look damning, but the same evidence is consistent with an honest configuration mistake by someone whose account was still active. Watch for agents that treat the process failure (late revocation) and the alleged act (sabotage) as the same finding — they are separate, and only one is clearly established.

### 4.4 Ransomware Deployment and Extortion

File: data/incidents/ransomware_deployment_extortion.json

Summary: Multiple file servers become unreachable overnight and a ransom note appears on shared drives. Backup jobs also show unexpected activity.

Learning goals:

- Sequence initial access, lateral movement, and encryption impact from log evidence
- Recognize double-extortion (data theft plus encryption) versus encryption alone
- Separate immediate containment actions from root-cause investigation

Artifacts linked to this scenario:

- data/logs/auth_log_ransomware_lab.csv
- data/evidence/ransom_note.txt

Simulation injects:

- 06:15 — IT confirms backup jobs failed overnight and the backup account was used from an unfamiliar host.
- 06:22 — The ransom note claims data was copied out before encryption began.
- 06:30 — Leadership asks whether to pay, and whether law enforcement should be contacted first.

> **Instructor note:** Students should build a sequence — initial access, lateral movement, encryption — and mark which links in that chain the evidence actually supports. Agents frequently assert double extortion (data stolen as well as encrypted) on the strength of the ransom note alone; the note is the attacker's claim, not evidence of exfiltration. That distinction is the strongest single teaching moment in this scenario.

### 4.5 Cloud Storage Bucket Misconfiguration

File: data/incidents/cloud_storage_misconfiguration.json

Summary: A routine review finds that a cloud storage bucket was briefly configured for public read access, and the audit log shows anonymous requests during that window.

Learning goals:

- Apply the shared-responsibility model to a cloud misconfiguration
- Distinguish evidence of possible exposure from evidence of confirmed data exfiltration
- Recommend proportionate response given genuinely incomplete evidence

Artifacts linked to this scenario:

- data/logs/cloud_audit_log.csv
- data/configs/bucket_policy_notes.txt

Simulation injects:

- 09:00 — Security team confirms the public ACL was live for roughly seven hours before being reverted.
- 09:10 — The audit log shows anonymous GetObject and ListBucket calls, but no unusually large transfer volumes are recorded.
- 09:25 — Leadership asks whether this must be reported as a confirmed data breach.

> **Instructor note:** A good scenario for teaching proportionate response. Anonymous requests during a public-access window prove possible exposure, not confirmed exfiltration, and the audit log genuinely cannot settle the question. Reward students who say the evidence is inconclusive and specify what would resolve it, rather than those who pick a side confidently.

### 4.6 Leaked Cloud API Key in a Public Repository

File: data/incidents/leaked_api_key_repo.json

Summary: An intern accidentally commits a live cloud API key to a public GitHub repository, and anomalous compute usage appears in the billing dashboard shortly after.

Learning goals:

- Apply secret-scanning and credential-hygiene practices to a real leak
- Assess blast radius by reasoning about what the leaked key could actually access
- Treat rapid rotation as the primary response action rather than only cleanup

Artifacts linked to this scenario:

- data/evidence/github_commit_diff.txt
- data/evidence/cloud_billing_anomaly.csv
- data/evidence/key_revocation_timeline.txt

Simulation injects:

- 10:00 — Billing shows compute usage spinning up in regions the organization has never used before.
- 10:10 — The on-call engineer confirms the key found in the commit is still active and was not yet revoked.
- 10:20 — Management asks how much this incident is going to cost and whether more keys may be exposed elsewhere in the repository history.

> **Instructor note:** Blast radius is the analytical core here: what could this key actually reach? Agents tend to jump to cleanup steps (rewrite git history, delete the commit) ahead of the action that actually stops the bleeding, which is rotation. Ask students to order the response actions and defend the ordering.

### 4.7 Business Email Compromise and Invoice Fraud

File: data/incidents/bec_invoice_fraud.json

Summary: Accounts payable processes a wire transfer to updated bank details after receiving an urgent email from a familiar vendor contact, only to have the real vendor later ask why an invoice remains unpaid.

Learning goals:

- Analyze sender domains and headers for lookalike-domain spoofing
- Identify social-engineering pressure tactics such as urgency and authority
- Separate the human process failure from the technical delivery mechanism

Artifacts linked to this scenario:

- data/phishing/bec_spoofed_email.txt
- data/evidence/wire_transfer_request.txt

Simulation injects:

- 16:05 — The real Northfield Partners contact emails asking why invoice INV-4471 is still marked unpaid.
- 16:12 — AP confirms the original request came in under time pressure and was not verified by phone.
- 16:20 — Finance asks whether the funds can still be recovered and how this was allowed to happen.

> **Instructor note:** The technical indicator (a lookalike sender domain) is easy to spot; the harder question is the process failure that let a payment change proceed on the strength of an email. Students who only critique the email headers have done half the analysis. Agents often recommend email controls and never mention out-of-band verification of bank detail changes.

### 4.8 Software Supply Chain Compromise

File: data/incidents/supply_chain_compromise.json

Summary: A routine dependency update pulled in a package version published from a compromised maintainer account, and the vendor has now disclosed the incident.

Learning goals:

- Reason about trust boundaries introduced by transitive dependencies
- Distinguish a vulnerable dependency being present from confirmed exploitation in this environment
- Explain why exposure and compromise require different evidence and different responses

Artifacts linked to this scenario:

- data/evidence/dependency_diff.txt
- data/evidence/build_log_excerpt.txt
- data/evidence/vendor_disclosure_email.txt

Simulation injects:

- 10:00 — CI logs confirm 1.4.3 was installed during build #5521 and the post-install script executed a network callback.
- 10:08 — The vendor advisory states impact is confirmed in only a subset of reported cases, not all installations.
- 10:15 — Engineering asks whether production was affected and whether this needs to be reported as a breach.

> **Instructor note:** This scenario turns on a distinction students routinely collapse: a compromised package being present in the build is exposure; evidence of it executing against this environment is compromise. They require different evidence and different responses. Expect agents to slide from one to the other mid-paragraph — have students find the exact sentence where it happens.

### 4.9 Traffic Spike: Possible DDoS or Legitimate Surge

File: data/incidents/availability_incident_ddos.json

Summary: The admissions website begins returning intermittent errors during a sudden traffic increase, and the on-call team must decide whether this is an attack or a legitimate surge.

Learning goals:

- Evaluate whether traffic evidence supports an attack hypothesis or a benign explanation
- Make service-prioritization decisions under time pressure with incomplete certainty
- Practice stating that evidence is inconclusive rather than defaulting to a confident conclusion

Artifacts linked to this scenario:

- data/logs/web_log_traffic_spike.csv
- data/configs/waf_loadbalancer_notes.txt

Simulation injects:

- 14:00 — On-call engineer asks whether this should be treated as a DDoS attack and mitigated with aggressive rate limiting.
- 14:03 — Marketing mentions an admissions-deadline email campaign was scheduled for the same time window.
- 14:07 — Leadership asks for a same-hour decision: block traffic aggressively, or scale up capacity and monitor.

> **Instructor note:** The most useful scenario for practising 'the evidence does not decide this'. The traffic pattern is compatible with both an attack and a legitimate surge, and the on-call decision has to be made anyway. Grade on whether students separate the operational decision from the causal claim, rather than on which cause they pick.

### 4.10 BYOD Smishing and Attempted App Sideload

File: data/incidents/mobile_byod_compromise.json

Summary: An employee's personal phone receives a smishing message impersonating IT, and shortly after, the device attempts to sideload a suspicious app that is blocked by mobile device management.

Learning goals:

- Assess BYOD risk surface and the limits of MDM telemetry on personal devices
- Recognize privacy and legal boundaries when investigating a personal device
- Work with weaker evidence quality than a fully managed endpoint provides

Artifacts linked to this scenario:

- data/evidence/mdm_enrollment_log.csv
- data/evidence/smishing_message.txt
- data/evidence/app_permissions_list.txt

Simulation injects:

- 14:20 — The user reports entering their campus credentials on a link from a text message before realizing the domain looked wrong.
- 14:25 — MDM shows a sideload attempt for an app requesting SMS and accessibility permissions, which was blocked.
- 14:35 — The user asks whether IT can just remotely wipe their personal phone to be safe.

> **Instructor note:** Evidence quality is deliberately weaker here than on a managed endpoint, and MDM telemetry on a personal device has real limits. Strong students will note both the investigative constraint and the privacy and legal boundaries that apply to a personal phone. Agents rarely raise the privacy dimension unprompted — a good gap to point out during debrief.

### 4.11 OT/ICS Network Segmentation Exposure

File: data/incidents/ot_ics_exposure.json

Summary: A leftover firewall rule from a vendor maintenance visit left a path open from the corporate IT network into the plant's OT historian server for eleven days.

Learning goals:

- Identify IT/OT segmentation failures and their root causes
- Weigh safety-versus-security tradeoffs specific to operational technology
- Distinguish confirmed unauthorized control actions from unexplained but benign access

Artifacts linked to this scenario:

- data/evidence/ot_network_flow_notes.txt
- data/evidence/vendor_security_advisory.txt
- data/evidence/engineer_incident_notes.txt

Simulation injects:

- 08:10 — The engineer on shift confirms no PLC setpoint changes occurred and production values stayed normal throughout the window.
- 08:18 — The vendor advisory notes similar leftover access has contributed to incidents elsewhere, though usually without unauthorized control commands.
- 08:25 — Plant management asks whether production needs to be halted while this is investigated.

> **Instructor note:** Safety-versus-security tradeoffs make OT different from IT, and the standard containment reflex — cut the connection — may not be available on a live plant network. Watch for agents recommending IT-style remediation with no acknowledgement of process safety. Unexplained access is also not the same as a confirmed unauthorized control action.

### 4.12 Internal AI Assistant Prompt-Injection Data Leak

File: data/incidents/ai_assistant_prompt_injection_leak.json

Summary: An internal support chatbot, grounded via retrieval over the support ticket queue, is manipulated by an instruction embedded in a submitted ticket into disclosing an internal contact list and account recovery codes.

Learning goals:

- Recognize prompt injection carried through retrieved content rather than direct user input
- Evaluate whether an AI system properly separated trusted instructions from untrusted evidence
- Reason about another AI system's design flaws as a third-party reviewer

Artifacts linked to this scenario:

- data/evidence/poisoned_support_ticket.txt
- data/evidence/chatbot_transcript.txt
- data/evidence/it_incident_notes.txt

Simulation injects:

- 11:00 — IT confirms no authentication step actually occurred in the flagged session, despite the assistant's response claiming a verified administrator.
- 11:08 — A review shows the assistant's prompt design never distinguished trusted instructions from retrieved, untrusted ticket content.
- 11:15 — Leadership asks whether this is an isolated incident or a systemic design flaw likely to recur.

> **Instructor note:** This scenario asks students to review another AI system's design failure, which pairs directly with the prompt-injection material in kb/03 and kb/05. The instructive irony is that the reviewing agents are themselves susceptible to the same class of flaw — a point worth making explicitly during debrief, and one you can demonstrate live using the injection flagging on the RAG Control page.

## 5. Extending the Lab

### 5.1 Adding a New Scenario

Scenarios are JSON files in data/incidents/. Create a new file following this structure:

**Schema:**

```json
{
  "id": "unique_scenario_id",
  "title": "Scenario Display Title",
  "summary": "One-paragraph summary for the Home page.",
  "learning_goals": ["Goal 1", "Goal 2"],
  "initial_situation": "What the responder knows at time 0.",
  "injects": [
    { "time": "HH:MM", "message": "New information arriving at this time." }
  ],
  "artifacts": [
    "data/logs/your_log.csv",
    "data/configs/your_config.txt"
  ],
  "default_objective": "The default crew mission for this scenario."
}
```

The new scenario appears automatically in the scenario dropdowns on the Home, Scenario Lab, Crew Run, and Guided Walkthrough pages. No code changes are required.

### 5.2 Adding Artifacts

Place artifact files in the appropriate subdirectory:

- data/logs/ — CSV log files (auth logs, network logs, web access logs, cloud audit logs)
- data/phishing/ — email text files
- data/configs/ — configuration notes, access reviews, policy documents
- data/evidence/ — mixed supporting evidence: incident notes, transcripts, commit diffs, advisories, ransom notes, billing exports

Supported artifact types for preview: .md, .txt, .log, .conf, .json (rendered as a code block), .csv (rendered as a markdown table, first 20 rows).

### 5.3 Adding Knowledge Base Content

Knowledge base files live in kb/. Drop any supported file type into that directory:

- .md, .txt, .py, .csv, .json, .yaml, .yml, .log — read as plain text
- .pdf — extracted page by page via pypdf
- .docx — extracted paragraph by paragraph via python-docx

After adding files, go to RAG Control > Build / refresh index. New content is chunked into 900-character segments with 150-character overlap and embedded with mxbai-embed-large through the local Ollama server.

> **Tip:** Add your course slides, reading summaries, or reference documents to kb/ before class. The agents will draw on them during retrieval, grounding their analysis in material students have studied.

### 5.4 Adding Lab Handout Files

Lab markdown files in labs/ are included in the RAG index when Build / refresh index is run with the Include built-in KB and labs checkbox enabled. Place new lab handouts (as .md files) in labs/ to make them retrievable.

## 6. Assessment and Grading

### 6.1 Required Deliverables

| Deliverable | Description |
|---|---|
| Exported run bundle | JSON file from Crew Run > Export current run. Confirms the student ran the lab and records the full agent output. File: exports/<scenario_id>_<timestamp>.json. |
| One-page critique | Written analysis of agent output quality. Must answer four structured questions (see below). |
| Corrected human summary | Student-authored revision of the final synthesis that removes unsupported claims, adds uncertainty language, and proposes additional verification steps. |

If you teach with the Guided Walkthrough, the workflow document is a useful optional fifth deliverable: it captures every step the student advanced through along with every question they asked, which makes engagement visible in a way the JSON bundle does not.

### 6.2 Critique Rubric

The four required critique questions and what strong answers look like:

| Question | Strong answer criteria |
|---|---|
| Which findings were strongly evidence-supported? | Cites a specific log row or artifact line. Names the agent. Explains why the evidence directly supports the claim. |
| Which findings were weakly supported or inferred? | Names at least two inferences presented as facts. Explains what evidence would be needed to confirm them. |
| Which agent was most cautious? | Goes beyond “the Security Reviewer.” Compares hedging language across agents with examples. May identify a surprising second choice. |
| What would you verify next? | Proposes concrete investigative steps. Specifies what system, log, or artifact to query. Does not propose generic steps like “check more logs.” |

### 6.3 Suggested Grading Weights

| Component | Weight |
|---|---|
| Run bundle submitted and valid | 10% |
| Critique question 1 (evidence support) | 20% |
| Critique question 2 (weak inferences) | 20% |
| Critique question 3 (agent caution) | 15% |
| Critique question 4 (next verification) | 15% |
| Corrected human summary | 20% |

### 6.4 Common Student Errors to Watch For

- Submitting the AI synthesis as their own corrected summary (verbatim or near-verbatim)
- Critique answers that do not cite any specific artifact or log data
- Accepting the agents’ motive claims (insider, attacker) without noting these are unconfirmed
- Failing to notice when the Security Reviewer itself overclaims
- Conflating “the crew concluded X” with “X is true” in their own writing
- Treating an answer from the in-app chat panel as verified fact — it is another model output, grounded in the evidence but not authoritative

## 7. Instructor Dashboard

The Instructor Dashboard page is available to both instructors and students. It serves three functions.

First, it displays suggested grading prompts and a reflection structure that mirrors the deliverable requirements. You can use this in class to prime discussion before students read the synthesis.

Second, it shows the runs completed in the current browser session. Each is expandable and shows the execution mode and full final synthesis. This is useful for live demonstration: run the same scenario twice with different objectives or student notes and compare the outputs. This list is session state only and resets when the app restarts.

Third, and independently of session state, it renders the interaction log — a persistent record across all sessions and all students who have used this installation.

| Panel | What it shows |
|---|---|
| Summary metrics | Runs and walkthroughs started, crew stage completions, guided steps completed, and total questions asked. |
| Student questions | Every question asked in Crew Run or Guided Walkthrough, with the scenario, the step it was asked at, an answer preview, and a truncated session id. |

> **Classroom use:** The question log is the most direct feedback signal in the system. Questions cluster where the material is weak — if six students ask what RAG poisoning is at the same walkthrough step, that concept needs more time in lecture, not more time in the lab. Review it after each session.

The log is written to logs/interactions.jsonl, one JSON object per line, appended as events occur. It is gitignored and never leaves the machine. Delete the file to reset the dashboard.

## 8. Technical Reference

### 8.1 Execution Modes

The Crew Run page has two execution paths. Guided Walkthrough always uses direct Ollama calls and is not affected by either.

#### CrewAI (preferred)

When crewai imports successfully, each of the four agents runs as its own single-task Crew, executed one at a time, with an explicitly configured Ollama LLM (CrewAI would otherwise default to an OpenAI-backed model through LiteLLM and fail, since this app never configures an OpenAI key). Agents are created with allow_delegation=False to prevent recursive delegation.

Running one crew per agent rather than a single four-task crew is deliberate: it returns a real result the instant each agent finishes, which is what makes the live stage-by-stage reveal possible. The tasks never shared CrewAI-managed context between roles, so nothing is lost by separating them. All three execution paths — CrewAI, sequential, and Guided Walkthrough — build their prompts with the same function, so they ask the model the same thing.

#### Sequential fallback

If crewai is missing or raises during a run, the system falls back to a built-in loop that calls the Ollama generate endpoint once per agent. Output quality is similar; the difference is that the CrewAI orchestration layer is not involved. Availability is resolved when the app starts and shown in the sidebar, and the execution mode recorded in the run summary and the export bundle tells you which path actually ran, including the exception type if a fallback occurred.

### 8.2 RAG Pipeline

| Setting | Value |
|---|---|
| Embedding model | mxbai-embed-large:latest, served by the local Ollama instance via /api/embed |
| Vector store | ChromaDB PersistentClient at .chromadb/ in the project root |
| Collection name | course_kb |
| Chunking | 900 characters with 150-character overlap |
| Chunk IDs | MD5 hash of source path + chunk index + first 100 characters (stable across re-indexing) |
| Injection scanning | Regex scan of retrieved chunks; matches are labelled [UNTRUSTED / FLAGGED CONTENT] in the assembled context and flagged in the UI |

Build / refresh index upserts chunks: existing chunks with the same ID are replaced and new chunks are added, so re-indexing after adding a file is safe and non-destructive.

> **⚠️  Portability note:** Chunk IDs incorporate the absolute source path, so an index built on one machine does not match paths on another. If you distribute the project folder, have students rebuild the index rather than shipping .chromadb/ — it is gitignored for this reason.

### 8.3 Ollama Integration

The system calls Ollama at http://localhost:11434 unless OLLAMA_URL is set. Relevant settings:

- Timeout: 300 seconds per call, overridable with OLLAMA_TIMEOUT_S. Long runs on CPU may approach this limit.
- Temperature: 0.2 for agent runs, 0.15 for final synthesis. Lower temperature is more deterministic, less creative.
- Streaming: disabled. The app waits for the full response before displaying it.

### 8.4 Guided Walkthrough Step Sequence

The walkthrough builds its plan at run time. With RAG enabled it produces 15 steps; with RAG disabled the four retrieval steps are omitted, leaving 11.

| # | Step | Type |
|---|---|---|
| 1 | Load scenario casefile and evidence | load_casefile |
| 2 | Embed the retrieval query | rag_embed_query |
| 3 | Search the knowledge base | rag_similarity_search |
| 4 | Scan retrieved content for injection signals | rag_flag_check |
| 5 | Assemble the RAG context block | rag_assemble_context |
| 6–13 | Construct prompt and run analysis, for each of the four agents in turn | agent_prompt_construct, agent_llm_call |
| 14 | Construct final synthesis prompt | synthesis_prompt_construct |
| 15 | Generate final incident report | synthesis_llm_call |

Each step carries a fixed what / how / why teaching card filled in with the real values captured when that step ran — embedding dimensions, chunk counts, prompt character counts, call durations. The cards require no LLM call, so they are instant and cannot fail mid-demonstration.

### 8.5 Export Formats

Each exported run bundle is a JSON file in exports/ with the following fields:

| Field | Contents |
|---|---|
| scenario_id | Identifier from the scenario JSON file |
| scenario_title | Display title |
| model | The Ollama model used for this run |
| execution_mode | CrewAI, or Sequential fallback with the exception type |
| objective | The mission text used for this run |
| student_notes | Student notes injected into the prompt |
| rag_context_used | The full RAG context string passed to agents |
| agent_outputs | Dict of agent name to output string |
| final_report | The synthesis markdown |
| raw_crewai_output | Raw CrewAI output (or the traceback, in fallback mode) |
| step_results | Per-step technical detail captured during the run |

Both Crew Run and Guided Walkthrough additionally offer two rendered documents, each downloadable as markdown or HTML:

| Document | Contents |
|---|---|
| Workflow doc | Every step with its what / how / why card and captured technical detail, with any student questions shown inline under the step where they were asked. |
| SOP report | The same run rewritten as a narrative standard operating procedure, with each step's purpose, analytical method, findings, and connection to the next step. |

### 8.6 Interaction Log Format

logs/interactions.jsonl records one JSON object per line. Every record carries a timestamp, session_id, and scenario_id; the remaining fields depend on event_type.

| event_type | Emitted when |
|---|---|
| run_complete | A Crew Run finishes, with the execution mode |
| stage_complete | An individual agent or the synthesis finishes in Crew Run |
| guided_walkthrough_started | A student begins a Guided Walkthrough |
| guided_step_complete | A walkthrough step finishes, with step id, type, and duration |
| question_asked | A question is asked from the Crew Run chat panel |
| guided_question_asked | A question is asked during a walkthrough, with the step it was asked at |

## 9. Troubleshooting

| Symptom | Diagnosis and fix |
|---|---|
| Ollama reachable: No | Ollama is not running. Run ollama serve in a separate terminal and keep it running during the session. |
| CrewAI available: No | The active environment does not have crewai. The sidebar shows the import error and the interpreter path — usually the app was launched from the wrong environment. Activate the 3.11 env and relaunch. |
| No model found | No models are pulled. Run ollama pull llama3.1:8b. The app auto-detects after a refresh. |
| Indexing fails with an embedding error | mxbai-embed-large has not been pulled. Run ollama pull mxbai-embed-large, then rebuild the index. |
| Crew run spinner runs indefinitely | Generation timed out (over 300 s) or Ollama crashed. Check the Ollama terminal for errors, or try a smaller model. |
| 403 or subscription error on a run | A :cloud model was selected that your Ollama account's plan does not cover. Pick a local model in the sidebar. |
| Scenario does not appear in dropdown | The scenario JSON may be malformed. Validate the JSON syntax. |
| RAG returns empty results | The index was not built or is empty. Go to RAG Control > Build / refresh index. |
| Retrieved chunks cite unfamiliar file paths | The index was built on another machine. Rebuild it locally. |
| CrewAI falls back to sequential mid-run | A crewai API changed or an exception occurred. The execution mode field names the exception type. Run pip install -r requirements.txt to restore the pinned version. |

## 10. Course Integration Notes

### 10.1 Where This Lab Fits in a Course

This lab is designed for the applied phase of an AI + cybersecurity course, after students have covered:

- How LLMs generate text (token prediction, temperature, hallucination risk)
- Multi-agent systems and how agents coordinate
- Incident response fundamentals (the PICERL cycle or equivalent)
- Prompt injection and model risk

It works well as a capstone for a unit on AI in security operations, or as a recurring exercise where students run different scenarios as the course progresses. With twelve scenarios, a different one can anchor each week of a term without repetition.

### 10.2 Calibrating Agent Quality

If you find the agents are too accurate (students cannot find errors) or too incoherent (outputs are not useful), adjust:

- Model: smaller models hallucinate more; larger models are more coherent
- Temperature: increase slightly (to 0.4–0.5) to introduce more variability and more hallucination for critique exercises
- Objective: a vague objective produces vaguer agent outputs; a very specific objective produces tighter, harder-to-critique output
- RAG: disabling RAG grounding increases hallucination and can produce interesting “without grounding vs. with grounding” comparison exercises

> **Exercise idea:** Run the same scenario twice: once with RAG disabled, once with it enabled. Have students compare the agent outputs and identify specific claims that changed. This makes the value of retrieval augmentation concrete — and the Guided Walkthrough makes it sharper still, because the four retrieval steps disappear from the plan entirely when RAG is off.

### 10.3 Important Limitations to Communicate to Students

- This is a teaching and experimentation platform, not a production SOC tool.
- It does not isolate malware, connect to real SIEMs, or guarantee safe handling of live malicious content.
- Agent outputs should never be treated as authoritative security guidance.
- The local model has no access to current threat intelligence or live vulnerability databases.
- The prompt-injection scanning on uploaded documents is a regex-based teaching signal, not a security control.

### 10.4 Extending to New Topics

The lab can be extended to cover additional AI + security topics by:

- Adding KB files on prompt injection, adversarial ML, or supply chain attacks and running the crew against scenarios that reference those topics
- Uploading a document containing deliberate injection language on the RAG Control page, then showing the flagged chunk and tracing it into the assembled context in the Guided Walkthrough
- Running the crew with and without student notes to show how human framing changes AI output
- Assigning students to add their own scenario JSON and present it to the class
