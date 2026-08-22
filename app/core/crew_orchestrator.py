from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import json
import logging
import time
import traceback

from core.ollama_client import generate, OLLAMA_URL
from core.simulation import build_casefile, scenario_artifact_paths

logger = logging.getLogger(__name__)

# CrewAI is imported here at module scope, rather than lazily inside _try_crewai(),
# so the UI can report availability up front in the sidebar instead of the problem
# only surfacing when a student clicks Run. A missing or broken crewai is not fatal —
# run_multiagent_lab() falls back to the sequential path — so the failure is recorded
# rather than raised. The usual cause is launching the app from the wrong environment.
try:
    from crewai import Agent, Task, Crew, Process, LLM
    import crewai as _crewai
    CREWAI_AVAILABLE = True
    CREWAI_VERSION = getattr(_crewai, "__version__", "unknown")
    CREWAI_IMPORT_ERROR = ""
except Exception as _exc:
    Agent = Task = Crew = Process = LLM = None
    CREWAI_AVAILABLE = False
    CREWAI_VERSION = ""
    CREWAI_IMPORT_ERROR = f"{type(_exc).__name__}: {_exc}"
    logger.warning(
        "CrewAI unavailable — Crew Run will use the sequential fallback: %s",
        CREWAI_IMPORT_ERROR,
    )

# Called as on_stage(stage_name, output_text, detail) immediately after each
# agent (and the final synthesis) completes, so the UI can reveal results live
# instead of waiting for the whole run to finish. `detail` carries the same kind
# of technical facts (model, temperature, prompt/response char counts, duration_s)
# that guided_workflow.py's execute_step() captures, so Crew Run's live panel can
# show the same granularity as Guided Walkthrough. Optional / no-op if None.
StageCallback = Optional[Callable[[str, str, Dict[str, Any]], None]]

def _emit(on_stage: StageCallback, stage_name: str, output_text: str, detail: Optional[Dict[str, Any]] = None) -> None:
    if on_stage is not None:
        on_stage(stage_name, output_text, detail or {})

AGENT_SPECS = {
    "SOC Analyst": "Focus on evidence triage, timeline reconstruction, and separating observed facts from inference.",
    "Threat Hunter": "Focus on attacker behavior, plausible techniques, lateral movement, detection gaps, and alternative hypotheses.",
    "Incident Responder": "Focus on containment, eradication, recovery, and operational prioritization.",
    "Security Reviewer": "Focus on uncertainty, overclaiming, teaching clarity, and whether conclusions are justified by evidence.",
}

FINAL_SYNTHESIS_SYSTEM = (
    "You are the lead instructor synthesizing a cybersecurity incident lab. "
    "Produce a clear markdown report with sections: Confirmed Facts, Likely Inferences, Remaining Unknowns, "
    "Recommended Immediate Actions, Recommended Longer-Term Controls, and Notes for Students."
)

AGENT_ANALYST_SYSTEM = "You are a careful cybersecurity analyst in an educational simulation. Be precise and do not overclaim."
AGENT_TEMPERATURE = 0.2
SYNTHESIS_TEMPERATURE = 0.15

def build_agent_prompt(casefile: str, artifacts: str, rag_context: str, student_notes: str, objective: str, agent_name: str, role: str) -> str:
    return f"""
    Scenario casefile:
    {casefile}

    Evidence artifacts:
    {artifacts}

    Retrieved knowledge context:
    {rag_context}

    Student notes:
    {student_notes}

    Objective:
    {objective}

    Your role:
    {agent_name} — {role}

    Instructions:
    - Use markdown headings
    - Distinguish facts from inference
    - Do not invent artifacts or indicators not in evidence
    - If evidence is weak, say so explicitly
    - Include 3-5 most important findings
    """

def build_synthesis_prompt(scenario: dict, objective: str, rag_context: str, agent_outputs: Dict[str, str]) -> str:
    joined = "\n\n".join([f"## {k}\n{v}" for k, v in agent_outputs.items()])
    return f"""
    Scenario title: {scenario['title']}
    Objective: {objective}

    Retrieved knowledge context:
    {rag_context}

    Agent outputs:
    {joined}
    """

def _artifact_text(project_root: Path, scenario: dict, max_per_file: int = 2500) -> str:
    chunks = []
    for path in scenario_artifact_paths(project_root, scenario):
        try:
            if path.suffix.lower() in {".csv"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
            chunks.append(f"[Artifact: {path.name}]\n{text[:max_per_file]}")
        except Exception:
            continue
    return "\n\n".join(chunks)

def _sequential_agent_run(
    model: str,
    scenario: dict,
    project_root: Path,
    objective: str,
    student_notes: str,
    rag_context: str,
    on_stage: StageCallback = None,
) -> Dict[str, str]:
    casefile = build_casefile(scenario, project_root)
    artifacts = _artifact_text(project_root, scenario)
    outputs = {}
    for agent_name, role in AGENT_SPECS.items():
        prompt = build_agent_prompt(casefile, artifacts, rag_context, student_notes, objective, agent_name, role)
        t0 = time.time()
        output = generate(model=model, prompt=prompt, system=AGENT_ANALYST_SYSTEM, temperature=AGENT_TEMPERATURE)
        detail = {
            "agent_name": agent_name,
            "agent_role": role,
            "model": model,
            "temperature": AGENT_TEMPERATURE,
            "prompt_chars": len(prompt),
            "response_chars": len(output),
            "duration_s": round(time.time() - t0, 2),
        }
        outputs[agent_name] = output
        _emit(on_stage, agent_name, output, detail)
    return outputs

def _final_synthesis(
    model: str,
    scenario: dict,
    objective: str,
    rag_context: str,
    agent_outputs: Dict[str, str],
    on_stage: StageCallback = None,
) -> str:
    prompt = build_synthesis_prompt(scenario, objective, rag_context, agent_outputs)
    t0 = time.time()
    report = generate(model=model, prompt=prompt, system=FINAL_SYNTHESIS_SYSTEM, temperature=SYNTHESIS_TEMPERATURE)
    detail = {
        "model": model,
        "temperature": SYNTHESIS_TEMPERATURE,
        "num_agents": len(agent_outputs),
        "prompt_chars": len(prompt),
        "response_chars": len(report),
        "duration_s": round(time.time() - t0, 2),
    }
    _emit(on_stage, "Final Synthesis", report, detail)
    return report

def _try_crewai(
    model: str,
    scenario: dict,
    project_root: Path,
    objective: str,
    student_notes: str,
    rag_context: str,
    on_stage: StageCallback = None,
):
    if not CREWAI_AVAILABLE:
        raise RuntimeError(f"CrewAI import failed: {CREWAI_IMPORT_ERROR}")

    casefile = build_casefile(scenario, project_root)
    artifacts = _artifact_text(project_root, scenario)

    # CrewAI defaults to an OpenAI-backed LLM via LiteLLM unless one is passed
    # explicitly, which fails with AuthenticationError since this app never
    # configures an OpenAI key — it's meant to run entirely against Ollama.
    # temperature is set explicitly to match AGENT_TEMPERATURE used by the
    # Sequential path and Guided Walkthrough — otherwise CrewAI/LiteLLM falls
    # back to its own default, silently diverging in sampling behavior.
    ollama_llm = LLM(model=f"ollama/{model}", base_url=OLLAMA_URL, temperature=AGENT_TEMPERATURE)

    # Each agent runs as its own single-task Crew, one at a time, rather than one
    # multi-task Crew. This is functionally equivalent here (tasks never actually
    # shared CrewAI-managed context between roles) and gives a real per-stage result
    # the instant each agent finishes, instead of only after the whole crew completes —
    # required for the live stage-by-stage reveal in the UI.
    agent_outputs: Dict[str, str] = {}
    raw_parts = []
    for name, role in AGENT_SPECS.items():
        agent = Agent(
            role=name,
            goal=role,
            backstory=(
                "You are part of a local classroom cybersecurity simulation using evidence review and "
                "grounded reasoning. Be precise and do not overclaim."
            ),
            llm=ollama_llm,
            verbose=False,
            allow_delegation=False,
        )
        # Uses the same build_agent_prompt() as the Sequential path and Guided
        # Walkthrough, so all three execution modes ask the model the same thing —
        # previously this built its own separate, shorter prompt here, which was
        # the likely cause of CrewAI-mode reports reading noticeably thinner.
        prompt = build_agent_prompt(casefile, artifacts, rag_context, student_notes, objective, name, role)
        task = Task(
            description=prompt,
            expected_output=(
                f"A markdown analysis from the {name} with 3-5 of the most important findings, clearly "
                "distinguishing observed facts from inference, plus uncertainties and recommendations."
            ),
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        t0 = time.time()
        crew_result = crew.kickoff()

        tasks_output = crew_result.tasks_output
        if len(tasks_output) != 1:
            raise RuntimeError(f"CrewAI returned {len(tasks_output)} task outputs for '{name}', expected 1")
        output = tasks_output[0].raw
        detail = {
            "agent_name": name,
            "agent_role": role,
            "model": model,
            "temperature": AGENT_TEMPERATURE,
            "prompt_chars": len(prompt),
            "response_chars": len(output),
            "duration_s": round(time.time() - t0, 2),
        }
        agent_outputs[name] = output
        raw_parts.append(f"## {name}\n{output}")
        _emit(on_stage, name, output, detail)

    raw = "\n\n".join(raw_parts)
    final_report = _final_synthesis(model, scenario, objective, rag_context, agent_outputs, on_stage=on_stage)
    return {
        "execution_mode": "CrewAI",
        "raw_crewai_output": raw,
        "agent_outputs": agent_outputs,
        "final_report": final_report,
    }

def run_multiagent_lab(
    model: str,
    scenario: dict,
    project_root: Path,
    objective: str,
    student_notes: str = "",
    rag_context: str = "",
    prefer_crewai: bool = True,
    on_stage: StageCallback = None,
):
    try:
        if prefer_crewai:
            run = _try_crewai(model, scenario, project_root, objective, student_notes, rag_context, on_stage=on_stage)
        else:
            raise RuntimeError("CrewAI bypassed by user selection.")
    except Exception as exc:
        if prefer_crewai:
            logger.exception("CrewAI path failed, falling back to sequential agent run")
            # A partial CrewAI run may already have emitted some stages before
            # failing; tell the UI to clear them so only the (complete) fallback
            # run's stages end up displayed.
            _emit(on_stage, "__reset__", "")
        agent_outputs = _sequential_agent_run(model, scenario, project_root, objective, student_notes, rag_context, on_stage=on_stage)
        final_report = _final_synthesis(model, scenario, objective, rag_context, agent_outputs, on_stage=on_stage)
        run = {
            "execution_mode": f"Sequential fallback ({type(exc).__name__})",
            "raw_crewai_output": traceback.format_exc(limit=2),
            "agent_outputs": agent_outputs,
            "final_report": final_report,
        }

    run["model"] = model
    run["scenario_title"] = scenario["title"]
    run["scenario_id"] = scenario["id"]
    run["objective"] = objective
    run["student_notes"] = student_notes
    run["rag_context_used"] = rag_context
    return run

QA_SYSTEM = (
    "You are a patient instructor helping a student understand this cybersecurity incident lab. "
    "You have two kinds of material to draw on, and must keep them clearly separated:\n"
    "1. SCENARIO EVIDENCE — the casefile, artifacts, retrieved context, and agent findings provided below. "
    "This is the only source for claims about what happened in THIS incident. Never invent facts, artifacts, "
    "or indicators about this specific case that are not in that material — if the evidence doesn't cover "
    "something the student asks about this incident, say so explicitly.\n"
    "2. GENERAL KNOWLEDGE — your own security knowledge of concepts, terminology, attacker techniques, "
    "defensive controls, and industry context. You should freely use this to explain background concepts, "
    "define terms, or discuss techniques in general, even when the scenario evidence doesn't mention them.\n"
    "When you answer, make it clear which parts of your answer are grounded in the scenario evidence and "
    "which parts are general background knowledge (e.g. label them, or phrase clearly — 'In this incident, "
    "the evidence shows...' vs 'In general, this kind of technique...'). Keep answers concise."
)

def answer_student_question(
    model: str,
    scenario: dict,
    project_root: Path,
    objective: str,
    rag_context: str,
    agent_outputs_so_far: Dict[str, str],
    question: str,
) -> str:
    casefile = build_casefile(scenario, project_root)
    artifacts = _artifact_text(project_root, scenario)
    findings = "\n\n".join(f"## {k}\n{v}" for k, v in agent_outputs_so_far.items()) or "(No agent findings yet.)"
    prompt = f"""
    Scenario casefile:
    {casefile}

    Evidence artifacts:
    {artifacts}

    Retrieved knowledge context:
    {rag_context}

    Objective:
    {objective}

    Agent findings so far:
    {findings}

    Student question:
    {question}
    """
    return generate(model=model, prompt=prompt, system=QA_SYSTEM, temperature=0.2)
