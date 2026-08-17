import os
import re
import json
import math
import time
import hashlib
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))

try:
    import requests
except ImportError:
    requests = None

from src.database import update_semantic_data, get_access_history
from src.logger import get_logger

logger = get_logger("engine")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

READABLE_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".html",
    ".sh", ".log", ".csv", ".xml", ".rst", ".go",
}


def read_file_sample(path, max_chars=2000):
    ext = os.path.splitext(path)[1].lower()
    if ext not in READABLE_EXTENSIONS:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None


def simple_embedding(text, dims=64):
    if not text:
        return [0.0] * dims
    try:
        text = text.lower()
        ngrams = [text[i:i + 2] for i in range(len(text) - 1)]
        freq = {}
        for ng in ngrams:
            freq[ng] = freq.get(ng, 0) + 1
        total = max(sum(freq.values()), 1)
        vec = [0.0] * dims
        for ng, count in freq.items():
            idx = int(hashlib.md5(ng.encode()).hexdigest(), 16) % dims
            vec[idx] += count / total
        norm = math.sqrt(sum(v ** 2 for v in vec)) or 1.0
        return [v / norm for v in vec]
    except (ValueError, TypeError) as exc:
        logger.warning("Embedding failed: %s", exc)
        return [0.0] * dims


def call_groq(prompt):
    if not GROQ_API_KEY:
        logger.debug("GROQ_API_KEY not set, skipping LLM call")
        return None
    if requests is None:
        logger.warning("requests package not installed, skipping LLM call")
        return None
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a storage intelligence AI. Be concise."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 300,
        "temperature": 0.3,
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        logger.warning("Groq API returned status %d", r.status_code)
    except requests.RequestException as exc:
        logger.error("LLM request failed: %s", exc)
    except (KeyError, ValueError) as exc:
        logger.error("LLM response parse failed: %s", exc)
    return None


def analyze_with_llm(path, content):
    fname = os.path.basename(path)
    prompt = f"""Analyze this file for archival planning.
File: {fname}
Content:
---
{content[:1500]}
---
Respond ONLY as valid JSON:
{{
  "summary": "one sentence describing this file",
  "importance_score": <0.0 to 1.0>,
  "archival_recommendation": "KEEP | ARCHIVE_SOON | ARCHIVE_NOW | DELETE",
  "reasoning": "one sentence why"
}}"""
    response = call_groq(prompt)
    if not response:
        return None
    try:
        clean = re.sub(r"```json|```", "", response).strip()
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned invalid JSON for %s: %s", fname, exc)
        return None


def compute_access_entropy(file_path):
    try:
        events = get_access_history(file_path)
        if not events:
            return 0.5
        now = time.time()
        weights = []
        for e in events:
            age_days = (now - e["timestamp"]) / 86400
            decay = math.exp(-0.1 * age_days)
            weights.append(decay)
        total = sum(weights) or 1.0
        probs = [w / total for w in weights]
        entropy = -sum(p * math.log2(p + 1e-9) for p in probs)
        max_entropy = math.log2(len(probs) + 1)
        return round(min(entropy / (max_entropy + 1e-9), 1.0), 4)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Access entropy computation failed for %s: %s", file_path, exc)
        return 0.5


def predict_future_relevance(path, size_bytes, last_modified, access_entropy):
    try:
        now = time.time()
        age_days = (now - last_modified) / 86400
        recency = math.exp(-0.01 * age_days)
        size_mb = size_bytes / (1024 * 1024)
        size_penalty = 1.0 / (1.0 + 0.1 * size_mb) if size_mb > 100 else 1.0
        ext = os.path.splitext(path)[1].lower()
        ext_scores = {
            ".py": 0.9, ".js": 0.85, ".ts": 0.85, ".go": 0.9,
            ".md": 0.7, ".txt": 0.5, ".log": 0.2, ".tmp": 0.1,
            ".bak": 0.05, ".zip": 0.3, ".pdf": 0.6, ".csv": 0.5,
            ".json": 0.7, ".yaml": 0.75,
        }
        ext_score = ext_scores.get(ext, 0.4)
        activity_bonus = access_entropy * 0.3
        relevance = (recency * 0.3 + size_penalty * 0.2 + ext_score * 0.3 + activity_bonus)
        return round(min(max(relevance, 0.0), 1.0), 4)
    except (TypeError, ValueError) as exc:
        logger.warning("Future relevance computation failed for %s: %s", path, exc)
        return 0.5


def compute_semantic_access_entropy(path, size_bytes, last_modified):
    try:
        content = read_file_sample(path)
        embedding = simple_embedding(content or os.path.basename(path))
        embedding_json = json.dumps(embedding)
        access_entropy = compute_access_entropy(path)
        future_relevance = predict_future_relevance(path, size_bytes, last_modified, access_entropy)

        llm_result = None
        semantic_score = 0.5
        summary = f"File: {os.path.basename(path)}"
        archival_rec = "KEEP"

        if content:
            llm_result = analyze_with_llm(path, content)

        if llm_result:
            semantic_score = float(llm_result.get("importance_score", 0.5))
            summary = llm_result.get("summary", summary)
            archival_rec = llm_result.get("archival_recommendation", "KEEP")
        else:
            semantic_score = future_relevance
            ext = os.path.splitext(path)[1].lower()
            age_days = (time.time() - last_modified) / 86400
            if age_days > 365 and ext in {".log", ".tmp", ".bak"}:
                archival_rec = "ARCHIVE_NOW"
                summary = f"Old {ext} file, likely obsolete"
            elif age_days > 180:
                archival_rec = "ARCHIVE_SOON"
                summary = f"Not modified in {int(age_days)} days"
            elif age_days > 30:
                archival_rec = "KEEP"
                summary = f"Moderately recent {ext} file"
            else:
                archival_rec = "KEEP"
                summary = f"Recently active {ext} file"

        archival_urgency = round(
            (1.0 - semantic_score) * 0.4 +
            (1.0 - access_entropy) * 0.3 +
            (1.0 - future_relevance) * 0.3,
            4,
        )

        if archival_rec == "ARCHIVE_NOW":
            archival_urgency = max(archival_urgency, 0.85)
        elif archival_rec == "ARCHIVE_SOON":
            archival_urgency = max(archival_urgency, 0.65)
        elif archival_rec == "DELETE":
            archival_urgency = max(archival_urgency, 0.95)

        archival_urgency = min(max(archival_urgency, 0.0), 1.0)

        update_semantic_data(
            path=path,
            semantic_score=semantic_score,
            content_summary=summary,
            embedding_json=embedding_json,
            archival_rec=archival_rec,
            urgency=archival_urgency,
        )

        return {
            "path": path,
            "semantic_score": semantic_score,
            "access_entropy": access_entropy,
            "future_relevance": future_relevance,
            "archival_urgency": archival_urgency,
            "archival_recommendation": archival_rec,
            "summary": summary,
            "llm_used": llm_result is not None,
        }
    except Exception as exc:
        logger.error("SAE computation failed for %s: %s", path, exc)
        return {
            "path": path,
            "semantic_score": 0.5,
            "access_entropy": 0.5,
            "future_relevance": 0.5,
            "archival_urgency": 0.5,
            "archival_recommendation": "PENDING",
            "summary": "Analysis failed",
            "llm_used": False,
        }


def batch_analyze(file_list, verbose=True):
    results = []
    for i, fmeta in enumerate(file_list):
        path = fmeta["path"]
        if not os.path.exists(path):
            logger.warning("File not found, skipping: %s", path)
            continue
        if verbose:
            logger.info("[%d/%d] Analyzing %s", i + 1, len(file_list), os.path.basename(path))
        try:
            result = compute_semantic_access_entropy(
                path=path,
                size_bytes=fmeta.get("size_bytes", 0),
                last_modified=fmeta.get("last_modified", time.time()),
            )
            results.append(result)
        except Exception as exc:
            logger.error("Failed to analyze %s: %s", path, exc)
        time.sleep(0.05)
    return results
