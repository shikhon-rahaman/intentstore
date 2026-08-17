# IntentStore — 2-Minute Hackathon Demo Script

**Audience:** CDAC SSM Next-Gen Kernel Hackathon 2026 judges  
**Time:** ~2 minutes  
**Platform:** Linux (Ubuntu 22.04+ recommended)

Run these **5 commands in order** from the project root.

---

## Command 1 — Install dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed watchdog requests numpy scipy matplotlib rich fastapi uvicorn ...
```

**Proves:** IntentStore installs cleanly with all engine, CLI, and API dependencies.

---

## Command 2 — Run the full demo pipeline

```bash
python run_demo.py
```

**Expected output (abbreviated):**
```
==============================================================
  INTENTSTORE — Semantic Storage Intelligence Engine
  CDAC SSM Next-Gen Kernel Hackathon 2026
==============================================================

[DB] Initialized at ~/.intentstore/intentstore.db
Running IntentStore demo on: /path/to/intentstore

[SCAN] Scanning: /path/to/intentstore
[SCAN] Found 13 files in /path/to/intentstore

[eBPF] Simulating kernel syscall trace (SSM Next-Gen Kernel)
[eBPF] Attaching probe: tracepoint/syscalls/sys_enter_*
------------------------------------------------------------------------
[eBPF] 2026-08-17 18:22:04.457 PID=2334   openat  .../requirements.txt
[eBPF] 2026-08-17 18:22:04.510 PID=36740  read    .../src/database.py
[eBPF] 2026-08-17 18:22:04.567 PID=39106  write   .../src/cli/dashboard.py
[eBPF] 2026-08-17 18:22:04.627 PID=4133   read    .../src/collector/file_watcher.py
[eBPF] 2026-08-17 18:22:04.686 PID=25704  write   .../src/engine/semantic_engine.py
------------------------------------------------------------------------
[eBPF] Captured 5 syscall events

Analyzing 13 files...

[ENGINE] [1/13] requirements.txt
[ENGINE] [2/13] database.py
...

┌────────────────────────── IntentStore Dashboard ──────────────────────────┐
│ Files: 13   Size: 0.03 MB   Urgent: 0   Events: 5                         │
└───────────────────────────────────────────────────────────────────────────┘
╭─────────────┬───────────────────────────┬─────────────────┬────────╮
│ File        │ Summary                   │     Urgency     │ Action │
├─────────────┼───────────────────────────┼─────────────────┼────────┤
│ scan.yml    │ Recently active .yml file │ ███░░░░░░░ 0.31 │  KEEP  │
│ database.py │ Recently active .py file  │ ██░░░░░░░░ 0.21 │  KEEP  │
╰─────────────┴───────────────────────────┴─────────────────┴────────╯

==============================================================
  TOP 3 ARCHIVAL RECOMMENDATIONS
==============================================================

  #1  scan.yml
      Urgency: 0.31  |  Action: KEEP
      Recently active .yml file
  ...
```

**Proves:** End-to-end pipeline — eBPF syscall capture → file scan → LLM/heuristic semantic analysis → Rich dashboard → ranked archival recommendations.

> **Optional:** Set `GROQ_API_KEY` before this step to enable live LLM summaries instead of heuristic fallbacks.

---

## Command 3 — Show persisted dashboard from SQLite

```bash
python -m src.cli.dashboard status
```

**Expected output:**
```
┌────────────────────────── IntentStore Dashboard ──────────────────────────┐
│ Files: 13   Size: 0.03 MB   Urgent: 0   Events: 5                         │
└───────────────────────────────────────────────────────────────────────────┘
╭─────────────┬───────────────────────────┬─────────────────┬────────╮
│ File        │ Summary                   │     Urgency     │ Action │
...
```

**Proves:** Metadata and scores persist in SQLite (`~/.intentstore/intentstore.db`) and are queryable after the demo run.

---

## Command 4 — Start the REST API

```bash
uvicorn src.api.main:app --port 8000 &
sleep 2
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
[DB] Initialized at ~/.intentstore/intentstore.db
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Proves:** IntentStore exposes a production-ready FastAPI layer for integration with SSM tooling and external orchestrators.

---

## Command 5 — Query live stats via REST

```bash
curl -s http://127.0.0.1:8000/status | python -m json.tool
```

**Expected output:**
```json
{
    "total_files": 13,
    "urgent_files": 0,
    "total_size_mb": 0.03,
    "total_events": 5
}
```

**Proves:** Storage intelligence is accessible programmatically — same data the CLI dashboard uses, available to kernel modules, agents, and automation.

---

## Bonus talking points (if time remains)

| Endpoint | Command | What it shows |
|---|---|---|
| All files + scores | `curl -s http://127.0.0.1:8000/files \| python -m json.tool \| head -30` | Full semantic metadata per file |
| High-urgency report | `curl -s "http://127.0.0.1:8000/report?threshold=0.3" \| python -m json.tool` | Archival candidates above threshold |
| Trigger remote scan | `curl -s -X POST http://127.0.0.1:8000/scan -H "Content-Type: application/json" -d '{"path":"."}'` | On-demand scan via API |

**API docs (auto-generated):** http://127.0.0.1:8000/docs

---

## Demo checklist

- [ ] Run from project root
- [ ] Terminal width ≥ 80 columns (for Rich tables)
- [ ] Commands 1–3 take ~60 seconds; commands 4–5 take ~30 seconds
- [ ] Mention SAE formula: urgency combines semantic score, access entropy, and future relevance (see README)
- [ ] Highlight eBPF → SQLite → LLM → REST as the full SSM intelligence stack
