"""Backend selector. `FORMAT=md` emits markdown; anything else emits .docx.

The build scripts import their block writers from here, so both outputs come
from one content source and cannot drift apart.
"""
import os

if os.environ.get("FORMAT") == "md":
    from mdkit import (open_template, title_block, h1, h2, h3, body, bullets,
                       numbered, table, callout, terminal, spacer)
    EXT = ".md"
else:
    from docxkit import (open_template, title_block, h1, h2, h3, body, bullets,
                         numbered, table, callout, terminal, spacer)
    EXT = ".docx"

__all__ = ["open_template", "title_block", "h1", "h2", "h3", "body", "bullets",
           "numbered", "table", "callout", "terminal", "spacer", "EXT"]
