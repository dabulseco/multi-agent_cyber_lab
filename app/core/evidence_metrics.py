"""Deterministic analysis over a scenario's tabular evidence.

Everything an agent said before this module existed was the language model's own
reading of log text pasted into a prompt. This computes the numbers instead, so a
claim like "the requests arrived at machine-regular intervals" can be checked
against a coefficient of variation rather than taken on trust.

Design constraints, in order of importance:

1. No model-authored code is ever generated or executed here. The analyzers are
   fixed, version-controlled functions, chosen by inspecting each CSV's column
   headers. Log files are attacker-influenced evidence in several scenarios (see
   data/incidents/ai_assistant_prompt_injection_leak.json), and executing model
   output derived from them is the exact hazard kb/05_agentic_threats teaches
   against. Instead the executed source is shown to students via inspect.getsource().
2. Deterministic means reproducible: same file, same code, same numbers, every run.
3. The evidence files are small — a handful of rows each. Every analyzer that
   computes a dispersion statistic must say so when the sample is thin, because
   manufacturing false confidence would be worse than reporting nothing.

No Streamlit and no Ollama imports, so this module runs and is testable from a shell.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import inspect
import statistics

import pandas as pd

from core.simulation import available_artifact_tables

MAX_ROWS = 50_000
METRICS_CONTEXT_CHAR_CAP = 2500

# Below this many intervals, a standard deviation describes the sample and not
# much else. Analyzers attach a caveat rather than suppressing the number, so
# students can see both the statistic and the reason to distrust it.
MIN_INTERVALS_FOR_CONFIDENCE = 5


# --------------------------------------------------------------------- roles

# Analyzers are written against roles, not column names, because the six shipped
# log schemas share only their timestamp column. Ordered by preference; first hit wins.
ROLE_CANDIDATES: Dict[str, List[str]] = {
    "timestamp": ["timestamp", "time", "ts", "event_time", "@timestamp", "datetime"],
    "actor": ["user", "principal", "username", "account", "device_id", "src_host"],
    "source": ["src_ip", "source_ip", "src_host", "client_ip", "ip"],
    "geo": ["geo", "country", "region"],
    "outcome": ["result", "status", "event", "outcome", "action"],
    "measure": ["bytes_out", "bytes", "cost_usd", "usage_units", "duration", "count"],
    "target": ["resource", "uri", "host", "dst_ip", "service"],
    "user_agent": ["user_agent", "ua"],
}

# Numeric columns that look like measurements but are identifiers or codes. Picking
# dst_port as the "measure" and reporting its escalation would be nonsense.
MEASURE_EXCLUSIONS = {"dst_port", "src_port", "port", "status", "status_code", "id"}

# Outcome tokens recognised across the auth, cloud-audit and MDM schemas. Values
# outside this set are not errors — they are actions (CREATE_ACCOUNT, DELETE_JOB,
# GetObject) — and get reported separately rather than silently bucketed.
SUCCESS_TOKENS = {"SUCCESS", "ALLOW", "OK", "ALLOWED", "PASS", "ACCEPT"}
FAILURE_TOKENS = {"FAILED", "FAILURE", "DENIED", "DENY", "BLOCKED", "ERROR", "REJECT", "FAIL"}

BROWSER_TOKENS = ("mozilla", "chrome", "safari", "firefox", "edge", "opera", "webkit")


def _norm(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def detect_column_roles(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Map analytical roles onto this frame's actual column names.

    Exposed in the teaching card so students can see — and argue with — the
    inference the tool made before it computed anything.
    """
    lookup = {_norm(c): c for c in df.columns}
    roles: Dict[str, Optional[str]] = {}

    for role, candidates in ROLE_CANDIDATES.items():
        roles[role] = next((lookup[c] for c in candidates if c in lookup), None)

    # A timestamp column that isn't conventionally named still needs finding: fall
    # back to the first column that mostly parses as a date.
    if roles["timestamp"] is None:
        for col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
            if parsed.notna().mean() >= 0.9:
                roles["timestamp"] = col
                break

    if roles["measure"] is not None and _norm(roles["measure"]) in MEASURE_EXCLUSIONS:
        roles["measure"] = None
    if roles["measure"] is None:
        for col in df.columns:
            if _norm(col) in MEASURE_EXCLUSIONS:
                continue
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() > 1:
                roles["measure"] = col
                break

    # An actor is whoever the rows are attributable to; if nothing names a person
    # or device, the source address is the best available stand-in.
    if roles["actor"] is None and roles["source"] is not None:
        roles["actor"] = roles["source"]

    return roles


def roles_summary(roles: Dict[str, Optional[str]]) -> str:
    resolved = [f"{role}={col}" for role, col in roles.items() if col]
    return ", ".join(resolved) if resolved else "no roles resolved"


# ----------------------------------------------------------------- utilities

def _timestamps(df: pd.DataFrame, roles: Dict[str, Optional[str]]) -> pd.Series:
    col = roles.get("timestamp")
    if col is None:
        return pd.Series([], dtype="datetime64[ns, UTC]")
    parsed = pd.to_datetime(df[col], errors="coerce", utc=True, format="ISO8601")
    return parsed.dropna().sort_values()


def _intervals_seconds(ts: pd.Series) -> List[float]:
    if len(ts) < 2:
        return []
    return [d.total_seconds() for d in ts.diff().dropna()]


def _sample_note(n_intervals: int) -> str:
    if n_intervals == 0:
        return "No intervals available — a single event cannot show a pattern."
    if n_intervals < MIN_INTERVALS_FOR_CONFIDENCE:
        return (
            f"Only {n_intervals} interval(s) measured. Treat the dispersion figures as descriptive "
            f"of this sample, not as evidence of a stable pattern."
        )
    return ""


def _share(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _ratio(hi: float, lo: float) -> Optional[float]:
    return round(hi / lo, 3) if lo else None


# ---------------------------------------------------------------- analyzers

def interval_regularity(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Measure how evenly spaced the events are.

    Human activity is bursty and irregular; automation is not. The coefficient of
    variation (stdev / mean) makes that difference a number rather than an impression.
    """
    ts = _timestamps(df, roles)
    intervals = _intervals_seconds(ts)
    out: Dict[str, Any] = {
        "n_events": int(len(ts)),
        "n_intervals": len(intervals),
        "sample_size_note": _sample_note(len(intervals)),
    }
    if not intervals:
        return out

    mean_s = statistics.fmean(intervals)
    stdev_s = statistics.stdev(intervals) if len(intervals) > 1 else 0.0
    cv = stdev_s / mean_s if mean_s else 0.0

    if cv < 0.05:
        band = "machine-regular"
    elif cv < 0.35:
        band = "highly regular"
    else:
        band = "irregular / consistent with human jitter"

    out.update({
        "span_seconds": round((ts.iloc[-1] - ts.iloc[0]).total_seconds(), 3),
        "mean_s": round(mean_s, 3),
        "median_s": round(statistics.median(intervals), 3),
        "stdev_s": round(stdev_s, 3),
        "min_s": round(min(intervals), 3),
        "max_s": round(max(intervals), 3),
        "coefficient_of_variation": round(cv, 3),
        "regularity_band": band,
    })
    return out


def off_hours_share(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Share of events falling outside business hours.

    The timezone assumption is reported rather than corrected: every shipped log is
    stamped in UTC while several scenarios are set elsewhere, and a silent adjustment
    would be a hidden analytical decision. Students should see the assumption and
    challenge it.
    """
    start = int(params.get("business_start_hour", 8))
    end = int(params.get("business_end_hour", 18))
    tz_offset = float(params.get("tz_offset_hours", 0))

    ts = _timestamps(df, roles)
    if ts.empty:
        return {"n_events": 0}

    shifted = ts + pd.Timedelta(hours=tz_offset)
    hours = shifted.dt.hour
    in_hours = int(((hours >= start) & (hours < end)).sum())
    total = int(len(hours))

    return {
        "n_events": total,
        "in_hours_count": in_hours,
        "off_hours_count": total - in_hours,
        "off_hours_share": _share(total - in_hours, total),
        "business_window": f"{start:02d}:00-{end:02d}:00",
        "assumption": (
            f"Timestamps evaluated at UTC{tz_offset:+g}. The shipped logs are stamped in UTC; if the "
            f"organisation in this scenario sits in another timezone, this share is measured against "
            f"the wrong working day and should be recomputed."
        ),
        "hour_histogram": ", ".join(f"{h:02d}h×{c}" for h, c in sorted(hours.value_counts().items())),
    }


def outcome_breakdown(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Split the outcome column into successes, failures and everything else.

    Numeric outcome columns are HTTP status codes. String columns mix true outcomes
    (SUCCESS, DENIED) with action names (CREATE_ACCOUNT, GetObject); the latter are
    reported separately instead of being forced into a success/failure bucket.
    """
    col = roles.get("outcome")
    if col is None or col not in df.columns:
        return {"n_events": 0}

    series = df[col].dropna()
    total = int(len(series))
    out: Dict[str, Any] = {"n_events": total, "outcome_column": col}
    if total == 0:
        return out

    if pd.api.types.is_numeric_dtype(series):
        codes = series.astype(int)
        buckets = {f"{k}xx": int(((codes >= k * 100) & (codes < (k + 1) * 100)).sum()) for k in (2, 3, 4, 5)}
        errors = buckets["4xx"] + buckets["5xx"]
        out.update(buckets)
        out["error_rate"] = _share(errors, total)
        return out

    upper = series.astype(str).str.upper().str.strip()
    successes = int(upper.isin(SUCCESS_TOKENS).sum())
    failures = int(upper.isin(FAILURE_TOKENS).sum())
    other = upper[~upper.isin(SUCCESS_TOKENS | FAILURE_TOKENS)]

    out.update({
        "success_count": successes,
        "failure_count": failures,
        "failure_rate": _share(failures, total),
        "other_count": int(len(other)),
        "action_values": ", ".join(f"{v}×{c}" for v, c in other.value_counts().items()) or "none",
    })

    run = best = 0
    for value in upper:
        run = run + 1 if value in FAILURE_TOKENS else 0
        best = max(best, run)
    out["longest_consecutive_failure_run"] = best

    actor_col = roles.get("actor")
    if actor_col and failures:
        failing = df.loc[upper.isin(FAILURE_TOKENS), actor_col]
        if not failing.empty:
            top = failing.value_counts().idxmax()
            out["top_failing_actor"] = f"{top} ({int(failing.value_counts().max())} failures)"
    return out


def volume_escalation(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Total, spread and concentration of the numeric measure.

    A steadily climbing transfer size reads very differently from a flat one, and
    "99% of the bytes came from one host" is a fact worth stating as a fact.
    """
    col = roles.get("measure")
    if col is None or col not in df.columns:
        return {"n_events": 0}

    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        return {"n_events": 0, "measure_column": col}

    values = series.tolist()
    run = best = 1
    for prev, cur in zip(values, values[1:]):
        run = run + 1 if cur > prev else 1
        best = max(best, run)

    out: Dict[str, Any] = {
        "measure_column": col,
        "n_events": int(len(series)),
        "total": round(float(series.sum()), 3),
        "max": round(float(series.max()), 3),
        "min": round(float(series.min()), 3),
        "mean": round(float(series.mean()), 3),
        "max_min_ratio": _ratio(float(series.max()), float(series.min())),
        "longest_monotonic_increase_run": best,
    }

    group_col = roles.get("actor") or roles.get("source")
    if group_col and group_col in df.columns:
        grouped = df.assign(_m=pd.to_numeric(df[col], errors="coerce")).groupby(group_col)["_m"].sum()
        grouped = grouped.sort_values(ascending=False)
        total = float(grouped.sum())
        out["top_contributors"] = "; ".join(
            f"{idx}={round(float(val), 1)} ({_share(int(val), int(total)) * 100:.1f}%)"
            for idx, val in grouped.head(3).items()
        )
    return out


def entity_cardinality(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """How many distinct values each categorical column holds, relative to row count.

    A unique-to-row ratio near 1.0 means every request came from somewhere different
    — the difference between a distributed flood and one noisy host, stated numerically.
    """
    total = int(len(df))
    out: Dict[str, Any] = {"n_rows": total}
    if total == 0:
        return out

    interesting = [c for r, c in roles.items() if c and r in {"actor", "source", "target", "geo"}]
    for col in dict.fromkeys(interesting):
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        counts = series.value_counts()
        key = _norm(col)
        out[f"{key}_n_unique"] = int(series.nunique())
        out[f"{key}_unique_to_row_ratio"] = _share(series.nunique(), total)
        out[f"{key}_top"] = "; ".join(
            f"{v}×{c} ({_share(int(c), total) * 100:.1f}%)" for v, c in counts.head(3).items()
        )
    return out


def actor_source_pivot(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Per actor: how many distinct sources and geographies, and how fast they switched.

    This is impossible travel expressed as a measurement — the seconds between one
    account's appearances from two different places — rather than an assertion.
    """
    actor_col, source_col = roles.get("actor"), roles.get("source")
    if not actor_col or not source_col or actor_col == source_col:
        return {"n_actors": 0}

    ts_col = roles.get("timestamp")
    geo_col = roles.get("geo")
    work = df.copy()
    work["_ts"] = pd.to_datetime(work[ts_col], errors="coerce", utc=True, format="ISO8601") if ts_col else pd.NaT

    lines: List[str] = []
    fastest_source: Optional[float] = None
    fastest_geo: Optional[float] = None
    multi_source_actors = 0

    for actor, group in work.groupby(actor_col):
        group = group.sort_values("_ts")
        n_sources = int(group[source_col].nunique())
        n_geos = int(group[geo_col].nunique()) if geo_col else 0
        if n_sources > 1:
            multi_source_actors += 1

        detail = f"{actor}: {len(group)} events, {n_sources} source(s)"
        if geo_col:
            detail += f", {n_geos} geo(s)"

        for col, tracker in ((source_col, "source"), (geo_col, "geo")):
            if not col:
                continue
            prev_val, prev_ts = None, None
            for _, row in group.iterrows():
                val, ts = row[col], row["_ts"]
                if prev_val is not None and val != prev_val and pd.notna(ts) and pd.notna(prev_ts):
                    gap = (ts - prev_ts).total_seconds()
                    if tracker == "source":
                        fastest_source = gap if fastest_source is None else min(fastest_source, gap)
                    else:
                        fastest_geo = gap if fastest_geo is None else min(fastest_geo, gap)
                    detail += f", switched {tracker} in {gap:.0f}s"
                prev_val, prev_ts = val, ts
        lines.append(detail)

    return {
        "n_actors": int(work[actor_col].nunique()),
        "actors_using_multiple_sources": multi_source_actors,
        "min_seconds_between_different_sources": round(fastest_source, 1) if fastest_source is not None else None,
        "min_seconds_between_different_geos": round(fastest_geo, 1) if fastest_geo is not None else None,
        "per_actor": " | ".join(lines[:6]),
    }


def client_tooling(df: pd.DataFrame, roles: Dict[str, Optional[str]], params: Dict[str, Any]) -> Dict[str, Any]:
    """Share of requests whose user-agent does not look like a browser.

    A heuristic teaching signal, not a guarantee — the same framing the retrieved-content
    injection scan uses. User agents are trivially forged; absence of a scripted client
    string is not evidence of a human.
    """
    col = roles.get("user_agent")
    if col is None or col not in df.columns:
        return {"n_events": 0}

    series = df[col].dropna().astype(str)
    total = int(len(series))
    if total == 0:
        return {"n_events": 0}

    non_browser = series[~series.str.lower().str.contains("|".join(BROWSER_TOKENS), regex=True, na=False)]
    return {
        "n_events": total,
        "non_browser_count": int(len(non_browser)),
        "non_browser_share": _share(len(non_browser), total),
        "non_browser_values": "; ".join(sorted(set(non_browser))[:5]) or "none",
        "distinct_user_agents": int(series.nunique()),
        "caveat": "User-agent strings are self-reported and trivially forged. This is a heuristic signal, not proof.",
    }


# ----------------------------------------------------------------- registry

@dataclass(frozen=True)
class Analyzer:
    name: str
    description: str
    required_roles: tuple
    func: Callable[[pd.DataFrame, Dict[str, Optional[str]], Dict[str, Any]], Dict[str, Any]]
    param_schema: Dict[str, Any] = field(default_factory=dict)


ANALYZERS: Dict[str, Analyzer] = {
    a.name: a for a in (
        Analyzer("interval_regularity",
                 "Timing regularity: are events machine-spaced or humanly jittery?",
                 ("timestamp",), interval_regularity),
        Analyzer("off_hours_share",
                 "Proportion of activity outside business hours.",
                 ("timestamp",), off_hours_share,
                 {"business_start_hour": 8, "business_end_hour": 18, "tz_offset_hours": 0}),
        Analyzer("outcome_breakdown",
                 "Success, failure and action counts, plus failure streaks.",
                 ("outcome",), outcome_breakdown),
        Analyzer("volume_escalation",
                 "Totals, spread and concentration of the numeric measure.",
                 ("measure",), volume_escalation),
        Analyzer("entity_cardinality",
                 "Distinct-value counts per categorical column: concentrated or distributed?",
                 ("actor",), entity_cardinality),
        Analyzer("actor_source_pivot",
                 "Per-actor source and geography spread, including switch timing.",
                 ("actor", "source"), actor_source_pivot),
        Analyzer("client_tooling",
                 "Share of non-browser user agents.",
                 ("user_agent",), client_tooling),
    )
}


@dataclass
class AnalysisSpec:
    path: Path
    analyzer: str
    params: Dict[str, Any]
    reason: str
    columns_used: str


@dataclass
class AnalysisResult:
    path: Path
    analyzer: str
    metrics: Dict[str, Any]
    column_roles: Dict[str, Optional[str]]
    n_rows: int
    error: Optional[str] = None


# ------------------------------------------------------------------ pipeline

def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, nrows=MAX_ROWS)


def plan_analyses(project_root: Path, scenario: dict) -> List[AnalysisSpec]:
    """Select every analyzer whose required roles are present in each CSV artifact.

    Selection is a rule, not a judgment: it depends only on which columns exist, so
    the same scenario always produces the same plan.
    """
    specs: List[AnalysisSpec] = []
    for path in available_artifact_tables(project_root, scenario):
        try:
            roles = detect_column_roles(_load(path))
        except Exception:
            continue
        for analyzer in ANALYZERS.values():
            missing = [r for r in analyzer.required_roles if not roles.get(r)]
            if missing:
                continue
            used = ", ".join(f"{r}={roles[r]}" for r in analyzer.required_roles)
            specs.append(AnalysisSpec(
                path=path,
                analyzer=analyzer.name,
                params=dict(analyzer.param_schema),
                reason=f"requires {', '.join(analyzer.required_roles)}; present as {used}",
                columns_used=used,
            ))
    return specs


def run_analyses(project_root: Path, specs: List[AnalysisSpec]) -> List[AnalysisResult]:
    """Execute each spec in isolation. One bad file must never abort a live class."""
    results: List[AnalysisResult] = []
    frames: Dict[Path, pd.DataFrame] = {}

    for spec in specs:
        try:
            if spec.path not in frames:
                frames[spec.path] = _load(spec.path)
            df = frames[spec.path]
            roles = detect_column_roles(df)
            metrics = ANALYZERS[spec.analyzer].func(df, roles, spec.params)
            results.append(AnalysisResult(spec.path, spec.analyzer, metrics, roles, int(len(df))))
        except Exception as exc:
            results.append(AnalysisResult(
                spec.path, spec.analyzer, {}, {}, 0, error=f"{type(exc).__name__}: {exc}"
            ))
    return results


# ---------------------------------------------------------------- formatting

def _fmt_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def format_metrics_context(results: List[AnalysisResult]) -> str:
    """The block injected into agent prompts, alongside the retrieved RAG context."""
    if not results:
        return ""

    lines: List[str] = []
    for path in dict.fromkeys(r.path for r in results):
        lines.append(f"[{path.name}]")
        for result in (r for r in results if r.path == path):
            if result.error:
                lines.append(f"  {result.analyzer}: could not be computed ({result.error})")
                continue
            pairs = [f"{k}={_fmt_value(v)}" for k, v in result.metrics.items() if v not in (None, "", 0.0) or k.endswith("_count")]
            if pairs:
                lines.append(f"  {result.analyzer}: " + "; ".join(pairs))
    text = "\n".join(lines)
    if len(text) > METRICS_CONTEXT_CHAR_CAP:
        text = text[:METRICS_CONTEXT_CHAR_CAP] + "\n  [truncated to keep the prompt within budget]"
    return text


def format_metrics_markdown(results: List[AnalysisResult], include_source: bool = True) -> str:
    """The step's output_preview: per-file metric tables, then the executed source.

    Showing the source is the point. Students are told these numbers are reproducible;
    the code that produced them has to be available for that claim to mean anything.
    """
    if not results:
        return "_No tabular evidence in this scenario — nothing was computed._"

    blocks: List[str] = []
    for path in dict.fromkeys(r.path for r in results):
        blocks.append(f"#### {path.name}")
        for result in (r for r in results if r.path == path):
            blocks.append(f"**{result.analyzer}**")
            if result.error:
                blocks.append(f"> Could not be computed: {result.error}")
                continue
            if not result.metrics:
                blocks.append("> No values produced.")
                continue
            blocks.append("| Metric | Value |")
            blocks.append("|---|---|")
            for key, value in result.metrics.items():
                if value in (None, ""):
                    continue
                blocks.append(f"| {key} | {_fmt_value(value)} |")
            blocks.append("")

    if include_source:
        used = dict.fromkeys(r.analyzer for r in results if not r.error)
        blocks.append("#### Executed source")
        blocks.append("Exactly the code that produced the values above:")
        for name in used:
            blocks.append(f"```python\n{inspect.getsource(ANALYZERS[name].func).rstrip()}\n```")

    return "\n".join(blocks)


def headline_findings(results: List[AnalysisResult], limit: int = 4) -> str:
    """The two to four most quotable measured facts, for the flattened teaching card.

    The report formatters collapse whitespace in every technical_detail value, so a
    nested structure would render unreadably; this exists to give that flat line
    something worth saying.
    """
    picks: List[tuple] = []
    for result in results:
        if result.error or not result.metrics:
            continue
        m, name = result.metrics, result.path.name
        cv = m.get("coefficient_of_variation")
        if cv is not None:
            picks.append((3 if cv < 0.05 else 1, f"{name}: interval CV {_fmt_value(cv)} ({m.get('regularity_band')})"))
        share = m.get("off_hours_share")
        if share:
            picks.append((2 if share > 0.5 else 0, f"{name}: {share * 100:.0f}% of events off-hours"))
        ratio = m.get("max_min_ratio")
        if ratio and ratio > 5:
            picks.append((2, f"{name}: largest {result.metrics.get('measure_column', 'measure')} {_fmt_value(ratio)}x the smallest"))
        gap = m.get("min_seconds_between_different_geos")
        if gap is not None:
            picks.append((3, f"{name}: one actor appeared from two geographies {gap:.0f}s apart"))
        nb = m.get("non_browser_share")
        if nb:
            picks.append((2, f"{name}: {nb * 100:.0f}% non-browser user agents"))
        err = m.get("error_rate")
        if err:
            picks.append((1, f"{name}: {err * 100:.0f}% error responses"))

    picks.sort(key=lambda p: -p[0])
    return "; ".join(text for _, text in picks[:limit]) or "no headline metrics for this evidence"
