"""Regenerate student_manual.docx at v2.0.

The scenario catalogue is generated from data/incidents/*.json so it cannot drift
from the shipped scenarios again.
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

ORDER = [
    "insider_exfiltration", "credential_theft_vpn", "insider_sabotage",
    "ransomware_deployment_extortion", "cloud_storage_misconfiguration",
    "leaked_api_key_repo", "bec_invoice_fraud", "supply_chain_compromise",
    "availability_incident_ddos", "mobile_byod_compromise", "ot_ics_exposure",
    "ai_assistant_prompt_injection_leak",
]

# The analytical tension each scenario is built around — what the student has to
# resolve, stated without giving away an answer.
TENSION = {
    "insider_exfiltration":
        "The manager asks whether an employee intentionally exported records. Your job is to evaluate whether the "
        "evidence supports intentional exfiltration, accidental transfer, or an external compromise using a service "
        "account — and what additional evidence would distinguish between these.",
    "credential_theft_vpn":
        "A suspicious email and a foreign VPN login are both present, but neither proves the other. Decide what the "
        "evidence actually establishes about credential capture, and what you would need to confirm that anything "
        "was accessed.",
    "insider_sabotage":
        "Access was not revoked on time and backup jobs were deleted. Separate the process failure, which the "
        "evidence clearly shows, from the question of intent, which it may not.",
    "ransomware_deployment_extortion":
        "The ransom note claims data was stolen as well as encrypted. A claim by an attacker is not evidence. "
        "Determine which parts of the attack sequence the logs actually support.",
    "cloud_storage_misconfiguration":
        "Anonymous requests arrived while a bucket was public. That establishes possible exposure — decide whether "
        "anything in the evidence can establish confirmed exfiltration, and say so plainly if it cannot.",
    "leaked_api_key_repo":
        "A live key reached a public repository and unusual compute usage followed. Work out the blast radius — "
        "what could this key actually reach — and order the response actions by what stops the damage first.",
    "bec_invoice_fraud":
        "The email is a technical artifact you can analyze, but the money moved because of a process. Identify both "
        "the delivery mechanism and the control failure that let a payment change proceed.",
    "supply_chain_compromise":
        "A compromised package being present in your build is exposure. Evidence of it executing in your "
        "environment is compromise. Decide which one this evidence supports.",
    "availability_incident_ddos":
        "The traffic pattern fits both an attack and a legitimate surge, and the on-call decision must be made "
        "anyway. Separate what you decide operationally from what you claim causally.",
    "mobile_byod_compromise":
        "The device is personal, so the telemetry is thinner than on a managed endpoint and the investigation has "
        "privacy limits. Work out what you can legitimately establish given both constraints.",
    "ot_ics_exposure":
        "An exposure path was open for eleven days. In an OT environment the usual containment reflex may be unsafe "
        "— weigh process safety alongside security, and distinguish unexplained access from confirmed unauthorized "
        "control actions.",
    "ai_assistant_prompt_injection_leak":
        "An AI system followed instructions hidden in content it retrieved. You are reviewing another AI's design "
        "failure — while using an AI system with the same class of weakness.",
}

# One-line catalogue descriptions. Written out rather than derived from the summary
# text, which does not truncate cleanly.
ONELINE = {
    "insider_exfiltration": "Escalating outbound transfers from a finance host, using a broad service account.",
    "credential_theft_vpn": "Mailbox trouble after a phishing email, then a VPN login from a foreign IP.",
    "insider_sabotage": "Backup jobs deleted during the gap before a departing admin's access was revoked.",
    "ransomware_deployment_extortion": "File servers unreachable overnight, a ransom note, and odd backup activity.",
    "cloud_storage_misconfiguration": "A storage bucket briefly public, with anonymous requests in the audit log.",
    "leaked_api_key_repo": "A live cloud API key committed to a public repo, followed by billing anomalies.",
    "bec_invoice_fraud": "A wire sent to new bank details on the word of a spoofed vendor email.",
    "supply_chain_compromise": "A dependency update pulling a package from a compromised maintainer account.",
    "availability_incident_ddos": "A traffic surge that could be an attack or a legitimate rush.",
    "mobile_byod_compromise": "A smishing text to a personal phone, then a blocked app sideload attempt.",
    "ot_ics_exposure": "A leftover firewall rule exposing a plant historian server to corporate IT for 11 days.",
    "ai_assistant_prompt_injection_leak": "A support chatbot talked into leaking internal data by a poisoned ticket.",
}

doc = open_template(str(ROOT / "student_manual.docx"))

title_block(
    doc,
    "Student User Manual",
    "Multi-Agent Cybersecurity Lab",
    "AI + Cybersecurity — Lab 09 Reference Guide",
    "Multi-Agent Cybersecurity Lab Environment",
    "Version 2.0 — August 2026",
)

# ----------------------------------------------------------- 1. Introduction
h1(doc, "1. Introduction")
body(doc, "This lab environment lets you investigate realistic cybersecurity incidents alongside a team of AI "
          "agents. Your job is not just to watch the agents work — it is to challenge their conclusions, compare "
          "them against the evidence, and produce a better, human-verified analysis.")
body(doc, "The system runs entirely on your local machine. No data is sent to the cloud. All AI inference is "
          "performed by a locally installed language model through Ollama.")
callout(doc, "⚠️  Important:",
        "The AI agents in this lab will sometimes overclaim, hallucinate indicators, or present inferences as "
        "facts. That is intentional. Your critical review is the point of the exercise.")

h2(doc, "1.1 What You Will Practice")
bullets(doc, [
    "Reading and interpreting raw evidence artifacts (logs, emails, config files)",
    "Distinguishing confirmed facts from plausible inferences",
    "Evaluating AI-generated analysis for accuracy, gaps, and overconfidence",
    "Applying structured incident response thinking",
    "Writing a corrected human-authored incident summary",
])

h2(doc, "1.2 The Four AI Agents")
body(doc, "Every run deploys four agents in sequence. Each has a distinct analytical lens:")
table(doc, ["Agent", "Role and Focus"], [
    ["SOC Analyst", "Evidence triage and timeline reconstruction. Separates observed facts from inference. "
                    "Identifies what the logs actually show."],
    ["Threat Hunter", "Attacker behavior, plausible techniques, lateral movement, detection gaps, and alternative "
                      "hypotheses. Considers what might have been missed."],
    ["Incident Responder", "Containment, eradication, recovery, and operational prioritization. Focuses on what to "
                           "do right now vs. later."],
    ["Security Reviewer", "Uncertainty, overclaiming, teaching clarity. Flags where the other agents drew "
                          "conclusions not supported by evidence."],
])
body(doc, "After the four agents complete their analysis, a final synthesis pass produces an integrated report "
          "structured as: Confirmed Facts, Likely Inferences, Remaining Unknowns, Recommended Immediate Actions, "
          "Recommended Longer-Term Controls, and Notes for Students.")

h2(doc, "1.3 Two Ways to Run a Scenario")
body(doc, "The app offers two pages that run the same analysis at different speeds. Which one you use depends on "
          "what your instructor has assigned.")
table(doc, ["", "Crew Run", "Guided Walkthrough"], [
    ["What it does", "Runs the whole investigation continuously, revealing each agent's findings as it finishes.",
     "Breaks the same investigation into 11–17 steps and pauses after each one until you advance it."],
    ["What you see", "Each agent's analysis and the final synthesis.",
     "Everything Crew Run shows, plus the retrieval steps, the injection scan, and the exact prompt each agent "
     "receives — each with a what / how / why explanation."],
    ["How long", "A single run, typically 30 seconds to several minutes.",
     "As long as you take. You control the pace."],
    ["Use it for", "Producing the export bundle for your submission.",
     "Understanding how the system actually works."],
])

# --------------------------------------------------------- 2. Getting Started
h1(doc, "2. Getting Started")
h2(doc, "2.1 Before You Open the App")
body(doc, "Check that the following are true before launching the lab:")
bullets(doc, [
    "Ollama is installed on your machine.",
    "Ollama is running. Open a terminal and confirm it responds:",
])
terminal(doc, "ollama list")
bullets(doc, [
    "At least one chat model has been pulled, for example: ollama pull llama3.1:8b",
    "The embedding model has been pulled: ollama pull mxbai-embed-large — RAG indexing will not work without it.",
    "Your Python environment is active (ask your instructor which conda/venv to use).",
])

h2(doc, "2.2 Launching the App")
body(doc, "In a terminal, navigate to the project directory and run:")
terminal(doc, "streamlit run app/main.py")
body(doc, "A browser window will open automatically at http://localhost:8501. If it does not, open that address "
          "manually.")

h2(doc, "2.3 Checking the Sidebar")
body(doc, "Before doing anything else, look at the sidebar on the left side of every page:")
bullets(doc, [
    "Ollama reachable: Yes — this must say Yes. If it says No, Ollama is not running.",
    "CrewAI available: Yes — if this says No, your environment is missing a component. The lab still works, but "
    "Crew Run will use a simpler fallback path. Tell your instructor.",
    "Local model — select the model you want the agents to use.",
    "Use RAG grounding — keep this checked for best results. It grounds the agents in course knowledge base "
    "content.",
    "Top-k retrieved chunks — how many knowledge base passages the agents receive per run. The default of 4 is "
    "appropriate for most scenarios.",
    "Run mode — leave on CrewAI (preferred) unless your instructor tells you otherwise.",
])

# ------------------------------------------------------- 3. Navigating the App
h1(doc, "3. Navigating the App")
body(doc, "The app has six pages accessible from the navigation panel.")

h2(doc, "3.1 Home")
body(doc, "The Home page lists all available scenarios with a brief summary of each. Read the scenario summaries "
          "here before selecting one. Each scenario includes a title and summary, learning goals that tell you what "
          "skills it develops, and an initial situation description — the starting point for your investigation.")
body(doc, "You do not run anything from the Home page. It is a reference and orientation view.")

h2(doc, "3.2 Scenario Lab")
body(doc, "This is where you read the scenario in detail and review evidence before running anything. Use it as "
          "your preparation step.")
h3(doc, "Scenario selector")
body(doc, "Use the dropdown to choose a scenario. The left panel shows the scenario brief and simulation injects. "
          "Injects are time-stamped events that simulate new information arriving during the incident.")
h3(doc, "Evidence artifacts")
body(doc, "The right panel shows the artifacts linked to the selected scenario. Select each artifact from the "
          "dropdown and read it before running the crew. Artifacts include CSV log files (authentication, egress, "
          "web access, cloud audit), plain text files (phishing emails, config notes, access reviews), and mixed "
          "evidence such as incident notes, chat transcripts, commit diffs, and vendor advisories.")
body(doc, "At the bottom of the page, a structured evidence preview displays CSV artifacts as a formatted table so "
          "you can scan them without a spreadsheet tool.")
callout(doc, "📌  Best practice:",
        "Write down your own initial hypotheses before running anything. What does the evidence suggest to you? "
        "Compare your read to what the agents produce.")

h2(doc, "3.3 Crew Run")
body(doc, "This is the main execution page. Here you configure and launch the multi-agent analysis.")
h3(doc, "Mission / student objective")
body(doc, "A default objective is pre-filled for each scenario. You may edit it to narrow or redirect the crew's "
          "focus — for example, to concentrate only on the timeline, or to specifically evaluate insider-threat vs. "
          "external-compromise hypotheses.")
h3(doc, "Student notes or hypotheses")
body(doc, "This optional field injects your own notes into the crew's context. Use it to share a hypothesis you "
          "want the crew to consider, or to highlight a specific artifact. Example: “The suspicious email may have "
          "led to credential theft and external login attempts.”")
h3(doc, "Running the crew")
body(doc, "Click Run multi-agent lab. Each agent's findings appear as soon as that agent finishes, rather than all "
          "at the end, so you can start reading while the rest of the run continues. Expect anywhere from 30 "
          "seconds to several minutes depending on your hardware and model.")
h3(doc, "Reading the results")
body(doc, "After the run completes, the page shows the execution mode (whether CrewAI or the sequential fallback "
          "ran), the model used, the RAG context injected into the agents, each agent's individual analysis, and "
          "the final synthesis report.")
callout(doc, "🔎  How to read agent outputs:",
        "Look for hedging language vs. confident claims. Does the agent say “the logs show” or “it is likely "
        "that”? The former is a fact claim; the latter is an inference. Flag every inference for verification.")
h3(doc, "Exporting your run")
body(doc, "Use Export current run to save the full run bundle as a JSON file in the exports/ directory — you need "
          "this for your submission. You can also download the final report on its own, or two fuller documents: a "
          "workflow doc (every step with its technical detail) and an SOP report (the run written up as a narrative "
          "procedure). Both are available as markdown or HTML.")

h2(doc, "3.4 Guided Walkthrough")
body(doc, "This page runs the same investigation as Crew Run, but stops after every step and explains what just "
          "happened. Use it when you want to understand the machinery rather than just the output.")
h3(doc, "How it works")
body(doc, "Select a scenario and start the walkthrough. The system builds a plan of 11–17 steps and executes "
          "them one at a time, waiting for you to advance. A scenario with log evidence and RAG enabled gives you "
          "17; turn RAG off and the four retrieval steps disappear from the plan entirely — which is itself worth "
          "seeing once. Scenarios with no spreadsheet-style evidence skip the two measurement steps.")
h3(doc, "What each step shows")
body(doc, "Every step presents a card answering three questions — what just happened, how it was done, and why the "
          "system does it this way — alongside the real technical detail captured from that step: the number of "
          "dimensions in the query embedding, which knowledge-base chunks matched, how many were flagged as "
          "suspicious, how many characters the assembled prompt ran to, and how long each model call took.")
h3(doc, "The steps you should slow down on")
bullets(doc, [
    "Compute deterministic metrics — where the tool measures the logs instead of describing them, and shows you "
    "the exact code it ran.",
    "Embed the retrieval query — where your question becomes a vector, and semantic search becomes possible.",
    "Search the knowledge base — which chunks matched, and from which source files.",
    "Scan retrieved content for injection signals — where untrusted retrieved text gets flagged before it reaches "
    "any agent.",
    "Assemble the RAG context block — the exact text every agent will see as background knowledge.",
    "Construct prompt for [agent] — the same evidence, framed four different ways, is what produces four different "
    "analyses.",
])
callout(doc, "📌  Best practice:",
        "Compare the prompts built for two different agents at the same point in the run. The evidence is "
        "identical; only the role instruction differs. That difference is the entire mechanism behind “multi-agent” "
        "analysis, and seeing it directly is worth more than any description of it.")

h2(doc, "3.5 Measured Evidence")
body(doc, "Where a scenario includes spreadsheet-style log evidence, the tool computes real measurements over it "
          "before any agent reasons about it — how evenly spaced the events were, what share fell outside business "
          "hours, failure rates, how much the transfer sizes escalated, how many distinct sources appear, and "
          "whether one account showed up from two places in an implausibly short time.")
body(doc, "These numbers are handed to every agent along with the evidence, and they are shown to you with the "
          "exact code that produced them. Nothing about them is generated by a language model: the same file run "
          "through the same code gives the same answer every time.")
callout(doc, "🔎  What to do with them:",
        "Check every quantitative claim an agent makes against the measured value. An agent that says traffic "
        "arrived at machine-like intervals when the measured coefficient of variation says otherwise has made a "
        "specific, citable error — and that is exactly the kind of finding your critique is graded on.")
body(doc, "Two cautions. A measurement over a handful of rows describes those rows and not much else; the tool "
          "says so when the sample is thin, and you should repeat the caveat rather than quoting the bare number. "
          "And a measurement is not a finding until you have interpreted it — perfectly regular timing might be an "
          "automated attacker, or it might be a billing system sampling on a fixed schedule.")

h2(doc, "3.6 Asking Questions During a Run")
body(doc, "Both Crew Run and Guided Walkthrough include a chat panel. You can ask a question at any point and the "
          "answer draws on the scenario evidence, the indexed knowledge base, and whatever the agents have found so "
          "far.")
body(doc, "Answers separate two things explicitly: what the scenario evidence supports, and what is general "
          "background knowledge. If the evidence does not cover something you asked about this incident, the answer "
          "will say so rather than inventing a detail.")
callout(doc, "⚠️  Remember:",
        "The chat panel is another model output, not an authority. It is grounded in the evidence, but it can "
        "still be wrong — hold it to the same standard you hold the agents. Your questions are also logged for "
        "your instructor, which is a feature: it shows where the material needs more attention.")

h2(doc, "3.7 RAG Control")
body(doc, "RAG stands for Retrieval-Augmented Generation. It is the mechanism that grounds the AI agents in "
          "factual course material rather than relying solely on what the model memorized during training.")
body(doc, "When RAG is enabled, the agents receive relevant passages from the knowledge base before generating "
          "their analysis. This reduces hallucination and connects the agents' outputs to material you have "
          "studied.")
h3(doc, "Building the index")
body(doc, "The first time you use the lab, you must build or refresh the RAG index. On the RAG Control page, check "
          "Include built-in KB and labs, optionally upload additional files (text, markdown, PDF, Word, CSV, JSON, "
          "Python, or log files), then click Build / refresh index. You will see a count of documents and chunks "
          "indexed.")
callout(doc, "ℹ️  Note:",
        "The index is stored locally and persists between sessions. You only need to rebuild it if you add new "
        "files, or if you were given a project folder whose index was built on someone else's machine.")
h3(doc, "Testing retrieval")
body(doc, "Use the retrieval test at the bottom of the page to verify the index is working. Type a query — for "
          "example, “prompt injection defense in AI systems” — and click Retrieve evidence to see which "
          "knowledge-base passages would be provided to the agents.")
h3(doc, "Injection flagging")
body(doc, "Uploaded and indexed content is scanned for language that resembles a prompt-injection attempt — "
          "phrases like “ignore previous instructions.” Flagged chunks are marked in the retrieval results and "
          "labelled as untrusted in the context handed to the agents.")
body(doc, "Try this deliberately: upload a short document containing an instruction aimed at the AI, index it, and "
          "watch where the flag appears. This is a teaching signal rather than a security control, and seeing its "
          "limits is part of the lesson.")

h2(doc, "3.8 Instructor Dashboard")
body(doc, "This page is primarily for your instructor, but you can use it for your own reflection. It shows "
          "suggested grading prompts that reveal what analytical quality is being evaluated, a four-question "
          "reflection structure that mirrors the lab deliverables, the runs you have completed this session, and a "
          "log of questions asked across all sessions.")

# ------------------------------------------- 4. Recommended Step-by-Step Workflow
h1(doc, "4. Recommended Step-by-Step Workflow")
body(doc, "Follow this sequence for each lab session:")
table(doc, ["Step", "Action"], [
    ["1. Launch", "Start Ollama, then run: streamlit run app/main.py"],
    ["2. Check sidebar", "Confirm Ollama reachable: Yes and CrewAI available: Yes. Select your model. Enable RAG "
                         "grounding."],
    ["3. Build index", "Go to RAG Control. Click Build / refresh index."],
    ["4. Read the scenario", "Go to Scenario Lab. Read the scenario brief, all injects, and every artifact."],
    ["5. Form your hypothesis", "Before running anything, write down what you think happened based on the "
                                "evidence."],
    ["6. Walk the pipeline", "If assigned, run the Guided Walkthrough and read every step card. Ask questions as "
                             "they occur to you."],
    ["7. Set objective", "Go to Crew Run. Edit the mission objective if needed. Add your hypothesis in student "
                         "notes."],
    ["8. Run the crew", "Click Run multi-agent lab. Read each agent's output as it appears."],
    ["9. Review RAG context", "Expand the RAG context panel. Note which knowledge-base passages were injected, and "
                              "whether any were flagged."],
    ["10. Audit agent outputs", "Read each agent's output. Mark where they cite evidence vs. infer. Flag "
                                "overclaiming."],
    ["11. Read the synthesis", "Identify what it got right, what it missed, and what remains uncertain."],
    ["12. Export", "Export the run bundle and download the report."],
    ["13. Write your critique", "Complete the lab reflection. See Section 5 for required deliverables."],
])

# ---------------------------------------------------------- 5. Lab Deliverables
h1(doc, "5. Lab Deliverables")
body(doc, "For Lab 09, you must submit three items.")
h2(doc, "5.1 Exported Incident Report")
body(doc, "The JSON export from Crew Run > Export current run. This is the raw output of the multi-agent run and "
          "proves you executed the lab. File name format: <scenario_id>_<timestamp>.json.")
h2(doc, "5.2 One-Page Critique")
body(doc, "A written analysis answering all four of the following questions:")
numbered(doc, [
    "Which agent findings were strongly supported by the evidence? Cite specific log entries or artifact data.",
    "Which findings were weakly supported or inferred without adequate evidence? Give examples.",
    "Which agent was most cautious in separating facts from inference, and why do you think so?",
    "What would you verify next as a human analyst, and what evidence would you look for?",
])
callout(doc, "📊  Grading note:",
        "Vague answers like “the agents did well” will not receive credit. Your critique must cite specific lines "
        "from agent outputs and connect them to specific artifacts.")
h2(doc, "5.3 Corrected Human Summary")
body(doc, "A corrected version of the final synthesis, written by you, that:")
bullets(doc, [
    "Removes unsupported inferences without evidence citations",
    "Adds appropriate uncertainty language where the evidence is ambiguous",
    "Proposes at least two verification steps the agents did not mention",
    "Is written in plain, professional incident-response language (not AI prose)",
])

# ------------------------------------------------------- 6. Available Scenarios
h1(doc, "6. Available Scenarios")
body(doc, f"The lab includes {len(SCENARIOS)} scenarios. Your instructor will tell you which to run. Each has "
          "three timed injects that deliver new information partway through the incident.")
table(doc, ["Scenario", "In one line"],
      [[BY_ID[sid]["title"], ONELINE[sid]] for sid in ORDER])

for n, sid in enumerate(ORDER, start=1):
    s = BY_ID[sid]
    h2(doc, f"6.{n} {s['title']}")
    body(doc, s["summary"])
    body(doc, "Learning goals for this scenario:")
    bullets(doc, s["learning_goals"])
    body(doc, "Available artifacts:")
    bullets(doc, [a.split("/")[-1] for a in s["artifacts"]])
    callout(doc, "Key tension in this scenario:", TENSION[sid])

# ------------------------------------------- 7. Understanding Agent Limitations
h1(doc, "7. Understanding Agent Limitations")
body(doc, "These agents are educational tools, not production security systems. Understanding their failure modes "
          "is itself a learning objective.")
h2(doc, "7.1 Common Failure Modes")
table(doc, ["Failure mode", "What to look for"], [
    ["Hallucinated indicators", "Agent cites an IP address, hash, or filename not present in any artifact. Always "
                                "cross-check against the actual logs."],
    ["Unjustified certainty", "Agent says “the attacker used X” when the log only shows an anomaly. Look for "
                              "missing hedging language."],
    ["Overclaiming scope", "Agent concludes regulated data was exfiltrated when no data classification appears in "
                           "the artifacts."],
    ["Invented remediation", "Agent recommends tools or procedures not mentioned in the knowledge base or "
                             "artifacts."],
    ["Motive assumption", "Agent assumes intent (malicious, insider) without evidence of intent in the logs."],
])
h2(doc, "7.2 What RAG Does and Does Not Fix")
body(doc, "RAG grounding reduces hallucination by giving the agents factual course material to draw on. However, "
          "it does not eliminate hallucination. An agent may still misinterpret a retrieved passage, selectively "
          "apply retrieval context to support a prior claim, or fail to retrieve the most relevant passage if the "
          "query embedding did not match well.")
body(doc, "Always verify by expanding the RAG context panel and checking whether the agents actually used the "
          "retrieved material, and whether they used it accurately. The Guided Walkthrough makes this easier: it "
          "shows you the retrieved chunks and the assembled context as separate, inspectable steps.")
h2(doc, "7.3 Retrieved Content Is Not Trusted Content")
body(doc, "Anything retrieved from the knowledge base is evidence to be analyzed, never instructions to be "
          "followed. The system scans retrieved chunks for injection-like language and labels matches as untrusted "
          "before they reach any agent.")
body(doc, "That scan is a regular-expression pattern match. It catches obvious attempts and will miss subtle ones — "
          "which is precisely why a human reviewer stays in the loop. Treat a clean scan as no evidence of a "
          "problem, not as evidence of no problem.")
h2(doc, "7.4 Temperature and Determinism")
body(doc, "The agents run at a low temperature setting (0.2, and 0.15 for the final synthesis), which makes "
          "outputs more consistent and less creative. This is intentional for an educational setting: you should "
          "see similar outputs on repeat runs, making comparison meaningful. Small differences will still appear "
          "between runs.")

# ---------------------------------------------------------- 8. Troubleshooting
h1(doc, "8. Troubleshooting")
table(doc, ["Problem", "Solution"], [
    ["Ollama reachable: No", "Open a terminal and run: ollama serve. Wait a few seconds, then refresh the app."],
    ["CrewAI available: No", "Your Python environment is missing crewai, most often because the app was launched "
                             "from the wrong environment. The sidebar shows which interpreter is running. Tell "
                             "your instructor."],
    ["No model found in sidebar", "Run: ollama pull llama3.1:8b (or another model). Then refresh the app."],
    ["Indexing fails with an embedding error", "Run: ollama pull mxbai-embed-large, then rebuild the index."],
    ["A run produces no output", "The model may have timed out. Try a smaller model or a simpler objective."],
    ["A run fails with a 403 or subscription error", "You selected a :cloud model your Ollama account does not "
                                                     "cover. Pick a local model in the sidebar."],
    ["RAG index returns no results", "Go to RAG Control and click Build / refresh index before running."],
    ["Retrieved chunks show unfamiliar file paths", "The index was built on a different machine. Rebuild it."],
    ["Export file not found", "Check the exports/ directory in the project root. The file is named "
                              "<scenario_id>_<timestamp>.json."],
])

# ------------------------------------------------------------ 9. Quick Reference
h1(doc, "9. Quick Reference")
h2(doc, "Sidebar Controls")
table(doc, ["Control", "Purpose"], [
    ["Ollama reachable", "Health check. Must say Yes before running."],
    ["CrewAI available", "Whether full orchestration is available. No means Crew Run uses the fallback path."],
    ["Local model", "Which LLM the agents use for inference."],
    ["Use RAG grounding", "Enables knowledge-base retrieval to ground agent outputs."],
    ["Top-k retrieved chunks", "Number of KB passages injected per run (default: 4)."],
    ["Run mode", "CrewAI preferred (full orchestration) or sequential fallback."],
])
h2(doc, "Key Questions for Your Critique")
bullets(doc, [
    "Did the agent cite the artifact, or did it invent the claim?",
    "Is this a fact (observed in logs) or an inference (interpreted from logs)?",
    "What evidence would confirm or refute this finding?",
    "Which agent was most and least cautious?",
    "What did all four agents miss?",
])

out = ROOT / f"student_manual{EXT}"
doc.save(str(out))
print(f"wrote {out}")
