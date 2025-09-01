from __future__ import annotations
import hashlib
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from pydantic import BaseModel

from .ipfs_client import IPFSClient
from .ingestion.pdf_ocr import extract_text_from_pdf
from .storage import Ledgers
from .verify_store import VerifyStore  # <-- new

app = FastAPI(title="Prometheus – Open Knowledge Movement")  # <-- must be BEFORE any @app.route

ledgers = Ledgers()
ipfs = IPFSClient()
verifier = VerifyStore()  # <-- created once, after app exists



from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from pathlib import Path
import json

from .db import init_db, get_conn
from .models import IngestResponse, DocMeta, SearchHit, VerifyProposal, VerifyVote
from .utils import sha256_bytes, now_iso, guess_content_type, extract_text_stub

from .ipfs_client import IPFSClient
from .storage import Ledgers
from .ingestion.pdf_ocr import extract_text_from_pdf

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body

from fastapi import Body
from pathlib import Path
from .verify_store import VerifyStore
from pydantic import BaseModel

# near the top
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from fastapi import HTTPException

from typing import Optional, Union
from fastapi import HTTPException
from pydantic import BaseModel

from typing import Optional, Union
from fastapi import HTTPException
from pydantic import BaseModel

class VoteIn(BaseModel):
    claim_id: Union[int, str]
    reviewer: Optional[str] = None
    decision: Optional[str] = None   # approve/reject/upvote/downvote/yes/no
    value: Optional[int] = None      # +1 or -1

def _normalize_vote(v: VoteIn) -> tuple[str, int, str]:
    cid = str(v.claim_id)
    voter = v.reviewer or "anon"

    # If numeric provided, honor it first
    if v.value in (-1, 1):
        return cid, int(v.value), voter

    # Otherwise map decision strings to +1 / -1
    key = (v.decision or "").strip().lower()
    pos = {"approve", "accept", "upvote", "yes", "y", "true", "1"}
    neg = {"reject", "downvote", "no", "n", "false", "-1"}
    if key in pos: return cid, 1, voter
    if key in neg: return cid, -1, voter

    raise HTTPException(400, "Invalid decision. Use approve/reject (or value +1/-1).")




@app.post("/verify/vote")
async def verify_vote(v: VoteIn):
    claim_id, val, voter = _normalize_vote(v)
    rec = verifier.vote(claim_id=claim_id, value=val, voter=voter)
    tally = verifier.tally(claim_id)
    promoted = False
    try:
        if tally.get("net", 0) >= 3:
            claim = verifier.get_claim(claim_id)
            if claim:
                ledgers.append_verified({
                    "cid": claim.get("cid"),
                    "kind": "VERIFIED",
                    "title": (claim.get("text") or "claim")[:80],
                    "text": claim.get("text") or "",
                    "meta": {"sources": claim.get("sources", [])},
                    "ts": ledgers.now_iso(),
                })
                promoted = True
    except Exception:
        pass
    return {"vote": rec, "tally": tally, "promoted": promoted}


class ClaimIn(BaseModel):
    # allow sending either 'summary' (old) or 'text' (new)
    model_config = ConfigDict(populate_by_name=True, extra='ignore')
    text: Optional[str] = Field(default=None, description="Claim text")
    summary: Optional[str] = Field(default=None, description="Alias of text")
    cid: Optional[str] = None
    sources: List[str] = []

@app.post("/verify/propose")
async def verify_propose(payload: ClaimIn):
    claim_text = payload.text or payload.summary
    if not claim_text:
        raise HTTPException(status_code=422, detail="Provide 'text' or 'summary'.")
    return verifier.propose(text=claim_text, cid=payload.cid, sources=payload.sources)




APP_DIR = Path(__file__).parent
STORAGE_DIR = APP_DIR.parent / "storage"
RAW_LOG = APP_DIR / "raw_log.jsonl"
VERIFIED_LOG = APP_DIR / "verified_log.jsonl"


from fastapi.responses import HTMLResponse

@app.get("/export/seed")
def export_seed():
    conn = get_conn(); cur = conn.cursor()
    docs = cur.execute("""
      SELECT cid, sha256, title, description, license, content_type, ingested_at
      FROM documents
    """).fetchall()
    claims = cur.execute("""
      SELECT id, summary, status, evidence_cids
      FROM claims ORDER BY id
    """).fetchall()
    conn.close()
    return {"docs": [dict(r) for r in docs], "claims": [dict(r) for r in claims]}

@app.post("/import/seed")
def import_seed(payload: dict = Body(...)):
    conn = get_conn(); cur = conn.cursor()
    imported = {"docs": 0, "claims": 0, "claim_id_map": {}}

    # documents (upsert)
    import json as _json
    for d in (payload.get("docs") or []):
        cid = d.get("cid"); 
        if not cid: 
            continue
        cur.execute("""INSERT OR REPLACE INTO documents
                       (cid, sha256, title, description, license, content_type, path, ingested_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cid, d.get("sha256",""), d.get("title"), d.get("description"),
                     d.get("license"), d.get("content_type"),
                     str((Path(__file__).parent.parent / "storage" / f"{cid}").resolve()),
                     d.get("ingested_at") or now_iso()))
        cur.execute("DELETE FROM documents_fts WHERE cid=?", (cid,))
        cur.execute("INSERT INTO documents_fts(cid, title, description, text) VALUES (?, ?, ?, ?)",
                    (cid, d.get("title") or "", d.get("description") or "", ""))
        imported["docs"] += 1

    # claims (preserve id if free; otherwise remap)
    for c in (payload.get("claims") or []):
        keep_id = c.get("id")
        blob = _json.dumps(c.get("evidence_cids") or [])
        if keep_id is not None:
            exists = cur.execute("SELECT 1 FROM claims WHERE id=?", (keep_id,)).fetchone()
            if exists:
                cur.execute("INSERT INTO claims (summary, method, status, evidence_cids) VALUES (?,?,?,?)",
                            (c.get("summary",""), c.get("method","peer_review"), c.get("status","pending"), blob))
                new_id = cur.lastrowid
            else:
                cur.execute("INSERT INTO claims (id, summary, method, status, evidence_cids) VALUES (?,?,?,?,?)",
                            (keep_id, c.get("summary",""), c.get("method","peer_review"), c.get("status","pending"), blob))
                new_id = keep_id
            if new_id != keep_id:
                imported["claim_id_map"][keep_id] = new_id
        else:
            cur.execute("INSERT INTO claims (summary, method, status, evidence_cids) VALUES (?,?,?,?)",
                        (c.get("summary",""), c.get("method","peer_review"), c.get("status","pending"), blob))
        imported["claims"] += 1

    conn.commit(); conn.close()
    return imported


@app.get("/export/seed")
def export_seed():
    conn = get_conn(); cur = conn.cursor()
    docs = cur.execute("""
      SELECT cid, sha256, title, description, license, content_type, ingested_at
      FROM documents
    """).fetchall()
    claims = cur.execute("""
      SELECT id, summary, status, evidence_cids
      FROM claims ORDER BY id
    """).fetchall()
    conn.close()
    # jsonify rows
    def rowdicts(rows): return [dict(zip(r.keys(), tuple(r))) for r in rows]
    return {"docs": rowdicts(docs), "claims": rowdicts(claims)}


# --- helpers & home ---
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return '<h2>Prometheus PoC</h2><p><a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>'

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# --- claims listing ---
@app.get("/claims")
def list_claims():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT id, summary, status, evidence_cids FROM claims ORDER BY id DESC").fetchall()
    conn.close()
    out = []
    for r in rows:
        item = dict(r)
        try:
            item["evidence_cids"] = [] if not item["evidence_cids"] else __import__("json").loads(item["evidence_cids"])
        except Exception:
            item["evidence_cids"] = []
        out.append(item)
    return out

@app.get("/claims/{claim_id}")
def get_claim(claim_id: int):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id, summary, status, evidence_cids FROM claims WHERE id=?", (claim_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    item = dict(row)
    try:
        item["evidence_cids"] = [] if not item["evidence_cids"] else __import__("json").loads(item["evidence_cids"])
    except Exception:
        item["evidence_cids"] = []
    return item

# --- make /ask prefer VERIFIED evidence ---
def _verified_evidence_cids():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT evidence_cids FROM claims WHERE status='verified'").fetchall()
    conn.close()
    import json
    cids = set()
    for (blob,) in rows:
        if blob:
            try:
                for c in json.loads(blob):
                    cids.add(c)
            except Exception:
                pass
    return cids

# --- make /ask prefer VERIFIED evidence ---
def _verified_evidence_cids():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT evidence_cids FROM claims WHERE status='verified'").fetchall()
    conn.close()
    import json
    cids = set()
    for (blob,) in rows:
        if blob:
            try:
                for c in json.loads(blob):
                    cids.add(c)
            except Exception:
                pass
    return cids

@app.get("/ask")
def ask(q: str, limit: int = 3):
    hits = search(q=q, limit=limit)  # reuse endpoint function
    verified = _verified_evidence_cids()
    hits_sorted = sorted(hits, key=lambda h: (h.cid not in verified,), reverse=False)
    citations = [{"cid": h.cid, "title": h.title, "verified": (h.cid in verified)} for h in hits_sorted]
    return {
        "answer": "PoC: Mnemosyne retrieves and cites sources. VERIFIED items appear first.",
        "citations": citations
    }

@app.on_event("startup")
def _startup():
    init_db()
    STORAGE_DIR.mkdir(exist_ok=True)
    if not RAW_LOG.exists():
        RAW_LOG.touch()
    if not VERIFIED_LOG.exists():
        VERIFIED_LOG.touch()

@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    license: Optional[str] = Form("CC-BY-SA-4.0")
):
    data = await file.read()
    sha256 = sha256_bytes(data)
    cid = sha256  # simple PoC: use sha256 as CID
    ct = guess_content_type(file.filename or "binary")

    # Save file by CID (preserve original extension if present)
    ext = Path(file.filename).suffix if file.filename else ""
    out_path = STORAGE_DIR / f"{cid}{ext}"
    out_path.write_bytes(data)

    # Extract text for FTS
    extracted_text = extract_text_stub(data, ct)

    # DB write
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO documents
        (cid, sha256, title, description, license, content_type, path, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cid, sha256, title, description, license, ct, str(out_path), now_iso())
    )
    cur.execute(
        """INSERT INTO documents_fts(cid, title, description, text)
        VALUES (?, ?, ?, ?)
        """, (cid, title or '', description or '', extracted_text or '')
    )
    conn.commit()
    conn.close()

    # RAW ledger append
    raw_entry = {
        "type": "ingest",
        "cid": cid,
        "sha256": sha256,
        "title": title,
        "license": license,
        "content_type": ct,
        "path": str(out_path),
        "ingested_at": now_iso()
    }
    with RAW_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(raw_entry) + "\n")

    return IngestResponse(cid=cid, sha256=sha256, title=title, description=description, license=license)

@app.get("/doc/{cid}", response_model=DocMeta)
def get_doc(cid: str):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM documents WHERE cid=?", (cid,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocMeta(**dict(row))

@app.get("/search", response_model=List[SearchHit])
def search(q: str, limit: int = 10):
    conn = get_conn()
    cur = conn.cursor()
    # Simple FTS query
    rows = cur.execute(
        """
        SELECT d.cid, d.title, snippet(documents_fts, 3, '<b>', '</b>', '…', 10) AS snip
        FROM documents_fts f
        JOIN documents d ON d.cid = f.cid
        WHERE documents_fts MATCH ?
        LIMIT ?
        """, (q, limit)
    ).fetchall()
    conn.close()
    hits = [SearchHit(cid=r[0], title=r[1], snippet=r[2], score=1.0) for r in rows]
    return hits

@app.post("/verify/propose")
def verify_propose(body: VerifyProposal):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO claims (summary, method, status, evidence_cids)
               VALUES (?, ?, 'pending', ?)""",
        (body.summary, body.method, json.dumps(body.evidence_cids))
    )
    claim_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Append to RAW log
    with RAW_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "verify_propose",
            "claim_id": claim_id,
            "summary": body.summary,
            "evidence_cids": body.evidence_cids,
            "at": now_iso()
        }) + "\n")

    return {"claim_id": claim_id, "status": "pending"}
\
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute("SELECT id, status FROM claims WHERE id=?", (vote.claim_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Claim not found")

    cur.execute(
        """INSERT INTO votes (claim_id, reviewer, decision, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
        (vote.claim_id, vote.reviewer, vote.decision, vote.notes, now_iso())
    )

    # PoC quorum: single vote decides
    new_status = vote.decision
    cur.execute("UPDATE claims SET status=? WHERE id=?", (new_status, vote.claim_id))
    conn.commit()
    conn.close()

    # VERIFIED ledger append (for verified only; include contested/rejected as audit too)
    with VERIFIED_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "type": "verify_result",
            "claim_id": vote.claim_id,
            "decision": new_status,
            "reviewer": vote.reviewer,
            "notes": vote.notes,
            "at": now_iso()
        }) + "\n")

    return {"claim_id": vote.claim_id, "status": new_status}

@app.get("/ask")
def ask(q: str, limit: int = 3):
    # Stub: just call search and return "answer" as a list of citations
    hits = search(q=q, limit=limit)
    citations = [{"cid": h.cid, "title": h.title} for h in hits]
    answer = {
        "answer": "This is a PoC. Mnemosyne would retrieve and cite sources. Here are the top citations.",
        "citations": citations
    }
    return JSONResponse(answer)
