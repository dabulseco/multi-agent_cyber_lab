from __future__ import annotations

from pathlib import Path
import json
import sys
import uuid
import pandas as pd
import streamlit as st

from core.ollama_client import list_models, healthcheck
from core.rag import ingest_paths, build_context, retrieve, sanitize_upload_filename
from core.simulation import (
    list_scenarios,
    load_scenario,
    scenario_artifact_paths,
    preview_artifact,
    scenario_brief_markdown,
    available_artifact_tables,
)
from core.crew_orchestrator import (
    run_multiagent_lab,
    answer_student_question,
    CREWAI_AVAILABLE,
    CREWAI_VERSION,
    CREWAI_IMPORT_ERROR,
)
from core.reporting import export_run_bundle, markdown_to_html
from core.interaction_log import log_event, read_events
from core.guided_workflow import build_workflow_plan, execute_step, format_workflow_document, format_sop_report, render_card

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
KB_DIR = PROJECT_ROOT / "kb"
LABS_DIR = PROJECT_ROOT / "labs"
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = PROJECT_ROOT / "exports"
DB_DIR = str(PROJECT_ROOT / ".chromadb")

st.set_page_config(page_title="Multi-Agent Cybersecurity Lab", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []
if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "indexed_once" not in st.session_state:
    st.session_state.indexed_once = False
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "guided_active_scenario" not in st.session_state:
    st.session_state.guided_active_scenario = None
if "guided_steps" not in st.session_state:
    st.session_state.guided_steps = None
if "guided_results" not in st.session_state:
    st.session_state.guided_results = []
if "guided_ctx" not in st.session_state:
    st.session_state.guided_ctx = {}
if "guided_chat" not in st.session_state:
    st.session_state.guided_chat = {}

st.title("Multi-Agent Cybersecurity Lab Environment")
st.caption("Local Streamlit + Ollama + CrewAI + RAG + simulation engine")

models = list_models()

with st.sidebar:
    st.header("Environment")
    st.write(f"Ollama reachable: {'Yes' if healthcheck() else 'No'}")
    # Surfaced here so a wrong-environment launch is visible before anyone starts a
    # run, rather than only appearing as a fallback banner partway through Crew Run.
    if CREWAI_AVAILABLE:
        st.write(f"CrewAI available: Yes ({CREWAI_VERSION})")
    else:
        st.write("CrewAI available: **No**")
        st.warning(
            "Crew Run will use the sequential fallback. Guided Walkthrough is unaffected — "
            "it never uses CrewAI."
        )
        st.caption(f"{CREWAI_IMPORT_ERROR}\n\nRunning under: `{sys.executable}`")
    st.selectbox("Local model", models if models else ["No model found"], key="selected_model")
    st.checkbox("Use RAG grounding", value=True, key="use_rag")
    st.slider("Top-k retrieved chunks", 2, 8, 4, key="top_k")
    st.selectbox("Run mode", ["CrewAI (preferred)", "Sequential fallback"], key="run_mode")
    st.markdown("---")
    st.header("Tips")
    st.markdown(
        """
        - Index the KB before running scenarios
        - Review artifacts before trusting the crew
        - Compare agent claims to evidence
        - Export the report for grading
        - Use **Guided Walkthrough** for a slow, step-by-step teaching pace; use **Crew Run** for a faster live demo
        """
    )

pages = st.navigation([
    st.Page(page=lambda: home_page(DB_DIR), title="Home", icon="🏠", url_path="home"),
    st.Page(page=lambda: scenario_page(DB_DIR), title="Scenario Lab", icon="🧪", url_path="scenario"),
    st.Page(page=lambda: crew_page(DB_DIR), title="Crew Run", icon="🤖", url_path="crew"),
    st.Page(page=lambda: guided_page(DB_DIR), title="Guided Walkthrough", icon="🧭", url_path="guided"),
    st.Page(page=lambda: rag_page(DB_DIR), title="RAG Control", icon="📚", url_path="rag"),
    st.Page(page=lambda: instructor_page(), title="Instructor Dashboard", icon="🧑‍🏫", url_path="instructor"),
])

def home_page(db_dir: str):
    st.subheader("Overview")
    st.markdown(
        """
        This environment is designed for **scenario-based AI + cybersecurity instruction**.
        Students should not only use the agents — they should challenge them.

        ### Suggested classroom pattern
        1. Read the scenario and evidence
        2. Retrieve background context with RAG
        3. Run the multi-agent crew
        4. Compare agent claims to the evidence
        5. Write a corrected human incident summary
        """
    )

    st.markdown("### Available scenarios")
    for scenario_id in list_scenarios(DATA_DIR / "incidents"):
        scenario = load_scenario(DATA_DIR / "incidents", scenario_id)
        with st.expander(scenario["title"]):
            st.markdown(scenario_brief_markdown(scenario))

def scenario_page(db_dir: str):
    st.subheader("Scenario Lab")
    scenario_ids = list_scenarios(DATA_DIR / "incidents")
    if not scenario_ids:
        st.warning("No scenarios found in data/incidents/.")
        st.stop()
    selected = st.selectbox("Choose a scenario", scenario_ids, key="selected_scenario")
    scenario = load_scenario(DATA_DIR / "incidents", selected)

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown(scenario_brief_markdown(scenario))
        st.markdown("### Simulation injects")
        for inject in scenario.get("injects", []):
            st.markdown(f"- **{inject['time']}** — {inject['message']}")

    with right:
        st.markdown("### Evidence artifacts")
        artifacts = scenario_artifact_paths(PROJECT_ROOT, scenario)
        if not artifacts:
            st.info("No artifacts linked to this scenario.")
        else:
            artifact_name = st.selectbox("Artifact", [a.name for a in artifacts], key="artifact_pick")
            artifact_path = next(a for a in artifacts if a.name == artifact_name)
            st.markdown(preview_artifact(artifact_path))

    st.markdown("### Structured evidence preview")
    artifact_tables = available_artifact_tables(PROJECT_ROOT, scenario)
    if artifact_tables:
        table_name = st.selectbox("Tabular artifact", [p.name for p in artifact_tables], key="table_pick")
        st.dataframe(pd.read_csv(next(p for p in artifact_tables if p.name == table_name)), use_container_width=True)
    else:
        st.info("No CSV artifacts available for this scenario.")

def crew_page(db_dir: str):
    st.subheader("Crew Run")
    scenario_ids = list_scenarios(DATA_DIR / "incidents")
    if not scenario_ids:
        st.warning("No scenarios found in data/incidents/.")
        st.stop()
    selected = st.selectbox("Scenario for crew analysis", scenario_ids, key="crew_scenario")
    scenario = load_scenario(DATA_DIR / "incidents", selected)

    objective = st.text_area(
        "Mission / student objective",
        value=scenario.get("default_objective", "Investigate the incident, identify likely causes, estimate impact, and propose containment steps."),
        height=140,
    )
    student_notes = st.text_area(
        "Student notes or hypotheses (optional)",
        placeholder="Example: The suspicious email may have led to credential theft and external login attempts.",
        height=120,
    )

    PREP_STEP_TYPES = {"load_casefile", "rag_embed_query", "rag_similarity_search", "rag_flag_check", "rag_assemble_context"}

    if st.button("Run multi-agent lab", type="primary"):
        if not models:
            st.error("No local Ollama model found.")
            return

        st.session_state.chat_history = []
        status = st.status("Running multi-agent investigation...", expanded=True)

        # Every step's full shape (step_id/step_type/title/technical_detail/output_preview)
        # is accumulated here — this is what lets Crew Run offer the same comprehensive
        # workflow/SOP downloads as Guided Walkthrough, reusing format_workflow_document()/
        # format_sop_report() directly, instead of only ever having the bare final report.
        step_results = []

        def log_stage(stage_name, output_chars, detail=None):
            log_event(
                PROJECT_ROOT,
                {
                    "session_id": st.session_state.session_id,
                    "scenario_id": scenario["id"],
                    "event_type": "stage_complete",
                    "stage": stage_name,
                    "output_chars": output_chars,
                    **({"duration_s": detail.get("duration_s")} if detail else {}),
                },
            )

        def on_stage(stage_name, output_text, detail=None):
            if stage_name == "__reset__":
                status.update(label="CrewAI failed mid-run — restarting with Sequential fallback...", state="running")
                # A partial CrewAI attempt may have already appended some agent-stage
                # entries before failing; drop them so the captured step list matches
                # only the run that actually completed (mirrors the live UI's own reset).
                del step_results[prep_step_count:]
                return
            detail = detail or {}
            step_type = "synthesis_llm_call" if stage_name == "Final Synthesis" else "agent_llm_call"
            step_id = "synthesis_call" if stage_name == "Final Synthesis" else f"agent_call::{stage_name}"
            fake_result = {"step_id": step_id, "step_type": step_type, "title": stage_name, "technical_detail": detail, "output_preview": output_text}
            status.markdown(f"**{stage_name}** complete ({detail.get('duration_s', '?')}s, {len(output_text)} chars)")
            with status.expander(f"View {stage_name} details", expanded=False):
                _render_step_result(fake_result)
            log_stage(stage_name, len(output_text), detail)
            step_results.append(fake_result)

        # Same granular RAG/casefile steps Guided Walkthrough uses (build_workflow_plan +
        # execute_step from guided_workflow.py) — this is what "the same workflow, minus
        # the pauses" means concretely: Crew Run now runs and displays these exact steps
        # automatically, back-to-back, instead of the caller pre-computing one opaque
        # rag_context string with no visibility into what happened.
        ctx = {"scenario": scenario}
        rag_context = ""
        try:
            prep_steps = [s for s in build_workflow_plan(scenario, use_rag=st.session_state.use_rag) if s["step_type"] in PREP_STEP_TYPES]
            for step in prep_steps:
                prep_result = execute_step(
                    step, ctx,
                    model=st.session_state.selected_model,
                    db_dir=db_dir,
                    project_root=PROJECT_ROOT,
                    objective=objective,
                    student_notes=student_notes,
                    top_k=st.session_state.top_k,
                )
                status.markdown(f"**{prep_result['title']}** complete")
                with status.expander(f"View {prep_result['title']} details", expanded=False):
                    _render_step_result(prep_result)
                log_stage(prep_result["title"], len(prep_result.get("output_preview") or ""), prep_result["technical_detail"])
                step_results.append(prep_result)
            rag_context = ctx.get("rag_context", "")
        except Exception as exc:
            st.warning(f"RAG/setup step failed, continuing with whatever context was gathered: {exc}")
            rag_context = ctx.get("rag_context", "")
        prep_step_count = len(step_results)

        try:
            result = run_multiagent_lab(
                model=st.session_state.selected_model,
                scenario=scenario,
                project_root=PROJECT_ROOT,
                objective=objective,
                student_notes=student_notes,
                rag_context=rag_context,
                prefer_crewai=(st.session_state.run_mode == "CrewAI (preferred)"),
                on_stage=on_stage,
            )
            result["step_results"] = step_results
            status.update(label="Investigation complete.", state="complete")
            st.session_state.run_result = result
            st.session_state.history.append(result)
            log_event(
                PROJECT_ROOT,
                {
                    "session_id": st.session_state.session_id,
                    "scenario_id": scenario["id"],
                    "event_type": "run_complete",
                    "execution_mode": result["execution_mode"],
                },
            )
        except Exception as exc:
            status.update(label="Run failed.", state="error")
            st.error(
                f"Run failed for model '{st.session_state.selected_model}': {exc}\n\n"
                f"If this is a 403/subscription error on a `:cloud` model, pick a different "
                f"model in the sidebar or check your Ollama account's plan at ollama.com."
            )

    result = st.session_state.run_result
    if result:
        st.markdown("### Run summary")
        st.write(f"Execution mode: **{result['execution_mode']}**")
        st.write(f"Model: **{result.get('model', 'unknown')}**")
        st.write(f"Scenario: **{result['scenario_title']}**")
        if result["execution_mode"].startswith("Sequential fallback"):
            st.warning(
                f"CrewAI failed and this run silently fell back to the sequential agent path. "
                f"Reason: {result['execution_mode']}"
            )

        if result.get("rag_context_used"):
            with st.expander("RAG context used"):
                st.text(result["rag_context_used"])

        st.markdown("### Agent outputs")
        for agent_name, output in result["agent_outputs"].items():
            with st.expander(agent_name, expanded=False):
                st.markdown(output)

        st.markdown("### Final synthesis")
        st.markdown(result["final_report"])

        st.markdown("### Ask a question about this scenario")
        st.caption("Questions are answered using the scenario evidence, the crew's findings, and anything indexed via RAG Control (including uploaded files), and are logged for instructor review.")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        question = st.chat_input("Ask about the evidence, an agent's reasoning, or what to do next...")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Re-run RAG retrieval keyed on the student's actual question, not
                    # just the scenario objective used at run-start — this is what
                    # makes newly-uploaded documents (e.g. a PDF added via RAG Control)
                    # actually get consulted for questions the original retrieval missed.
                    qa_rag_context = result.get("rag_context_used", "")
                    if st.session_state.use_rag:
                        try:
                            fresh_context = build_context(
                                query=question, db_dir=db_dir, top_k=st.session_state.top_k
                            )
                            if fresh_context:
                                qa_rag_context = fresh_context
                        except Exception:
                            pass  # fall back to the original run's context
                    try:
                        answer = answer_student_question(
                            model=st.session_state.selected_model,
                            scenario=scenario,
                            project_root=PROJECT_ROOT,
                            objective=result["objective"],
                            rag_context=qa_rag_context,
                            agent_outputs_so_far=result["agent_outputs"],
                            question=question,
                        )
                    except Exception as exc:
                        answer = f"Could not answer: {exc}"
                st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            log_event(
                PROJECT_ROOT,
                {
                    "session_id": st.session_state.session_id,
                    "scenario_id": scenario["id"],
                    "event_type": "question_asked",
                    "question": question,
                    "answer": answer,
                },
            )

        # Rendered after the Q&A section (not before it) so that whatever question was
        # just asked in this same script run is already reflected in chat_history here —
        # Streamlit doesn't re-execute earlier code when later state changes, so if this
        # ran before the chat_input handling above, the download buttons would always be
        # exactly one question behind (the N-1 bug: asking N questions only ever showed
        # N-1 of them, since each render's downloads reflected the *previous* render's
        # chat_history, not the one just updated in the same run).
        st.markdown("---")
        st.markdown("### Downloads")

        # Standalone downloads should be self-documenting even opened outside the app —
        # a bare final_report.html previously carried no record of which model/mode
        # produced it, making two downloaded reports impossible to compare properly.
        report_metadata = (
            f"*Model: `{result.get('model', 'unknown')}` &middot; "
            f"Execution mode: `{result['execution_mode']}` &middot; "
            f"Scenario: `{result['scenario_id']}`*\n\n---\n\n"
        )
        final_report_md = report_metadata + result["final_report"]
        # Crew Run's Q&A isn't tied to a specific step (unlike Guided Walkthrough's
        # per-step chat), so it's appended here as a flat appendix rather than inline —
        # this reflects whatever has been asked so far by the time the report is
        # downloaded, since chat_history is session state, not a run-time snapshot.
        if st.session_state.chat_history:
            # Paragraph blocks, not list items -- a list item requires single-line
            # content, which previously meant flattening every answer's whitespace
            # (destroying any code block's indentation/line breaks it contained).
            # Paragraphs can hold raw multi-line content, fenced code included.
            qa_lines = ["\n\n---\n\n## Appendix: Questions Asked About This Run"]
            pending_question = None
            for msg in st.session_state.chat_history:
                content = str(msg.get("content", "")).strip()
                if msg.get("role") == "user":
                    pending_question = " ".join(content.split())  # questions are short/single-line by nature
                else:
                    qa_lines.append(f"\n**Q:** {pending_question}\n\n**A:**\n\n{content}\n\n---")
                    pending_question = None
            final_report_md += "\n".join(qa_lines)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Export current run"):
                export_path = export_run_bundle(EXPORT_DIR, result)
                st.success(f"Exported to {export_path}")
        with col2:
            st.download_button(
                "Download final report (.md)",
                data=final_report_md.encode("utf-8"),
                file_name=f"{selected}_final_report.md",
                mime="text/markdown",
            )
        with col3:
            report_html = markdown_to_html(final_report_md, f"{result['scenario_title']} — Final Report")
            st.download_button(
                "Download final report (.html)",
                data=report_html.encode("utf-8"),
                file_name=f"{selected}_final_report.html",
                mime="text/html",
            )

        if result.get("step_results"):
            st.markdown("### Comprehensive reports (same depth as Guided Walkthrough)")
            st.caption(
                "These reuse the exact same granular step data captured live above — full RAG breakdown, every "
                "agent's prompt and output, and technical detail for every step. Q&A asked on this page isn't tied "
                "to a specific step, so it's included as an appendix in the Final Report download instead."
            )
            wf_md = format_workflow_document(scenario, result["step_results"])
            wf_html = markdown_to_html(wf_md, f"{result['scenario_title']} — Workflow Document")
            sop_md = format_sop_report(scenario, result["step_results"])
            sop_html = markdown_to_html(sop_md, f"{result['scenario_title']} — SOP Report")
            rcol1, rcol2, rcol3, rcol4 = st.columns([1, 1, 1, 1])
            with rcol1:
                st.download_button("Workflow doc (.md)", data=wf_md.encode("utf-8"), file_name=f"{selected}_crew_workflow.md", mime="text/markdown", key="crew_wf_md")
            with rcol2:
                st.download_button("Workflow doc (.html)", data=wf_html.encode("utf-8"), file_name=f"{selected}_crew_workflow.html", mime="text/html", key="crew_wf_html")
            with rcol3:
                st.download_button("SOP report (.md)", data=sop_md.encode("utf-8"), file_name=f"{selected}_crew_sop_report.md", mime="text/markdown", key="crew_sop_md")
            with rcol4:
                st.download_button("SOP report (.html)", data=sop_html.encode("utf-8"), file_name=f"{selected}_crew_sop_report.html", mime="text/html", key="crew_sop_html")

def _render_step_result(result):
    detail = result["technical_detail"]
    card = render_card(result["step_type"], detail)
    st.markdown(f"**What happened:** {card['what']}")
    st.markdown(f"**How:** {card['how']}")
    st.markdown(f"**Why it matters:** {card['why']}")
    with st.expander("Technical detail", expanded=False):
        st.json(detail)
    if result.get("output_preview"):
        with st.expander("Output preview", expanded=False):
            st.markdown(result["output_preview"][:3000])

def _render_step_qa(scenario, step_index, db_dir):
    history = st.session_state.guided_chat.setdefault(step_index, [])
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    # st.form(clear_on_submit=True) is Streamlit's own sanctioned way to clear a
    # widget after submit — manually assigning to st.session_state[<text_input key>]
    # after that widget has already been instantiated in the same run raises
    # StreamlitAPIException, which is what happened here before this fix.
    with st.form(key=f"guided_qa_form_{step_index}", clear_on_submit=True):
        q = st.text_input("Ask about this step...", key=f"guided_qa_input_{step_index}")
        submitted = st.form_submit_button("Ask")
    if submitted and q.strip():
        history.append({"role": "user", "content": q})
        qa_rag_context = ""
        if st.session_state.use_rag:
            try:
                qa_rag_context = build_context(query=q, db_dir=db_dir, top_k=st.session_state.top_k)
            except Exception:
                pass
        try:
            answer = answer_student_question(
                model=st.session_state.selected_model,
                scenario=scenario,
                project_root=PROJECT_ROOT,
                objective=scenario.get("default_objective", ""),
                rag_context=qa_rag_context,
                agent_outputs_so_far=st.session_state.guided_ctx.get("agent_outputs", {}),
                question=q,
            )
        except Exception as exc:
            answer = f"Could not answer: {exc}"
        history.append({"role": "assistant", "content": answer})
        step_id = st.session_state.guided_steps[step_index]["step_id"]
        log_event(
            PROJECT_ROOT,
            {
                "session_id": st.session_state.session_id,
                "scenario_id": scenario["id"],
                "event_type": "guided_question_asked",
                "step_index": step_index,
                "step_id": step_id,
                "question": q,
                "answer": answer,
            },
        )
        st.rerun()

def _render_guided_downloads(scenario, selected, completed, key_suffix):
    doc_md = format_workflow_document(scenario, completed, chat=st.session_state.guided_chat)
    doc_html = markdown_to_html(doc_md, f"{scenario['title']} — Guided Workflow")
    num_questions = sum(1 for msgs in st.session_state.guided_chat.values() for m in msgs if m.get("role") == "user")
    st.caption(
        f"Downloads include every step's technical detail plus all {num_questions} question(s) asked so far, "
        "shown inline under the step where each was asked."
    )
    dcol1, dcol2 = st.columns([1, 1])
    with dcol1:
        st.download_button(
            "Download workflow so far (.md)",
            data=doc_md.encode("utf-8"),
            file_name=f"{selected}_guided_workflow.md",
            mime="text/markdown",
            key=f"guided_dl_md_{key_suffix}",
        )
    with dcol2:
        st.download_button(
            "Download workflow so far (.html)",
            data=doc_html.encode("utf-8"),
            file_name=f"{selected}_guided_workflow.html",
            mime="text/html",
            key=f"guided_dl_html_{key_suffix}",
        )

def guided_page(db_dir: str):
    st.subheader("Guided Walkthrough")
    st.caption(
        "A granular, pause-at-every-step view of exactly what the system does and why — for deep teaching "
        "sessions. For a faster, still-live demo, use Crew Run instead."
    )
    scenario_ids = list_scenarios(DATA_DIR / "incidents")
    if not scenario_ids:
        st.warning("No scenarios found in data/incidents/.")
        st.stop()
    selected = st.selectbox("Scenario", scenario_ids, key="guided_scenario")
    scenario = load_scenario(DATA_DIR / "incidents", selected)
    student_notes = st.text_area(
        "Student notes or hypotheses (optional)",
        placeholder="Example: The suspicious email may have led to credential theft.",
        height=100,
        key="guided_notes",
    )

    if st.session_state.guided_active_scenario != selected:
        st.session_state.guided_active_scenario = selected
        st.session_state.guided_steps = None
        st.session_state.guided_results = []
        st.session_state.guided_ctx = {}
        st.session_state.guided_chat = {}

    if st.session_state.guided_steps is None:
        if st.button("Start Guided Walkthrough", type="primary"):
            if not models:
                st.error("No local Ollama model found.")
                return
            plan = build_workflow_plan(scenario, use_rag=st.session_state.use_rag)
            st.session_state.guided_steps = plan
            st.session_state.guided_results = []
            st.session_state.guided_ctx = {"scenario": scenario}
            st.session_state.guided_chat = {}
            log_event(
                PROJECT_ROOT,
                {
                    "session_id": st.session_state.session_id,
                    "scenario_id": scenario["id"],
                    "event_type": "guided_walkthrough_started",
                    "num_steps": len(plan),
                },
            )
            st.rerun()
        return

    plan = st.session_state.guided_steps
    completed = st.session_state.guided_results
    pos = len(completed)

    with st.expander(f"Workflow document ({len(plan)} steps)", expanded=(pos == 0)):
        for i, step in enumerate(plan):
            marker = "✅" if i < pos else ("▶️" if i == pos else "⬜")
            st.markdown(f"{marker} **Step {i + 1}.** {step['title']}")

    st.progress(pos / len(plan) if plan else 1.0, text=f"Step {min(pos + 1, len(plan))} of {len(plan)}")

    if completed:
        _render_guided_downloads(scenario, selected, completed, key_suffix="top")

    for i, result in enumerate(completed):
        with st.expander(f"Step {i + 1}: {result['title']} ✅", expanded=(i == pos - 1)):
            _render_step_result(result)
            st.markdown("---")
            _render_step_qa(scenario, i, db_dir)

    if pos < len(plan):
        step = plan[pos]
        st.markdown(f"### Next: Step {pos + 1} — {step['title']}")
        if st.button("▶ Run this step", type="primary", key=f"run_step_{pos}"):
            with st.spinner("Working..."):
                try:
                    result = execute_step(
                        step,
                        st.session_state.guided_ctx,
                        model=st.session_state.selected_model,
                        db_dir=db_dir,
                        project_root=PROJECT_ROOT,
                        objective=scenario.get("default_objective", ""),
                        student_notes=student_notes,
                        top_k=st.session_state.top_k,
                    )
                    completed.append(result)
                    log_event(
                        PROJECT_ROOT,
                        {
                            "session_id": st.session_state.session_id,
                            "scenario_id": scenario["id"],
                            "event_type": "guided_step_complete",
                            "step_index": pos,
                            "step_id": step["step_id"],
                            "step_type": step["step_type"],
                            "duration_s": result["technical_detail"].get("duration_s"),
                        },
                    )
                except Exception as exc:
                    st.error(f"Step failed: {exc}")
            st.rerun()
    else:
        st.success("🎉 Walkthrough complete — every step has been run.")
        if st.session_state.guided_ctx.get("final_report"):
            st.markdown("### Final report")
            st.markdown(st.session_state.guided_ctx["final_report"])

        st.markdown("---")
        st.markdown("### Comprehensive SOP Report")
        st.caption(
            "A separate, narrative Standard Operating Procedure for this scenario — organized by step, with an "
            "introduction, analysis and results, and how each step connects to the next. Distinct from the "
            "granular workflow document above."
        )
        sop_md = format_sop_report(scenario, completed, chat=st.session_state.guided_chat)
        sop_html = markdown_to_html(sop_md, f"{scenario['title']} — SOP Report")
        scol1, scol2 = st.columns([1, 1])
        with scol1:
            st.download_button(
                "Download SOP report (.md)",
                data=sop_md.encode("utf-8"),
                file_name=f"{selected}_sop_report.md",
                mime="text/markdown",
                key="guided_sop_dl_md",
            )
        with scol2:
            st.download_button(
                "Download SOP report (.html)",
                data=sop_html.encode("utf-8"),
                file_name=f"{selected}_sop_report.html",
                mime="text/html",
                key="guided_sop_dl_html",
            )

        if st.button("Restart Walkthrough"):
            st.session_state.guided_steps = None
            st.session_state.guided_results = []
            st.session_state.guided_ctx = {}
            st.session_state.guided_chat = {}
            st.rerun()

    if completed:
        st.markdown("---")
        _render_guided_downloads(scenario, selected, completed, key_suffix="bottom")

def rag_page(db_dir: str):
    st.subheader("RAG Control")
    st.markdown("Index local knowledge-base files, labs, or uploaded documents into local Chroma storage.")

    tmp_dir = PROJECT_ROOT / ".tmp_uploads"

    include_builtin = st.checkbox("Include built-in KB and labs", value=True)
    uploaded = st.file_uploader(
        "Upload extra files",
        type=["txt", "md", "pdf", "docx", "csv", "json", "py", "log"],
        accept_multiple_files=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        build_clicked = st.button("Build / refresh index", type="primary")
    with col2:
        if st.button("Clear uploaded files"):
            if tmp_dir.exists():
                for f in tmp_dir.glob("*"):
                    f.unlink(missing_ok=True)
            st.success("Cleared .tmp_uploads/.")

    if build_clicked:
        paths = []
        tmp_dir.mkdir(exist_ok=True)

        if uploaded:
            existing = {p.name for p in tmp_dir.glob("*")}
            for item in uploaded:
                safe_name = sanitize_upload_filename(item.name, existing)
                existing.add(safe_name)
                path = tmp_dir / safe_name
                path.write_bytes(item.read())
                paths.append(path)

        if include_builtin:
            paths.extend(KB_DIR.glob("*"))
            paths.extend(LABS_DIR.glob("*.md"))

        if not paths:
            st.warning("No files selected.")
        else:
            try:
                doc_count, chunk_count = ingest_paths(paths, db_dir)
                st.session_state.indexed_once = True
                st.success(f"Indexed {doc_count} documents and {chunk_count} chunks.")
            except Exception as exc:
                st.error(f"Indexing failed: {exc}")

    st.markdown("### Retrieval test")
    q = st.text_input("Test retrieval query", placeholder="Prompt injection defense in AI systems")
    if st.button("Retrieve evidence"):
        hits = retrieve(q, db_dir=db_dir, top_k=st.session_state.top_k)
        if not hits:
            st.info("No retrieval results found.")
        for i, (doc, meta) in enumerate(hits, start=1):
            flagged = meta.get("flagged")
            label = f"Hit {i} — {meta.get('source', 'unknown')}"
            if flagged:
                label += " ⚠️ flagged (resembles prompt injection)"
            with st.expander(label):
                if flagged:
                    st.warning("This chunk contains language resembling a prompt-injection attempt.")
                st.text(doc)

def instructor_page():
    st.subheader("Instructor Dashboard")
    st.markdown(
        """
        ### Suggested grading prompts
        - Which agent overclaimed the most?
        - Which conclusion depended on weak evidence?
        - What artifact should have been weighted more heavily?
        - Did the final synthesis separate facts from inference?

        ### Reflection structure
        1. What did the crew do well?
        2. What did the crew miss?
        3. What would a human analyst still need to verify?
        4. Which cybersecurity control should be prioritized next?
        """
    )

    if st.session_state.history:
        st.markdown("### Prior runs in this session")
        for idx, item in enumerate(reversed(st.session_state.history), start=1):
            with st.expander(f"Run {idx}: {item['scenario_title']}"):
                st.write(f"Mode: {item['execution_mode']}")
                st.markdown(item["final_report"])

    st.markdown("### Interaction log (all sessions)")
    st.caption(
        "Every stage completion and student question is logged locally to logs/interactions.jsonl. "
        "This view helps identify which scenarios/topics students ask about most — a proxy for where the material is weak."
    )
    events = read_events(PROJECT_ROOT, limit=500)
    if not events:
        st.info("No interactions logged yet. Run a scenario and ask a question to populate this.")
    else:
        crew_questions = [e for e in events if e.get("event_type") == "question_asked"]
        guided_questions = [e for e in events if e.get("event_type") == "guided_question_asked"]
        all_questions = crew_questions + guided_questions
        stage_events = [e for e in events if e.get("event_type") == "stage_complete"]
        guided_step_events = [e for e in events if e.get("event_type") == "guided_step_complete"]
        runs = [e for e in events if e.get("event_type") in ("run_complete", "guided_walkthrough_started")]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Runs / walkthroughs started", len(runs))
        col2.metric("Crew stage completions", len(stage_events))
        col3.metric("Guided steps completed", len(guided_step_events))
        col4.metric("Questions asked", len(all_questions))

        if all_questions:
            st.markdown("#### Student questions (Crew Run and Guided Walkthrough)")
            df = pd.DataFrame(
                [
                    {
                        "timestamp": q.get("timestamp"),
                        "source": "Guided Walkthrough" if q.get("event_type") == "guided_question_asked" else "Crew Run",
                        "scenario_id": q.get("scenario_id"),
                        "step": q.get("step_id", ""),
                        "question": q.get("question"),
                        "answer_preview": (q.get("answer") or "")[:150],
                        "session_id": (q.get("session_id") or "")[:8],
                    }
                    for q in sorted(all_questions, key=lambda e: e.get("timestamp", ""), reverse=True)
                ]
            )
            st.dataframe(df, use_container_width=True)

pages.run()
