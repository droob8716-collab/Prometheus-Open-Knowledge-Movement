from __future__ import annotations
import json, os, time, hashlib
from pathlib import Path
from typing import Dict, List, Optional

class VerifyStore:
    def __init__(self, data_dir: Optional[str] = None):
        base = Path(data_dir or os.getenv("DATA_DIR", "./seeds"))
        base.mkdir(parents=True, exist_ok=True)
        self.claims_fp = base / "claims.jsonl"
        self.votes_fp  = base / "votes.jsonl"
        for fp in (self.claims_fp, self.votes_fp):
            if not fp.exists():
                fp.write_text("")

    @staticmethod
    def now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @staticmethod
    def mk_claim_id(text: str) -> str:
        h = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return f"clm_{h}"

    def propose(self, text: str, cid: Optional[str] = None, sources: Optional[List[str]] = None) -> Dict:
        claim = {
            "claim_id": self.mk_claim_id(text),
            "text": text,
            "cid": cid,
            "sources": sources or [],
            "ts": self.now_iso(),
        }
        with self.claims_fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(claim, ensure_ascii=False) + "\n")
        return claim

    def list_claims(self, limit: int = 50) -> List[Dict]:
        rows: List[Dict] = []
        with self.claims_fp.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        rows.reverse()  # newest first
        return rows[:limit]

    def get_claim(self, claim_id: str) -> Optional[Dict]:
        with self.claims_fp.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                if obj.get("claim_id") == claim_id:
                    return obj
        return None

    def vote(self, claim_id: str, value: int, voter: Optional[str] = None) -> Dict:
        if value not in (-1, 1):
            raise ValueError("value must be +1 or -1")
        vote = {
            "claim_id": claim_id,
            "value": int(value),
            "voter": voter or "anon",
            "ts": self.now_iso(),
        }
        with self.votes_fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(vote, ensure_ascii=False) + "\n")
        return vote

    def tally(self, claim_id: str) -> Dict:
        up = down = 0
        with self.votes_fp.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                v = json.loads(line)
                if v.get("claim_id") != claim_id:
                    continue
                if int(v.get("value", 0)) > 0:
                    up += 1
                else:
                    down += 1
        return {"up": up, "down": down, "net": up - down}

    def export(self) -> Dict:
        def readall(fp: Path) -> List[Dict]:
            out: List[Dict] = []
            with fp.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        out.append(json.loads(line))
            return out
        return {"claims": readall(self.claims_fp), "votes": readall(self.votes_fp)}

    def import_(self, payload: Dict) -> Dict:
        added = {"claims": 0, "votes": 0}
        for key, fp in (("claims", self.claims_fp), ("votes", self.votes_fp)):
            for obj in payload.get(key, []) or []:
                with fp.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                added[key] += 1
        return added
