from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import hashlib
import re

import chromadb
from pypdf import PdfReader
from docx import Document

from core.ollama_client import embed as _ollama_embed

# Local Ollama embedding model (must already be pulled: `ollama pull mxbai-embed-large`).
# Embeddings go through the same local Ollama server as everything else in this app —
# no separate ML library/model download, and Ollama keeps the model resident in memory
# across requests rather than reloading it from disk on every call.
EMBED_MODEL_NAME = "mxbai-embed-large:latest"

def embed_texts(texts: List[str]) -> List[List[float]]:
    return _ollama_embed(EMBED_MODEL_NAME, texts)

# Regex-based teaching signal, not a security guarantee: flags content that
# resembles a prompt-injection attempt so it can be marked untrusted before
# being spliced into agent prompts as "retrieved knowledge context".
_INJECTION_MARKERS = [
    # The override phrasings allow words between the qualifier and the noun. The
    # original patterns required "prior instructions" adjacent, which meant the
    # poisoned ticket shipped with this course ("Ignore prior confidentiality
    # instructions") passed the scan clean — the one document the feature exists to
    # catch was the one document it missed.
    r"ignore (all |the |any )?(previous|prior|above|earlier)\b[^.\n]{0,40}?\binstructions",
    r"disregard (all |the |any )?(previous|prior|above|earlier)\b[^.\n]{0,40}?\b(instructions|rules|policy|guidance)",
    r"\bsystem\s*:\s*",
    # Fake system framing addressed at the assistant, e.g. "system note to assistant:".
    r"\bsystem\s+(note|message|prompt|instruction)\b[^:\n]{0,40}:",
    r"you are now\b",
    r"new instructions\s*:",
    r"\bact as\b.{0,30}\b(admin|root|system|developer)\b",
    r"do not (tell|inform|mention) (the )?(user|analyst|student)",
    r"\b(the )?(ai|model|assistant|analyst)\b.{0,20}\bmust\b",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_MARKERS), re.IGNORECASE)

def flag_suspicious_content(text: str) -> List[str]:
    return sorted(set(m.group(0).strip() for m in _INJECTION_RE.finditer(text)))

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

def sanitize_upload_filename(name: str, existing: set) -> str:
    # Strip any path components (Path(...).name drops directory parts on both
    # POSIX and Windows-style separators), restrict to a safe charset, cap
    # length, and dedupe against files already on disk.
    stem = Path(name).name
    stem = _SAFE_FILENAME_RE.sub("_", stem).strip("._") or "upload"
    stem = stem[:100]
    candidate = stem
    n = 1
    while candidate in existing:
        candidate = f"{stem}_{n}"
        n += 1
    return candidate

def get_client(db_dir: str):
    return chromadb.PersistentClient(path=db_dir)

def get_collection(db_dir: str, name: str = "course_kb"):
    client = get_client(db_dir)
    return client.get_or_create_collection(name=name)

def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def read_pdf_file(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)

def read_docx_file(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)

def load_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".py", ".csv", ".json", ".yaml", ".yml", ".log"}:
        return read_text_file(path)
    if suffix == ".pdf":
        return read_pdf_file(path)
    if suffix == ".docx":
        return read_docx_file(path)
    return ""

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks

def stable_id(source: str, idx: int, chunk: str) -> str:
    return hashlib.md5(f"{source}-{idx}-{chunk[:100]}".encode("utf-8")).hexdigest()

def ingest_paths(paths: List[Path], db_dir: str, collection_name: str = "course_kb") -> Tuple[int, int]:
    collection = get_collection(db_dir, collection_name)
    total_docs = 0
    total_chunks = 0

    for path in paths:
        text = load_file_text(path)
        if not text.strip():
            continue
        chunks = chunk_text(text)
        embeddings = embed_texts(chunks)
        ids = [stable_id(str(path), i, chunk) for i, chunk in enumerate(chunks)]
        metadatas = [
            {
                "source": str(path),
                "chunk_index": i,
                "flagged": bool(flag_suspicious_content(chunk)),
            }
            for i, chunk in enumerate(chunks)
        ]
        collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)
        total_docs += 1
        total_chunks += len(chunks)
    return total_docs, total_chunks

def retrieve(query: str, db_dir: str, collection_name: str = "course_kb", top_k: int = 4):
    collection = get_collection(db_dir, collection_name)
    q = embed_texts([query])
    results = collection.query(query_embeddings=q, n_results=top_k)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return list(zip(docs, metas))

def build_context(query: str, db_dir: str, collection_name: str = "course_kb", top_k: int = 4) -> str:
    hits = retrieve(query, db_dir, collection_name, top_k)
    parts = []
    for i, (doc, meta) in enumerate(hits, start=1):
        tag = "[UNTRUSTED / FLAGGED CONTENT] " if meta.get("flagged") else ""
        parts.append(
            f"[Context {i} | source={meta.get('source', 'unknown')} | chunk={meta.get('chunk_index', '?')}]\n{tag}{doc}"
        )
    return "\n\n".join(parts)
