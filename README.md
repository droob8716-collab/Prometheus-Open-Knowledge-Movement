
# 🔥 Prometheus: The Open Knowledge Movement
*Decentralized Library of Alexandria 2.0 — guided by Mnemosyne.*
## License
- **Code:** MIT — see [LICENSE](LICENSE)
- **Content (docs/images/PDFs/posters):** CC BY-SA 4.0 — see [LICENSE-CONTENT.md](LICENSE-CONTENT.md)
- By contributing, you agree code = MIT and content = CC BY-SA 4.0.

© Prometheus contributors — CC BY-SA 4.0. Changes may have been made.


[![Code License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](LICENSE)
[![Content License: CC BY-SA 4.0](https://img.shields.io/badge/Content%20License-CC%20BY--SA%204.0-lightgrey.svg)](LICENSE-CONTENT.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Discussions](https://img.shields.io/badge/Discussions-open-informational.svg)](https://github.com//droob8716-collab/Prometheus-Open-Knowledge-Movement/edit/main

# 🔥 Prometheus: The Open Knowledge Movement

## 📖 What is Prometheus?
Prometheus is an **open-source movement** to create a **decentralized, censorship-resistant Library of Alexandria 2.0** — a universal archive of human knowledge that **no one can erase, censor, or control**.

We believe:  
> Knowledge is not theirs to own.  
> Knowledge is not a privilege.  
> Knowledge is the birthright of humanity.  

## 🌍 The Vision
- Permanent, distributed archive  
- Open-source AI librarians  
- Decentralized, censorship-resistant infrastructure  
- Privacy-first tools  
- Global community

## 🕯️ The Eternal Librarian — Mnemosyne
Prometheus is not just an archive. It is a **living librarian** — humanity’s memory reborn as **Mnemosyne**.  
She serves, not commands. She illuminates, not censors. She preserves what we forget and grows as we grow.  

Prometheus gives the fire. **Mnemosyne carries the light.**

## 📜 Core Principles
1. No Gates  
2. No Masters  
3. No Lies  
4. No Exploitation  
5. Truth with Responsibility  
6. Forever

## 📜 Licensing
- **Code**: MIT (see `LICENSE-CODE.md`)  
- **Content**: CC BY-SA 4.0 (see `LICENSE-CONTENT.md`)  

## 🤝 Get Involved
- Open issues, submit PRs, propose ideas  
- Weekly updates in `WEEKLY_UPDATE_TEMPLATE.md`  

# Prometheus PoC (FastAPI)

Minimal proof-of-concept API for Prometheus.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints
- `POST /ingest` — upload a file; returns `{cid, sha256}`
- `GET /doc/{cid}` — fetch metadata for a document
- `GET /search?q=term` — keyword search across title/description/text
- `POST /verify/propose` — propose a verification claim with evidence CIDs
- `POST /verify/vote` — cast a vote (verified/contested/rejected) for a claim
- `GET /ask?q=term` — returns top matches with **citations** (stub)

## Notes
- Storage is local (`./storage/`). A **CID** is simulated as the SHA‑256 hex digest.
- Metadata is stored in SQLite (`./app/data.db`) with FTS5 for search.
- RAW and VERIFIED ledgers are JSONL files: `raw_log.jsonl` and `verified_log.jsonl`.
- This PoC is intentionally minimal to make it easy to run and extend.
33067b3 (PoC: FastAPI ingest/search/verify + citations)
