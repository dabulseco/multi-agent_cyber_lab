"""Package init for the lab's core modules.

This runs before any `core.*` module is imported, which makes it the one place
guaranteed to execute ahead of the CrewAI import in crew_orchestrator.py.

CrewAI's first-run tracing handler prints a Rich panel and then blocks on
`input()` for 20 seconds waiting for an answer that, in a classroom, nobody is
there to give — the prompt appears on the server terminal, not in the browser.
It fires once per `crew.kickoff()`, and this app runs one crew per agent, so an
affected session pays up to 80 seconds of dead time per Crew Run on the
Streamlit script thread.

`CREWAI_TRACING_ENABLED=false` does not suppress it. The gate in crewai/crew.py
reads `is_tracing_enabled() or self.tracing or should_auto_collect_first_time_traces()`,
and that third clause is the branch that prompts. `CREWAI_TESTING` is the only
flag that short-circuits both the auto-collect decision and the prompt itself.

Verified against crewai==0.193.2 (pinned in requirements.txt): CREWAI_TESTING is
read in exactly three places, all inside crewai/events/listeners/tracing/utils.py,
and affects nothing about agents, LLM calls, or crew execution. Re-check those
call sites when bumping crewai — the name suggests broader meaning than it has.

Set with setdefault so a real environment variable or .env entry still wins.
"""
import os

# Suppresses the interactive trace prompt and the 20s block behind it.
os.environ.setdefault("CREWAI_TESTING", "true")

# No trace collection. Kept explicit so the intent survives independently of the
# flag above, and so nothing is sent anywhere if that flag ever stops working.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

# CrewAI keys its per-project state directory on `Path.cwd().name` unless this is
# set, so launching from a different working directory looks like a brand new
# install and re-triggers the first-run prompt. This is an application *name*
# handed to appdirs, not a filesystem path, so it must stay a bare stable string.
os.environ.setdefault("CREWAI_STORAGE_DIR", "multi_agent_lab")
