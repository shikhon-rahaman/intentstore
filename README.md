# IntentStore

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-Compatible-green?logo=linux&logoColor=white)
![Hackathon](https://img.shields.io/badge/CDAC-SSM%20Next--Gen%20Kernel%202026-orange)

**LLM-powered semantic storage intelligence for the CDAC SSM Next-Gen Kernel.**

IntentStore watches filesystem activity (via eBPF-style syscall tracing), scores files with semantic analysis, and recommends archival actions — exposed through a Rich CLI dashboard and FastAPI REST API.

---

## Quick Start

```bash
pip install -r requirements.txt
python run_demo.py
python -m src.cli.dashboard status
```

That's it. The demo scans the repo, simulates 5 eBPF syscall events, runs semantic analysis, prints the dashboard, and shows the top 3 archival recommendations.

For a full judge walkthrough, see **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)**.

---

## How It Works

IntentStore computes a **Semantic Access Entropy (SAE)** score for every tracked file through a three-stage pipeline:

### 1. Collect — eBPF syscall tracing + file watcher

```
openat / read / write  →  access_events table (PID, timestamp, filepath)
filesystem scan        →  file_metadata table (size, extension, mtime)
```

The eBPF simulator (`src/engine/ebpf_simulator.py`) captures kernel-level I/O events. The file watcher (`src/collector/file_watcher.py`) indexes directory contents into SQLite.

### 2. Analyze — semantic engine

For each file, the engine computes three signals:

| Signal | Symbol | Source |
|---|---|---|
| **Semantic Score** | `S` | LLM content analysis (Groq/Llama3) or heuristic fallback |
| **Access Entropy** | `A` | Shannon entropy over time-decayed access events |
| **Future Relevance** | `F` | Recency × extension weight × size penalty × activity bonus |

**Access Entropy formula:**

```
A = H(decayed_events) / log₂(n)

where  decay(t) = e^(-0.1 × age_days)
       H       = -Σ pᵢ log₂(pᵢ)
```

**Future Relevance formula:**

```
F = 0.3 × recency + 0.2 × size_penalty + 0.3 × ext_score + 0.3 × A

where  recency      = e^(-0.01 × age_days)
       size_penalty = 1 / (1 + 0.1 × size_mb)   if size > 100 MB
       ext_score    = extension-based weight (.py=0.9, .log=0.2, …)
```

### 3. Recommend — archival urgency

The **SAE urgency score** drives recommendations:

```
Urgency = 0.4 × (1 - S) + 0.3 × (1 - A) + 0.3 × (1 - F)
```

| Urgency | Recommendation |
|---|---|
| ≥ 0.85 | `ARCHIVE_NOW` |
| ≥ 0.65 | `ARCHIVE_SOON` |
| < 0.65 | `KEEP` |
| ≥ 0.95 | `DELETE` |

Results are stored in `~/.intentstore/intentstore.db` and served via CLI and REST API.

---

## Why IntentStore Wins

| Capability | `find` / `locate` | `du` / `ncdu` | `atime` policies | **IntentStore** |
|---|---|---|---|---|
| Understands file *content* | ❌ | ❌ | ❌ | ✅ LLM + embeddings |
| Tracks access *patterns* | ❌ | ❌ | ⚠️ atime only | ✅ entropy over event history |
| Predicts future relevance | ❌ | ❌ | ❌ | ✅ recency + extension + activity model |
| Kernel-level I/O visibility | ❌ | ❌ | ❌ | ✅ eBPF syscall tracing |
| Actionable recommendations | ❌ | ❌ | ❌ | ✅ KEEP / ARCHIVE / DELETE |
| REST API for automation | ❌ | ❌ | ❌ | ✅ FastAPI (`/status`, `/files`, `/report`, `/scan`) |
| Persistent intelligence DB | ❌ | ❌ | ❌ | ✅ SQLite with full metadata |
| Live filesystem watch | ❌ | ❌ | ❌ | ✅ watchdog-based collector |

Traditional tools answer *"where is the space?"* IntentStore answers *"what should we do about it?"*

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  eBPF Simulator │────▶│  SQLite Database  │◀────│  File Watcher   │
│  (syscall trace)│     │  file_metadata    │     │  (scan + watch) │
└─────────────────┘     │  access_events    │     └─────────────────┘
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │ Semantic Engine  │
                        │ S, A, F → Urgency│
                        └────────┬─────────┘
                                 │
                   ┌─────────────┼─────────────┐
                   │             │             │
            ┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
            │ Rich CLI    │ │ FastAPI │ │ run_demo.py │
            │  dashboard  │ │  REST   │ │  (CI demo)  │
            └─────────────┘ └─────────┘ └─────────────┘
```

---

## CLI Commands

```bash
python -m src.cli.dashboard scan <path>     # Scan + analyze a directory
python -m src.cli.dashboard status          # Rich dashboard
python -m src.cli.dashboard report          # High-urgency archival report
python -m src.cli.dashboard watch <path>    # Live filesystem watch
```

## REST API

```bash
uvicorn src.api.main:app --port 8000
```

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Storage stats JSON |
| `GET` | `/files` | All files with SAE scores |
| `GET` | `/report?threshold=0.6` | High-urgency files |
| `POST` | `/scan` | Trigger scan on `{"path": "..."}` |

Interactive docs: http://127.0.0.1:8000/docs

---

## Project Structure

```
intentstore/
├── run_demo.py                  # One-command hackathon demo
├── DEMO_SCRIPT.md               # 2-minute judge walkthrough
├── src/
│   ├── database.py              # SQLite persistence layer
│   ├── api/main.py              # FastAPI REST API
│   ├── cli/dashboard.py         # Rich CLI dashboard
│   ├── collector/file_watcher.py# Filesystem scan + watch
│   └── engine/
│       ├── semantic_engine.py   # SAE scoring + LLM analysis
│       └── ebpf_simulator.py   # eBPF syscall trace simulator
└── .github/workflows/scan.yml   # CI runs run_demo.py on every push
```

---

## Configuration

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Enable live LLM summaries via Groq (Llama3). Falls back to heuristics if unset. |

---

## License

See [LICENSE](LICENSE).
