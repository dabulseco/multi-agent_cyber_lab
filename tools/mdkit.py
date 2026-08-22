"""Markdown backend exposing the same block-writer API as docxkit, so a single
build script emits the .docx and the .md from one content source.

Mapping: the document title is H1, so section headings shift down one level
(h1 -> ##, h2 -> ###, h3 -> ####). Callouts become blockquotes, terminal blocks
become fenced bash, and tables become GitHub pipe tables.
"""


class MarkdownDoc:
    def __init__(self):
        self.lines = []

    def add(self, text=""):
        self.lines.append(text)

    def save(self, path):
        out = "\n".join(self.lines).rstrip() + "\n"
        # Collapse runs of blank lines left by spacer() calls.
        while "\n\n\n" in out:
            out = out.replace("\n\n\n", "\n\n")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)


def open_template(_path):
    return MarkdownDoc()


def _cell(text):
    """Pipe tables are single-line: escape delimiters and fold hard breaks."""
    return text.replace("|", "\\|").replace("\n", "<br>")


def title_block(doc, title, subtitle, tagline, product, version):
    doc.add(f"# {title}")
    doc.add()
    doc.add(f"**{subtitle}**")
    doc.add()
    doc.add(f"*{tagline}*")
    doc.add()
    doc.add(f"{product}  ")
    doc.add(f"{version}")
    doc.add()
    doc.add("---")
    doc.add()


def h1(doc, text):
    doc.add()
    doc.add(f"## {text}")
    doc.add()


def h2(doc, text):
    doc.add()
    doc.add(f"### {text}")
    doc.add()


def h3(doc, text):
    doc.add()
    doc.add(f"#### {text}")
    doc.add()


def body(doc, text):
    doc.add(text)
    doc.add()


def bullets(doc, items):
    for item in items:
        doc.add(f"- {item}")
    doc.add()


def numbered(doc, items):
    for i, item in enumerate(items, start=1):
        doc.add(f"{i}. {item}")
    doc.add()


def table(doc, header, rows):
    doc.add("| " + " | ".join(_cell(h) if h else " " for h in header) + " |")
    doc.add("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        doc.add("| " + " | ".join(_cell(c) for c in row) + " |")
    doc.add()


def callout(doc, label, text):
    if "\n" in text:
        # Multi-line callouts in these manuals are code (the scenario schema).
        doc.add(f"**{label}**")
        doc.add()
        doc.add("```json")
        for line in text.split("\n"):
            doc.add(line)
        doc.add("```")
    else:
        doc.add(f"> **{label}** {text}")
    doc.add()


def terminal(doc, command):
    doc.add("```bash")
    for line in command.split("\n"):
        doc.add(line)
    doc.add("```")
    doc.add()


def spacer(doc):
    doc.add()
