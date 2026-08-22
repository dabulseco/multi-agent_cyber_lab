from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

def list_scenarios(incident_dir: Path):
    return sorted(p.stem for p in incident_dir.glob("*.json"))

def load_scenario(incident_dir: Path, scenario_id: str):
    path = incident_dir / f"{scenario_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))

def scenario_artifact_paths(project_root: Path, scenario: dict):
    paths = []
    for rel in scenario.get("artifacts", []):
        p = project_root / rel
        if p.exists():
            paths.append(p)
    return paths

def available_artifact_tables(project_root: Path, scenario: dict):
    return [p for p in scenario_artifact_paths(project_root, scenario) if p.suffix.lower() == ".csv"]

def preview_artifact(path: Path, max_chars: int = 4000) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".md", ".txt", ".log", ".conf", ".json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            return f"```\n{text[:max_chars]}\n```"
        if suffix == ".csv":
            df = pd.read_csv(path)
            return df.head(20).to_markdown(index=False)
        return f"Preview not implemented for {path.name}"
    except Exception as exc:
        return f"Could not preview {path.name}: {exc}"

def scenario_brief_markdown(scenario: dict) -> str:
    lines = [
        f"## {scenario['title']}",
        scenario.get("summary", ""),
        "",
        "### Learning goals",
    ]
    for item in scenario.get("learning_goals", []):
        lines.append(f"- {item}")
    lines.extend(["", "### Initial situation", scenario.get("initial_situation", "")])
    return "\n".join(lines)

def build_casefile(scenario: dict, project_root: Path) -> str:
    lines = [
        f"Scenario title: {scenario['title']}",
        f"Summary: {scenario.get('summary', '')}",
        f"Initial situation: {scenario.get('initial_situation', '')}",
        "Learning goals:",
    ]
    for goal in scenario.get("learning_goals", []):
        lines.append(f"- {goal}")
    lines.append("Injects:")
    for inject in scenario.get("injects", []):
        lines.append(f"- {inject['time']}: {inject['message']}")
    lines.append("Artifacts:")
    for rel in scenario.get("artifacts", []):
        lines.append(f"- {rel}")
    return "\n".join(lines)
