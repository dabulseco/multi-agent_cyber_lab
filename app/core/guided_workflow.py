from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

from core.ollama_client import generate
from core.simulation import build_casefile, scenario_artifact_paths
from core.rag import retrieve, build_context, flag_suspicious_content, embed_texts, get_collection, EMBED_MODEL_NAME
from core.crew_orchestrator import (
    AGENT_SPECS,
    _artifact_text,
    build_agent_prompt,
    build_synthesis_prompt,
    AGENT_ANALYST_SYSTEM,
    AGENT_TEMPERATURE,
    SYNTHESIS_TEMPERATURE,
    FINAL_SYNTHESIS_SYSTEM,
)

# Fixed what/how/why explanation per step TYPE. Filled in with the real
# technical detail captured when that step actually executes — no LLM call
# needed to produce these, so they're instant and can't fail mid-demo.
STEP_TEMPLATES: Dict[str, Dict[str, str]] = {
    "load_casefile": {
        "what": "Loaded the scenario casefile and all linked evidence artifacts from disk.",
        "how": "Reads the scenario JSON for `{scenario_id}`, then reads each of its {artifact_count} linked artifact "
               "files ({artifact_names}), truncating each to a fixed character limit so prompts stay a manageable size.",
        "why": "Every downstream agent needs to work from the same shared set of facts — this step establishes the "
               "single source of evidence everyone reasons about.",
    },
    "rag_embed_query": {
        "what": "Converted the retrieval query into a numeric vector (embedding).",
        "how": "Uses the local embedding model `{embedding_model}` to turn the query text into a "
               "{dims}-dimension vector, entirely on this machine — no external API call.",
        "why": "Semantic search compares *meaning*, not exact words — embeddings let the system find conceptually "
               "related content even when the wording differs from the query.",
    },
    "rag_similarity_search": {
        "what": "Searched the local knowledge base for the {num_results} most relevant chunks.",
        "how": "ChromaDB compares the query embedding against every stored chunk's embedding, out of {num_indexed} "
               "chunks currently indexed, and returns the top {top_k} matches: {sources}.",
        "why": "This is what lets agent reasoning be 'grounded' in real reference material instead of relying "
               "purely on the model's training data.",
    },
    "rag_flag_check": {
        "what": "Scanned each retrieved chunk for language resembling a prompt-injection attempt.",
        "how": "A regex scan checks all {num_checked} retrieved chunks for patterns like \"ignore previous "
               "instructions\" or \"system:\"; {num_flagged} were flagged. Examples matched: {example_markers}.",
        "why": "Retrieved content is untrusted by default — this is a concrete, inspectable example of separating "
               "evidence from instructions, a core AI-security principle covered in this course's KB.",
    },
    "rag_assemble_context": {
        "what": "Assembled the final block of retrieved context that gets injected into agent prompts.",
        "how": "Formats each retrieved chunk with its source and chunk index, prefixing any flagged chunk with "
               "`[UNTRUSTED / FLAGGED CONTENT]`. Produced {context_chars} characters of context.",
        "why": "This exact text is what every agent 'sees' as background knowledge — inspecting it here shows "
               "precisely what influenced their reasoning, and how untrusted content stays labeled.",
    },
    "agent_prompt_construct": {
        "what": "Built the full prompt for the {agent_name} agent.",
        "how": "Combines the casefile, evidence artifacts, retrieved context, student notes, objective, and this "
               "agent's specific role ({agent_role}) into one prompt of {prompt_chars} characters.",
        "why": "Prompt construction is where the agent's 'role' actually gets enforced — the same evidence produces "
               "different analysis depending on what lens the agent is instructed to apply.",
    },
    "agent_llm_call": {
        "what": "Sent the prompt to the local LLM and received the {agent_name}'s analysis.",
        "how": "Calls `{model}` via Ollama at temperature {temperature} (lower temperature = more deterministic, "
               "less creative). Took {duration_s}s and produced {response_chars} characters.",
        "why": "This is the actual reasoning step — everything before it was preparation, and everything after it "
               "is either another agent's turn or final synthesis.",
    },
    "synthesis_prompt_construct": {
        "what": "Built the prompt for the final synthesis step.",
        "how": "Combines all {num_agents} agents' findings plus the retrieved context into one prompt, instructed "
               "to separate confirmed facts from inference across required report sections.",
        "why": "Synthesis is where individual analyses get reconciled into one coherent report — and where "
               "disagreements or gaps between agents should surface.",
    },
    "synthesis_llm_call": {
        "what": "Generated the final incident report.",
        "how": "Calls `{model}` at temperature {temperature} with the combined findings; took {duration_s}s and "
               "produced {response_chars} characters across the required report sections.",
        "why": "This is the artifact students critique against the raw evidence — the core exercise of the lab.",
    },
}

# A note on today's analytical method, appended to any step where the "analysis" is
# entirely the language model's own reasoning rather than a separate deterministic
# computation. Kept as one shared string so the phrasing stays consistent everywhere
# it's used, and so it's trivial to update once a real code-generation step exists.
_LLM_ONLY_METHOD_NOTE = (
    " This analysis is performed by the language model's own reasoning over the evidence text; no separate "
    "deterministic computation is applied at this stage. A future version of this tool will pair this kind of "
    "step with generated, executable analysis code producing measurable, reproducible metrics."
)

# Narrative SOP report content per step TYPE — deliberately separate from
# STEP_TEMPLATES above: STEP_TEMPLATES drives the terse, granular teaching cards
# shown live during the walkthrough; SOP_TEMPLATES drives the comprehensive,
# narrative Standard Operating Procedure document generated once the walkthrough
# is complete. Static/reusable across scenarios by design (per user direction) —
# only the "Analysis and Results" section's actual findings are dynamic, filled
# in from real captured technical detail and output at render time.
SOP_TEMPLATES: Dict[str, Dict[str, str]] = {
    "load_casefile": {
        "intro": "Every incident investigation begins by establishing a shared, authoritative set of facts. This "
                  "step loads the scenario casefile and every piece of linked evidence, so that every subsequent "
                  "analytical step — and every analyst, human or AI — reasons from the same information rather "
                  "than partial or inconsistent evidence.",
        "analysis_method": "A direct file read: the scenario definition for `{scenario_id}` is loaded, and its "
                            "{artifact_count} linked evidence files ({artifact_names}) are read and prepared for "
                            "use. No interpretation happens at this stage — this is evidence collection, not analysis.",
        "connects_to_next": "The casefile and evidence collected here become the foundation every later step "
                             "references — from knowledge-base retrieval through each analyst's investigation and "
                             "the final synthesis.",
    },
    "rag_embed_query": {
        "intro": "Before external knowledge can be retrieved to ground the investigation, the question being asked "
                  "must be translated into a form a search system can compare against a knowledge base. This step "
                  "performs that translation.",
        "analysis_method": "The query text is converted into a {dims}-dimension numeric vector using the local "
                            "embedding model `{embedding_model}`, entirely on-device with no external service call. "
                            "This vector encodes the *meaning* of the query, not just its keywords.",
        "connects_to_next": "This vector is used immediately in the next step to search the knowledge base for "
                             "conceptually related reference material.",
    },
    "rag_similarity_search": {
        "intro": "With the query embedded, the system searches the locally indexed knowledge base for the "
                  "reference material most relevant to this specific incident and objective — grounding the "
                  "investigation in course reference content rather than relying solely on the model's general "
                  "training.",
        "analysis_method": "A vector similarity search is run against {num_indexed} indexed chunks in the local "
                            "knowledge base, returning the top {top_k} matches by embedding similarity.",
        "connects_to_next": "The retrieved material is screened for trustworthiness in the next step before being "
                             "included in any analyst's reasoning.",
    },
    "rag_flag_check": {
        "intro": "Retrieved content should never be treated as inherently trustworthy simply because a search "
                  "returned it — an AI-security principle this course teaches directly. This step applies that "
                  "principle before any retrieved material reaches an analyst.",
        "analysis_method": "A pattern-based scan checks each of the {num_checked} retrieved chunks for language "
                            "resembling a prompt-injection attempt. This is a heuristic teaching signal, not a "
                            "guarantee of safety.",
        "connects_to_next": "Any flagged content is explicitly marked as untrusted before being assembled into the "
                             "context every analyst will see in the next step.",
    },
    "rag_assemble_context": {
        "intro": "The individually retrieved and screened material must now be assembled into a single, "
                  "consistently labeled block of context that can be handed to every analyst.",
        "analysis_method": "Each retrieved chunk is formatted with its source and position, and any chunk flagged "
                            "in the previous step is explicitly prefixed as untrusted, producing {context_chars} "
                            "characters of retrieved context.",
        "connects_to_next": "This context block is included verbatim in every subsequent analyst's prompt — it is "
                             "the shared background knowledge every analyst reasons alongside the case evidence.",
    },
    "agent_prompt_construct": {
        "intro": "Each analyst on this investigation brings a distinct lens to the same evidence. This step "
                  "prepares the {agent_name}'s specific instructions: the shared case evidence and retrieved "
                  "context, combined with a role-specific mandate — {agent_role}",
        "analysis_method": "The casefile, evidence, retrieved context, student notes, and objective are combined "
                            "into a single {prompt_chars}-character prompt, with the {agent_name}'s role explicitly "
                            "stated as the analytical lens to apply.",
        "connects_to_next": "This prompt is sent to the local language model in the next step, producing the "
                             "{agent_name}'s actual findings.",
    },
    "agent_llm_call": {
        "intro": "This is where the {agent_name}'s actual investigation happens — the point where prepared "
                  "evidence and instructions become a concrete analytical judgment.",
        "analysis_method": "The prepared prompt is sent to the local model `{model}` at temperature {temperature} "
                            "(a low temperature favors consistent, less speculative output)." + _LLM_ONLY_METHOD_NOTE
                            + " This call took {duration_s}s and produced {response_chars} characters of analysis.",
        "connects_to_next": "The {agent_name}'s findings become part of the material every remaining analyst — and "
                             "the final synthesis — reasons alongside.",
    },
    "synthesis_prompt_construct": {
        "intro": "With every analyst's findings in hand, this step prepares the material needed to reconcile "
                  "potentially differing perspectives into one coherent incident report.",
        "analysis_method": "All {num_agents} analysts' findings are combined with the retrieved context into a "
                            "single {prompt_chars}-character synthesis prompt, instructed to separate confirmed "
                            "facts from inference and produce a structured report.",
        "connects_to_next": "This prompt is sent to the model in the final step to produce the deliverable of the "
                             "entire investigation.",
    },
    "synthesis_llm_call": {
        "intro": "This is the culminating step of the investigation: reconciling every analyst's perspective into "
                  "a single, structured incident report.",
        "analysis_method": "The synthesis prompt is sent to `{model}` at temperature {temperature}."
                            + _LLM_ONLY_METHOD_NOTE
                            + " This call took {duration_s}s and produced {response_chars} characters.",
        "connects_to_next": "This report is the deliverable of the workflow — the artifact students and "
                             "instructors should critique against the raw evidence reviewed in the earlier steps.",
    },
}


class _SafeDict(dict):
    def __missing__(self, key):
        return f"?{key}?"


def render_card(step_type: str, detail: Dict[str, Any]) -> Dict[str, str]:
    tmpl = STEP_TEMPLATES.get(step_type, {"what": "Unrecognized step type.", "how": "", "why": ""})
    safe = _SafeDict(detail)
    return {k: v.format_map(safe) for k, v in tmpl.items()}


def render_sop_section(step_type: str, detail: Dict[str, Any]) -> Dict[str, str]:
    tmpl = SOP_TEMPLATES.get(
        step_type,
        {"intro": "No description available for this step type.", "analysis_method": "", "connects_to_next": ""},
    )
    safe = _SafeDict(detail)
    return {k: v.format_map(safe) for k, v in tmpl.items()}


def build_workflow_plan(scenario: dict, use_rag: bool) -> List[Dict[str, str]]:
    plan: List[Dict[str, str]] = [
        {"step_id": "load_casefile", "step_type": "load_casefile", "title": "Load scenario casefile and evidence"}
    ]
    if use_rag:
        plan += [
            {"step_id": "rag_embed_query", "step_type": "rag_embed_query", "title": "Embed the retrieval query"},
            {"step_id": "rag_similarity_search", "step_type": "rag_similarity_search", "title": "Search the knowledge base"},
            {"step_id": "rag_flag_check", "step_type": "rag_flag_check", "title": "Scan retrieved content for injection signals"},
            {"step_id": "rag_assemble_context", "step_type": "rag_assemble_context", "title": "Assemble the RAG context block"},
        ]
    for name in AGENT_SPECS:
        plan.append({"step_id": f"agent_prompt::{name}", "step_type": "agent_prompt_construct", "title": f"Construct prompt for {name}", "agent_name": name})
        plan.append({"step_id": f"agent_call::{name}", "step_type": "agent_llm_call", "title": f"Run {name} analysis", "agent_name": name})
    plan.append({"step_id": "synthesis_prompt", "step_type": "synthesis_prompt_construct", "title": "Construct final synthesis prompt"})
    plan.append({"step_id": "synthesis_call", "step_type": "synthesis_llm_call", "title": "Generate final incident report"})
    return plan


def execute_step(
    step: Dict[str, str],
    ctx: Dict[str, Any],
    model: str,
    db_dir: str,
    project_root: Path,
    objective: str,
    student_notes: str,
    top_k: int,
) -> Dict[str, Any]:
    t0 = time.time()
    step_type = step["step_type"]
    detail: Dict[str, Any] = {}
    output_preview: Optional[str] = None
    scenario = ctx["scenario"]

    if step_type == "load_casefile":
        ctx["casefile"] = build_casefile(scenario, project_root)
        ctx["artifacts_text"] = _artifact_text(project_root, scenario)
        paths = scenario_artifact_paths(project_root, scenario)
        detail = {
            "scenario_id": scenario["id"],
            "artifact_count": len(paths),
            "artifact_names": ", ".join(p.name for p in paths) or "(none)",
        }

    elif step_type == "rag_embed_query":
        query = f"{scenario['title']}\n{objective}\n{student_notes}"
        ctx["rag_query"] = query
        vecs = embed_texts([query])
        detail = {"query": query, "embedding_model": EMBED_MODEL_NAME, "dims": len(vecs[0]) if vecs else 0}

    elif step_type == "rag_similarity_search":
        hits = retrieve(ctx["rag_query"], db_dir=db_dir, top_k=top_k)
        ctx["rag_hits"] = hits
        try:
            num_indexed = get_collection(db_dir).count()
        except Exception:
            num_indexed = "?"
        detail = {
            "top_k": top_k,
            "num_results": len(hits),
            "num_indexed": num_indexed,
            "sources": ", ".join(f"{Path(m.get('source', '?')).name}#{m.get('chunk_index', '?')}" for _, m in hits) or "(none)",
        }

    elif step_type == "rag_flag_check":
        hits = ctx.get("rag_hits", [])
        markers: List[str] = []
        num_flagged = 0
        for doc, meta in hits:
            found = flag_suspicious_content(doc)
            if found:
                num_flagged += 1
                markers.extend(found)
        detail = {
            "num_checked": len(hits),
            "num_flagged": num_flagged,
            "example_markers": ", ".join(sorted(set(markers))[:5]) or "(none found)",
        }

    elif step_type == "rag_assemble_context":
        context_text = build_context(ctx["rag_query"], db_dir=db_dir, top_k=top_k)
        ctx["rag_context"] = context_text
        detail = {"context_chars": len(context_text)}
        output_preview = context_text

    elif step_type == "agent_prompt_construct":
        name = step["agent_name"]
        role = AGENT_SPECS[name]
        prompt = build_agent_prompt(
            ctx.get("casefile", ""), ctx.get("artifacts_text", ""), ctx.get("rag_context", ""),
            student_notes, objective, name, role,
        )
        ctx.setdefault("agent_prompts", {})[name] = prompt
        detail = {"agent_name": name, "agent_role": role, "prompt_chars": len(prompt)}
        output_preview = prompt

    elif step_type == "agent_llm_call":
        name = step["agent_name"]
        prompt = ctx["agent_prompts"][name]
        output = generate(model=model, prompt=prompt, system=AGENT_ANALYST_SYSTEM, temperature=AGENT_TEMPERATURE)
        ctx.setdefault("agent_outputs", {})[name] = output
        detail = {
            "agent_name": name, "model": model, "temperature": AGENT_TEMPERATURE,
            "prompt_chars": len(prompt), "response_chars": len(output),
        }
        output_preview = output

    elif step_type == "synthesis_prompt_construct":
        prompt = build_synthesis_prompt(scenario, objective, ctx.get("rag_context", ""), ctx.get("agent_outputs", {}))
        ctx["synthesis_prompt"] = prompt
        detail = {"num_agents": len(ctx.get("agent_outputs", {})), "prompt_chars": len(prompt)}
        output_preview = prompt

    elif step_type == "synthesis_llm_call":
        report = generate(model=model, prompt=ctx["synthesis_prompt"], system=FINAL_SYNTHESIS_SYSTEM, temperature=SYNTHESIS_TEMPERATURE)
        ctx["final_report"] = report
        detail = {"model": model, "temperature": SYNTHESIS_TEMPERATURE, "response_chars": len(report)}
        output_preview = report

    else:
        raise ValueError(f"Unknown step type: {step_type}")

    detail["duration_s"] = round(time.time() - t0, 2)
    return {**step, "technical_detail": detail, "output_preview": output_preview}


def format_workflow_document(
    scenario: dict,
    results: List[Dict[str, Any]],
    chat: Optional[Dict[int, List[Dict[str, str]]]] = None,
) -> str:
    chat = chat or {}
    lines = [f"# Guided Workflow: {scenario['title']}", ""]
    total_questions = sum(len([m for m in msgs if m.get("role") == "user"]) for msgs in chat.values())
    if total_questions:
        lines.append(f"*{total_questions} question(s) asked during this session — shown inline under each step.*")
        lines.append("")
    for i, result in enumerate(results, start=1):
        detail = result["technical_detail"]
        card = render_card(result["step_type"], detail)
        lines.append(f"## Step {i}: {result['title']}")
        lines.append("")
        lines.append(f"**What:** {card['what']}")
        lines.append("")
        lines.append(f"**How:** {card['how']}")
        lines.append("")
        lines.append(f"**Why it matters:** {card['why']}")
        lines.append("")
        lines.append("**Technical detail:**")
        lines.append("")
        for k, v in detail.items():
            # Values (e.g. the RAG query, which embeds the scenario title/objective/
            # notes joined with newlines) can contain embedded newlines, which would
            # otherwise break markdown list parsing for subsequent bullets.
            flat_value = " ".join(str(v).split())
            lines.append(f"- {k}: {flat_value}")
        lines.append("")

        step_index = i - 1
        messages = chat.get(step_index, [])
        if messages:
            lines.append("**Questions asked at this step:**")
            lines.append("")
            # Paragraph blocks, not list items -- a list item requires single-line
            # content, which would otherwise flatten (and destroy) any code block an
            # answer contains. Questions are short/single-line by nature, so those
            # alone are safe to normalize.
            pending_question = None
            for msg in messages:
                content = str(msg.get("content", "")).strip()
                if msg.get("role") == "user":
                    pending_question = " ".join(content.split())
                else:
                    lines.append(f"**Q:** {pending_question}")
                    lines.append("")
                    lines.append(f"**A:**")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    pending_question = None
    return "\n".join(lines)


def format_sop_report(
    scenario: dict,
    results: List[Dict[str, Any]],
    chat: Optional[Dict[int, List[Dict[str, str]]]] = None,
    output_preview_chars: int = 2000,
) -> str:
    """A comprehensive, narrative Standard Operating Procedure for this scenario run —
    separate and distinct from the granular workflow document. The report format and
    per-step conceptual background (SOP_TEMPLATES) are static and reusable across any
    run of any scenario; the Analysis and Results content in each section is generated
    fresh from this run's actual captured evidence, so re-running the same scenario
    with different log data produces different findings here.
    """
    chat = chat or {}
    lines = [
        f"# Standard Operating Procedure: {scenario['title']}",
        "",
    ]
    summary = scenario.get("summary", "").strip()
    if summary:
        lines.append(summary)
        lines.append("")
    lines.append(
        f"This document walks through the {len(results)}-step procedure this investigation followed, "
        f"why each step matters, what analysis was actually performed, and how each step's output feeds the next."
    )
    lines.append("")

    for i, result in enumerate(results, start=1):
        detail = result["technical_detail"]
        section = render_sop_section(result["step_type"], detail)
        is_last = (i == len(results))

        lines.append(f"## Step {i}: {result['title']}")
        lines.append("")
        lines.append("### Introduction")
        lines.append("")
        lines.append(section["intro"])
        lines.append("")
        lines.append("### Analysis and Results")
        lines.append("")
        if section["analysis_method"]:
            lines.append(section["analysis_method"])
            lines.append("")
        lines.append("**Findings from this run:**")
        lines.append("")
        for k, v in detail.items():
            flat_value = " ".join(str(v).split())
            lines.append(f"- {k}: {flat_value}")
        if result.get("output_preview"):
            preview = result["output_preview"]
            truncated = len(preview) > output_preview_chars
            preview_text = preview[:output_preview_chars]
            lines.append("")
            lines.append("**Output produced at this step:**")
            lines.append("")
            lines.append("```")
            lines.append(preview_text + ("... [truncated]" if truncated else ""))
            lines.append("```")
        lines.append("")
        lines.append("### Connection to the Next Step")
        lines.append("")
        if is_last:
            lines.append(
                "This is the final step in the workflow. " + section["connects_to_next"]
            )
        else:
            lines.append(section["connects_to_next"])
        lines.append("")

    total_questions = sum(len([m for m in msgs if m.get("role") == "user"]) for msgs in chat.values())
    if total_questions:
        lines.append("## Appendix: Questions Asked During This Session")
        lines.append("")
        for step_index in sorted(chat.keys()):
            messages = chat[step_index]
            if not messages:
                continue
            step_title = results[step_index]["title"] if step_index < len(results) else f"Step {step_index + 1}"
            lines.append(f"**At Step {step_index + 1} ({step_title}):**")
            lines.append("")
            # Paragraph blocks, not list items -- see format_workflow_document's per-step
            # Q&A rendering for why (list items require single-line content, which would
            # otherwise flatten and destroy any code block an answer contains).
            pending_question = None
            for msg in messages:
                content = str(msg.get("content", "")).strip()
                if msg.get("role") == "user":
                    pending_question = " ".join(content.split())
                else:
                    lines.append(f"**Q:** {pending_question}")
                    lines.append("")
                    lines.append(f"**A:**")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    pending_question = None

    return "\n".join(lines)
