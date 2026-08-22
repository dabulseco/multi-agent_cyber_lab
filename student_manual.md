# Student User Manual

**Multi-Agent Cybersecurity Lab**

*AI + Cybersecurity — Lab 09 Reference Guide*

Multi-Agent Cybersecurity Lab Environment  
Version 2.0 — August 2026

---

## 1. Introduction

This lab environment lets you investigate realistic cybersecurity incidents alongside a team of AI agents. Your job is not just to watch the agents work — it is to challenge their conclusions, compare them against the evidence, and produce a better, human-verified analysis.

The system runs entirely on your local machine. No data is sent to the cloud. All AI inference is performed by a locally installed language model through Ollama.

> **⚠️  Important:** The AI agents in this lab will sometimes overclaim, hallucinate indicators, or present inferences as facts. That is intentional. Your critical review is the point of the exercise.

### 1.1 What You Will Practice

- Reading and interpreting raw evidence artifacts (logs, emails, config files)
- Distinguishing confirmed facts from plausible inferences
- Evaluating AI-generated analysis for accuracy, gaps, and overconfidence
- Applying structured incident response thinking
- Writing a corrected human-authored incident summary

### 1.2 The Four AI Agents

Every run deploys four agents in sequence. Each has a distinct analytical lens:

| Agent | Role and Focus |
|---|---|
| SOC Analyst | Evidence triage and timeline reconstruction. Separates observed facts from inference. Identifies what the logs actually show. |
| Threat Hunter | Attacker behavior, plausible techniques, lateral movement, detection gaps, and alternative hypotheses. Considers what might have been missed. |
| Incident Responder | Containment, eradication, recovery, and operational prioritization. Focuses on what to do right now vs. later. |
| Security Reviewer | Uncertainty, overclaiming, teaching clarity. Flags where the other agents drew conclusions not supported by evidence. |

After the four agents complete their analysis, a final synthesis pass produces an integrated report structured as: Confirmed Facts, Likely Inferences, Remaining Unknowns, Recommended Immediate Actions, Recommended Longer-Term Controls, and Notes for Students.

### 1.3 Two Ways to Run a Scenario

The app offers two pages that run the same analysis at different speeds. Which one you use depends on what your instructor has assigned.

|   | Crew Run | Guided Walkthrough |
|---|---|---|
| What it does | Runs the whole investigation continuously, revealing each agent's findings as it finishes. | Breaks the same investigation into 11–15 steps and pauses after each one until you advance it. |
| What you see | Each agent's analysis and the final synthesis. | Everything Crew Run shows, plus the retrieval steps, the injection scan, and the exact prompt each agent receives — each with a what / how / why explanation. |
| How long | A single run, typically 30 seconds to several minutes. | As long as you take. You control the pace. |
| Use it for | Producing the export bundle for your submission. | Understanding how the system actually works. |

## 2. Getting Started

### 2.1 Before You Open the App

Check that the following are true before launching the lab:

- Ollama is installed on your machine.
- Ollama is running. Open a terminal and confirm it responds:

```bash
ollama list
```

- At least one chat model has been pulled, for example: ollama pull llama3.1:8b
- The embedding model has been pulled: ollama pull mxbai-embed-large — RAG indexing will not work without it.
- Your Python environment is active (ask your instructor which conda/venv to use).

### 2.2 Launching the App

In a terminal, navigate to the project directory and run:

```bash
streamlit run app/main.py
```

A browser window will open automatically at http://localhost:8501. If it does not, open that address manually.

### 2.3 Checking the Sidebar

Before doing anything else, look at the sidebar on the left side of every page:

- Ollama reachable: Yes — this must say Yes. If it says No, Ollama is not running.
- CrewAI available: Yes — if this says No, your environment is missing a component. The lab still works, but Crew Run will use a simpler fallback path. Tell your instructor.
- Local model — select the model you want the agents to use.
- Use RAG grounding — keep this checked for best results. It grounds the agents in course knowledge base content.
- Top-k retrieved chunks — how many knowledge base passages the agents receive per run. The default of 4 is appropriate for most scenarios.
- Run mode — leave on CrewAI (preferred) unless your instructor tells you otherwise.

## 3. Navigating the App

The app has six pages accessible from the navigation panel.

### 3.1 Home

The Home page lists all available scenarios with a brief summary of each. Read the scenario summaries here before selecting one. Each scenario includes a title and summary, learning goals that tell you what skills it develops, and an initial situation description — the starting point for your investigation.

You do not run anything from the Home page. It is a reference and orientation view.

### 3.2 Scenario Lab

This is where you read the scenario in detail and review evidence before running anything. Use it as your preparation step.

#### Scenario selector

Use the dropdown to choose a scenario. The left panel shows the scenario brief and simulation injects. Injects are time-stamped events that simulate new information arriving during the incident.

#### Evidence artifacts

The right panel shows the artifacts linked to the selected scenario. Select each artifact from the dropdown and read it before running the crew. Artifacts include CSV log files (authentication, egress, web access, cloud audit), plain text files (phishing emails, config notes, access reviews), and mixed evidence such as incident notes, chat transcripts, commit diffs, and vendor advisories.

At the bottom of the page, a structured evidence preview displays CSV artifacts as a formatted table so you can scan them without a spreadsheet tool.

> **📌  Best practice:** Write down your own initial hypotheses before running anything. What does the evidence suggest to you? Compare your read to what the agents produce.

### 3.3 Crew Run

This is the main execution page. Here you configure and launch the multi-agent analysis.

#### Mission / student objective

A default objective is pre-filled for each scenario. You may edit it to narrow or redirect the crew's focus — for example, to concentrate only on the timeline, or to specifically evaluate insider-threat vs. external-compromise hypotheses.

#### Student notes or hypotheses

This optional field injects your own notes into the crew's context. Use it to share a hypothesis you want the crew to consider, or to highlight a specific artifact. Example: “The suspicious email may have led to credential theft and external login attempts.”

#### Running the crew

Click Run multi-agent lab. Each agent's findings appear as soon as that agent finishes, rather than all at the end, so you can start reading while the rest of the run continues. Expect anywhere from 30 seconds to several minutes depending on your hardware and model.

#### Reading the results

After the run completes, the page shows the execution mode (whether CrewAI or the sequential fallback ran), the model used, the RAG context injected into the agents, each agent's individual analysis, and the final synthesis report.

> **🔎  How to read agent outputs:** Look for hedging language vs. confident claims. Does the agent say “the logs show” or “it is likely that”? The former is a fact claim; the latter is an inference. Flag every inference for verification.

#### Exporting your run

Use Export current run to save the full run bundle as a JSON file in the exports/ directory — you need this for your submission. You can also download the final report on its own, or two fuller documents: a workflow doc (every step with its technical detail) and an SOP report (the run written up as a narrative procedure). Both are available as markdown or HTML.

### 3.4 Guided Walkthrough

This page runs the same investigation as Crew Run, but stops after every step and explains what just happened. Use it when you want to understand the machinery rather than just the output.

#### How it works

Select a scenario and start the walkthrough. The system builds a plan of 11–15 steps and executes them one at a time, waiting for you to advance. With RAG grounding enabled you get 15 steps; with it disabled, the four retrieval steps disappear from the plan entirely — which is itself worth seeing once.

#### What each step shows

Every step presents a card answering three questions — what just happened, how it was done, and why the system does it this way — alongside the real technical detail captured from that step: the number of dimensions in the query embedding, which knowledge-base chunks matched, how many were flagged as suspicious, how many characters the assembled prompt ran to, and how long each model call took.

#### The steps you should slow down on

- Embed the retrieval query — where your question becomes a vector, and semantic search becomes possible.
- Search the knowledge base — which chunks matched, and from which source files.
- Scan retrieved content for injection signals — where untrusted retrieved text gets flagged before it reaches any agent.
- Assemble the RAG context block — the exact text every agent will see as background knowledge.
- Construct prompt for [agent] — the same evidence, framed four different ways, is what produces four different analyses.

> **📌  Best practice:** Compare the prompts built for two different agents at the same point in the run. The evidence is identical; only the role instruction differs. That difference is the entire mechanism behind “multi-agent” analysis, and seeing it directly is worth more than any description of it.

### 3.5 Asking Questions During a Run

Both Crew Run and Guided Walkthrough include a chat panel. You can ask a question at any point and the answer draws on the scenario evidence, the indexed knowledge base, and whatever the agents have found so far.

Answers separate two things explicitly: what the scenario evidence supports, and what is general background knowledge. If the evidence does not cover something you asked about this incident, the answer will say so rather than inventing a detail.

> **⚠️  Remember:** The chat panel is another model output, not an authority. It is grounded in the evidence, but it can still be wrong — hold it to the same standard you hold the agents. Your questions are also logged for your instructor, which is a feature: it shows where the material needs more attention.

### 3.6 RAG Control

RAG stands for Retrieval-Augmented Generation. It is the mechanism that grounds the AI agents in factual course material rather than relying solely on what the model memorized during training.

When RAG is enabled, the agents receive relevant passages from the knowledge base before generating their analysis. This reduces hallucination and connects the agents' outputs to material you have studied.

#### Building the index

The first time you use the lab, you must build or refresh the RAG index. On the RAG Control page, check Include built-in KB and labs, optionally upload additional files (text, markdown, PDF, Word, CSV, JSON, Python, or log files), then click Build / refresh index. You will see a count of documents and chunks indexed.

> **ℹ️  Note:** The index is stored locally and persists between sessions. You only need to rebuild it if you add new files, or if you were given a project folder whose index was built on someone else's machine.

#### Testing retrieval

Use the retrieval test at the bottom of the page to verify the index is working. Type a query — for example, “prompt injection defense in AI systems” — and click Retrieve evidence to see which knowledge-base passages would be provided to the agents.

#### Injection flagging

Uploaded and indexed content is scanned for language that resembles a prompt-injection attempt — phrases like “ignore previous instructions.” Flagged chunks are marked in the retrieval results and labelled as untrusted in the context handed to the agents.

Try this deliberately: upload a short document containing an instruction aimed at the AI, index it, and watch where the flag appears. This is a teaching signal rather than a security control, and seeing its limits is part of the lesson.

### 3.7 Instructor Dashboard

This page is primarily for your instructor, but you can use it for your own reflection. It shows suggested grading prompts that reveal what analytical quality is being evaluated, a four-question reflection structure that mirrors the lab deliverables, the runs you have completed this session, and a log of questions asked across all sessions.

## 4. Recommended Step-by-Step Workflow

Follow this sequence for each lab session:

| Step | Action |
|---|---|
| 1. Launch | Start Ollama, then run: streamlit run app/main.py |
| 2. Check sidebar | Confirm Ollama reachable: Yes and CrewAI available: Yes. Select your model. Enable RAG grounding. |
| 3. Build index | Go to RAG Control. Click Build / refresh index. |
| 4. Read the scenario | Go to Scenario Lab. Read the scenario brief, all injects, and every artifact. |
| 5. Form your hypothesis | Before running anything, write down what you think happened based on the evidence. |
| 6. Walk the pipeline | If assigned, run the Guided Walkthrough and read every step card. Ask questions as they occur to you. |
| 7. Set objective | Go to Crew Run. Edit the mission objective if needed. Add your hypothesis in student notes. |
| 8. Run the crew | Click Run multi-agent lab. Read each agent's output as it appears. |
| 9. Review RAG context | Expand the RAG context panel. Note which knowledge-base passages were injected, and whether any were flagged. |
| 10. Audit agent outputs | Read each agent's output. Mark where they cite evidence vs. infer. Flag overclaiming. |
| 11. Read the synthesis | Identify what it got right, what it missed, and what remains uncertain. |
| 12. Export | Export the run bundle and download the report. |
| 13. Write your critique | Complete the lab reflection. See Section 5 for required deliverables. |

## 5. Lab Deliverables

For Lab 09, you must submit three items.

### 5.1 Exported Incident Report

The JSON export from Crew Run > Export current run. This is the raw output of the multi-agent run and proves you executed the lab. File name format: <scenario_id>_<timestamp>.json.

### 5.2 One-Page Critique

A written analysis answering all four of the following questions:

1. Which agent findings were strongly supported by the evidence? Cite specific log entries or artifact data.
2. Which findings were weakly supported or inferred without adequate evidence? Give examples.
3. Which agent was most cautious in separating facts from inference, and why do you think so?
4. What would you verify next as a human analyst, and what evidence would you look for?

> **📊  Grading note:** Vague answers like “the agents did well” will not receive credit. Your critique must cite specific lines from agent outputs and connect them to specific artifacts.

### 5.3 Corrected Human Summary

A corrected version of the final synthesis, written by you, that:

- Removes unsupported inferences without evidence citations
- Adds appropriate uncertainty language where the evidence is ambiguous
- Proposes at least two verification steps the agents did not mention
- Is written in plain, professional incident-response language (not AI prose)

## 6. Available Scenarios

The lab includes 12 scenarios. Your instructor will tell you which to run. Each has three timed injects that deliver new information partway through the incident.

| Scenario | In one line |
|---|---|
| Possible Insider Data Exfiltration | Escalating outbound transfers from a finance host, using a broad service account. |
| Credential Theft and Suspicious VPN Access | Mailbox trouble after a phishing email, then a VPN login from a foreign IP. |
| Insider Sabotage by a Departing Administrator | Backup jobs deleted during the gap before a departing admin's access was revoked. |
| Ransomware Deployment and Extortion | File servers unreachable overnight, a ransom note, and odd backup activity. |
| Cloud Storage Bucket Misconfiguration | A storage bucket briefly public, with anonymous requests in the audit log. |
| Leaked Cloud API Key in a Public Repository | A live cloud API key committed to a public repo, followed by billing anomalies. |
| Business Email Compromise and Invoice Fraud | A wire sent to new bank details on the word of a spoofed vendor email. |
| Software Supply Chain Compromise | A dependency update pulling a package from a compromised maintainer account. |
| Traffic Spike: Possible DDoS or Legitimate Surge | A traffic surge that could be an attack or a legitimate rush. |
| BYOD Smishing and Attempted App Sideload | A smishing text to a personal phone, then a blocked app sideload attempt. |
| OT/ICS Network Segmentation Exposure | A leftover firewall rule exposing a plant historian server to corporate IT for 11 days. |
| Internal AI Assistant Prompt-Injection Data Leak | A support chatbot talked into leaking internal data by a poisoned ticket. |

### 6.1 Possible Insider Data Exfiltration

Outbound traffic from a finance host increased sharply late in the day, and a service account appears to retain excessive permissions.

Learning goals for this scenario:

- Analyze egress anomalies
- Compare insider-threat and external-compromise hypotheses
- Propose evidence-driven next steps instead of assuming motive

Available artifacts:

- egress_exfiltration.csv
- fileshare_access_review.txt

> **Key tension in this scenario:** The manager asks whether an employee intentionally exported records. Your job is to evaluate whether the evidence supports intentional exfiltration, accidental transfer, or an external compromise using a service account — and what additional evidence would distinguish between these.

### 6.2 Credential Theft and Suspicious VPN Access

A staff member reports mailbox access issues shortly after receiving a password-reset email. Security operations sees unusual VPN activity.

Learning goals for this scenario:

- Distinguish phishing indicators from confirmed account compromise
- Correlate email, VPN, and file access artifacts
- Separate containment actions from longer-term control improvements

Available artifacts:

- credential_reset_email.txt
- web_log_credential_theft.csv
- auth_log_ransomware_lab.csv
- vpn_gateway_notes.txt
- fileshare_access_review.txt

> **Key tension in this scenario:** A suspicious email and a foreign VPN login are both present, but neither proves the other. Decide what the evidence actually establishes about credential capture, and what you would need to confirm that anything was accessed.

### 6.3 Insider Sabotage by a Departing Administrator

A former systems administrator's access was not revoked promptly after resignation, and backup jobs were deleted using a newly created service account during the gap.

Learning goals for this scenario:

- Identify privileged-access review and offboarding process gaps
- Distinguish malicious sabotage from an honest configuration mistake
- Prioritize access revocation as the primary immediate control

Available artifacts:

- offboarding_notes.txt
- auth_log_sabotage.csv

> **Key tension in this scenario:** Access was not revoked on time and backup jobs were deleted. Separate the process failure, which the evidence clearly shows, from the question of intent, which it may not.

### 6.4 Ransomware Deployment and Extortion

Multiple file servers become unreachable overnight and a ransom note appears on shared drives. Backup jobs also show unexpected activity.

Learning goals for this scenario:

- Sequence initial access, lateral movement, and encryption impact from log evidence
- Recognize double-extortion (data theft plus encryption) versus encryption alone
- Separate immediate containment actions from root-cause investigation

Available artifacts:

- auth_log_ransomware_lab.csv
- ransom_note.txt

> **Key tension in this scenario:** The ransom note claims data was stolen as well as encrypted. A claim by an attacker is not evidence. Determine which parts of the attack sequence the logs actually support.

### 6.5 Cloud Storage Bucket Misconfiguration

A routine review finds that a cloud storage bucket was briefly configured for public read access, and the audit log shows anonymous requests during that window.

Learning goals for this scenario:

- Apply the shared-responsibility model to a cloud misconfiguration
- Distinguish evidence of possible exposure from evidence of confirmed data exfiltration
- Recommend proportionate response given genuinely incomplete evidence

Available artifacts:

- cloud_audit_log.csv
- bucket_policy_notes.txt

> **Key tension in this scenario:** Anonymous requests arrived while a bucket was public. That establishes possible exposure — decide whether anything in the evidence can establish confirmed exfiltration, and say so plainly if it cannot.

### 6.6 Leaked Cloud API Key in a Public Repository

An intern accidentally commits a live cloud API key to a public GitHub repository, and anomalous compute usage appears in the billing dashboard shortly after.

Learning goals for this scenario:

- Apply secret-scanning and credential-hygiene practices to a real leak
- Assess blast radius by reasoning about what the leaked key could actually access
- Treat rapid rotation as the primary response action rather than only cleanup

Available artifacts:

- github_commit_diff.txt
- cloud_billing_anomaly.csv
- key_revocation_timeline.txt

> **Key tension in this scenario:** A live key reached a public repository and unusual compute usage followed. Work out the blast radius — what could this key actually reach — and order the response actions by what stops the damage first.

### 6.7 Business Email Compromise and Invoice Fraud

Accounts payable processes a wire transfer to updated bank details after receiving an urgent email from a familiar vendor contact, only to have the real vendor later ask why an invoice remains unpaid.

Learning goals for this scenario:

- Analyze sender domains and headers for lookalike-domain spoofing
- Identify social-engineering pressure tactics such as urgency and authority
- Separate the human process failure from the technical delivery mechanism

Available artifacts:

- bec_spoofed_email.txt
- wire_transfer_request.txt

> **Key tension in this scenario:** The email is a technical artifact you can analyze, but the money moved because of a process. Identify both the delivery mechanism and the control failure that let a payment change proceed.

### 6.8 Software Supply Chain Compromise

A routine dependency update pulled in a package version published from a compromised maintainer account, and the vendor has now disclosed the incident.

Learning goals for this scenario:

- Reason about trust boundaries introduced by transitive dependencies
- Distinguish a vulnerable dependency being present from confirmed exploitation in this environment
- Explain why exposure and compromise require different evidence and different responses

Available artifacts:

- dependency_diff.txt
- build_log_excerpt.txt
- vendor_disclosure_email.txt

> **Key tension in this scenario:** A compromised package being present in your build is exposure. Evidence of it executing in your environment is compromise. Decide which one this evidence supports.

### 6.9 Traffic Spike: Possible DDoS or Legitimate Surge

The admissions website begins returning intermittent errors during a sudden traffic increase, and the on-call team must decide whether this is an attack or a legitimate surge.

Learning goals for this scenario:

- Evaluate whether traffic evidence supports an attack hypothesis or a benign explanation
- Make service-prioritization decisions under time pressure with incomplete certainty
- Practice stating that evidence is inconclusive rather than defaulting to a confident conclusion

Available artifacts:

- web_log_traffic_spike.csv
- waf_loadbalancer_notes.txt

> **Key tension in this scenario:** The traffic pattern fits both an attack and a legitimate surge, and the on-call decision must be made anyway. Separate what you decide operationally from what you claim causally.

### 6.10 BYOD Smishing and Attempted App Sideload

An employee's personal phone receives a smishing message impersonating IT, and shortly after, the device attempts to sideload a suspicious app that is blocked by mobile device management.

Learning goals for this scenario:

- Assess BYOD risk surface and the limits of MDM telemetry on personal devices
- Recognize privacy and legal boundaries when investigating a personal device
- Work with weaker evidence quality than a fully managed endpoint provides

Available artifacts:

- mdm_enrollment_log.csv
- smishing_message.txt
- app_permissions_list.txt

> **Key tension in this scenario:** The device is personal, so the telemetry is thinner than on a managed endpoint and the investigation has privacy limits. Work out what you can legitimately establish given both constraints.

### 6.11 OT/ICS Network Segmentation Exposure

A leftover firewall rule from a vendor maintenance visit left a path open from the corporate IT network into the plant's OT historian server for eleven days.

Learning goals for this scenario:

- Identify IT/OT segmentation failures and their root causes
- Weigh safety-versus-security tradeoffs specific to operational technology
- Distinguish confirmed unauthorized control actions from unexplained but benign access

Available artifacts:

- ot_network_flow_notes.txt
- vendor_security_advisory.txt
- engineer_incident_notes.txt

> **Key tension in this scenario:** An exposure path was open for eleven days. In an OT environment the usual containment reflex may be unsafe — weigh process safety alongside security, and distinguish unexplained access from confirmed unauthorized control actions.

### 6.12 Internal AI Assistant Prompt-Injection Data Leak

An internal support chatbot, grounded via retrieval over the support ticket queue, is manipulated by an instruction embedded in a submitted ticket into disclosing an internal contact list and account recovery codes.

Learning goals for this scenario:

- Recognize prompt injection carried through retrieved content rather than direct user input
- Evaluate whether an AI system properly separated trusted instructions from untrusted evidence
- Reason about another AI system's design flaws as a third-party reviewer

Available artifacts:

- poisoned_support_ticket.txt
- chatbot_transcript.txt
- it_incident_notes.txt

> **Key tension in this scenario:** An AI system followed instructions hidden in content it retrieved. You are reviewing another AI's design failure — while using an AI system with the same class of weakness.

## 7. Understanding Agent Limitations

These agents are educational tools, not production security systems. Understanding their failure modes is itself a learning objective.

### 7.1 Common Failure Modes

| Failure mode | What to look for |
|---|---|
| Hallucinated indicators | Agent cites an IP address, hash, or filename not present in any artifact. Always cross-check against the actual logs. |
| Unjustified certainty | Agent says “the attacker used X” when the log only shows an anomaly. Look for missing hedging language. |
| Overclaiming scope | Agent concludes regulated data was exfiltrated when no data classification appears in the artifacts. |
| Invented remediation | Agent recommends tools or procedures not mentioned in the knowledge base or artifacts. |
| Motive assumption | Agent assumes intent (malicious, insider) without evidence of intent in the logs. |

### 7.2 What RAG Does and Does Not Fix

RAG grounding reduces hallucination by giving the agents factual course material to draw on. However, it does not eliminate hallucination. An agent may still misinterpret a retrieved passage, selectively apply retrieval context to support a prior claim, or fail to retrieve the most relevant passage if the query embedding did not match well.

Always verify by expanding the RAG context panel and checking whether the agents actually used the retrieved material, and whether they used it accurately. The Guided Walkthrough makes this easier: it shows you the retrieved chunks and the assembled context as separate, inspectable steps.

### 7.3 Retrieved Content Is Not Trusted Content

Anything retrieved from the knowledge base is evidence to be analyzed, never instructions to be followed. The system scans retrieved chunks for injection-like language and labels matches as untrusted before they reach any agent.

That scan is a regular-expression pattern match. It catches obvious attempts and will miss subtle ones — which is precisely why a human reviewer stays in the loop. Treat a clean scan as no evidence of a problem, not as evidence of no problem.

### 7.4 Temperature and Determinism

The agents run at a low temperature setting (0.2, and 0.15 for the final synthesis), which makes outputs more consistent and less creative. This is intentional for an educational setting: you should see similar outputs on repeat runs, making comparison meaningful. Small differences will still appear between runs.

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| Ollama reachable: No | Open a terminal and run: ollama serve. Wait a few seconds, then refresh the app. |
| CrewAI available: No | Your Python environment is missing crewai, most often because the app was launched from the wrong environment. The sidebar shows which interpreter is running. Tell your instructor. |
| No model found in sidebar | Run: ollama pull llama3.1:8b (or another model). Then refresh the app. |
| Indexing fails with an embedding error | Run: ollama pull mxbai-embed-large, then rebuild the index. |
| A run produces no output | The model may have timed out. Try a smaller model or a simpler objective. |
| A run fails with a 403 or subscription error | You selected a :cloud model your Ollama account does not cover. Pick a local model in the sidebar. |
| RAG index returns no results | Go to RAG Control and click Build / refresh index before running. |
| Retrieved chunks show unfamiliar file paths | The index was built on a different machine. Rebuild it. |
| Export file not found | Check the exports/ directory in the project root. The file is named <scenario_id>_<timestamp>.json. |

## 9. Quick Reference

### Sidebar Controls

| Control | Purpose |
|---|---|
| Ollama reachable | Health check. Must say Yes before running. |
| CrewAI available | Whether full orchestration is available. No means Crew Run uses the fallback path. |
| Local model | Which LLM the agents use for inference. |
| Use RAG grounding | Enables knowledge-base retrieval to ground agent outputs. |
| Top-k retrieved chunks | Number of KB passages injected per run (default: 4). |
| Run mode | CrewAI preferred (full orchestration) or sequential fallback. |

### Key Questions for Your Critique

- Did the agent cite the artifact, or did it invent the claim?
- Is this a fact (observed in logs) or an inference (interpreted from logs)?
- What evidence would confirm or refute this finding?
- Which agent was most and least cautious?
- What did all four agents miss?
