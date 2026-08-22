from __future__ import annotations
from typing import Iterable, Dict, List
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT_S = float(os.environ.get("OLLAMA_TIMEOUT_S", "300"))

def healthcheck() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.ok
    except Exception:
        return False

def list_models() -> List[str]:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=20)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("models", [])
        # Embedding-only models (capabilities == ["embedding"]) can't be used for
        # /api/generate chat completion, so exclude them from the picker.
        models = [m for m in models if "completion" in m.get("capabilities", [])]
        # /api/tags already returns models most-recently-modified first, matching
        # `ollama list`'s ordering exactly -- preserve that order as-is rather than
        # regrouping local-before-cloud, since a stable "local first" sort meant the
        # default (index 0) selection barely ever changed (the most-recent local model
        # only changes when a new one is pulled). If the default selection happens to
        # land on a subscription-gated cloud model, generate()/chat() now surface a
        # clear error via _raise_for_status_with_detail() instead of crashing.
        return [m["name"] for m in models]
    except Exception:
        return []

def _raise_for_status_with_detail(resp: requests.Response, model: str) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        try:
            detail = resp.json().get("error", resp.text)
        except Exception:
            detail = resp.text
        raise requests.HTTPError(
            f"Ollama returned {resp.status_code} for model '{model}': {detail}", response=resp
        ) from exc

def generate(model: str, prompt: str, system: str = "", temperature: float = 0.2) -> str:
    payload = {
        "model": model,
        "prompt": prompt if not system else f"System:\n{system}\n\nUser:\n{prompt}",
        "options": {"temperature": temperature},
        "stream": False,
    }
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT_S)
    _raise_for_status_with_detail(resp, model)
    return resp.json().get("response", "").strip()

def chat(model: str, messages: Iterable[Dict[str, str]], temperature: float = 0.2, format_schema=None) -> str:
    payload = {
        "model": model,
        "messages": list(messages),
        "options": {"temperature": temperature},
        "stream": False,
    }
    if format_schema is not None:
        payload["format"] = format_schema
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_S)
    _raise_for_status_with_detail(resp, model)
    data = resp.json()
    return data.get("message", {}).get("content", "").strip()

def embed(model: str, texts: Iterable[str]) -> List[List[float]]:
    payload = {"model": model, "input": list(texts)}
    resp = requests.post(f"{OLLAMA_URL}/api/embed", json=payload, timeout=OLLAMA_TIMEOUT_S)
    _raise_for_status_with_detail(resp, model)
    return resp.json().get("embeddings", [])
