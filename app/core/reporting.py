from __future__ import annotations
from pathlib import Path
import html
import json
from datetime import datetime

import markdown as _markdown

def export_run_bundle(export_dir: Path, result: dict) -> Path:
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{result['scenario_id']}_{timestamp}"
    out = export_dir / f"{stem}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return out

_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #1a1a1a;
    background: #ffffff;
    max-width: 860px;
    margin: 2.5rem auto;
    padding: 0 1.5rem 4rem;
  }}
  h1, h2, h3, h4 {{ line-height: 1.3; margin-top: 2rem; margin-bottom: 0.6rem; }}
  h1 {{ font-size: 1.8rem; border-bottom: 2px solid #e2e2e2; padding-bottom: 0.4rem; }}
  h2 {{ font-size: 1.4rem; border-bottom: 1px solid #e8e8e8; padding-bottom: 0.3rem; }}
  h3 {{ font-size: 1.15rem; }}
  p {{ margin: 0.7rem 0; }}
  ul, ol {{ padding-left: 1.5rem; }}
  li {{ margin: 0.25rem 0; }}
  code {{
    background: #f2f2f2; border-radius: 3px; padding: 0.1rem 0.35rem;
    font-family: "SFMono-Regular", Consolas, Menlo, monospace; font-size: 0.9em;
  }}
  pre {{
    background: #f6f6f6; border: 1px solid #e2e2e2; border-radius: 6px;
    padding: 0.9rem 1rem; overflow-x: auto;
  }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }}
  th {{ background: #f6f6f6; }}
  blockquote {{
    border-left: 3px solid #ccc; margin: 1rem 0; padding: 0.2rem 1rem;
    color: #555; background: #fafafa;
  }}
  hr {{ border: none; border-top: 1px solid #e2e2e2; margin: 2rem 0; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 2rem; }}
  strong {{ color: #111; }}
</style>
</head>
<body>
<p class="meta">Generated {generated_at} &middot; Multi-Agent Cybersecurity Lab Environment</p>
{body}
</body>
</html>
"""

def markdown_to_html(md_text: str, title: str) -> str:
    body = _markdown.markdown(md_text, extensions=["extra", "sane_lists", "toc"])
    return _HTML_TEMPLATE.format(
        title=html.escape(title),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        body=body,
    )
