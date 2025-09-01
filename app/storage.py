# storage.py
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Dict, List, Optional

class Ledgers:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", "./seeds"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_fp = self.data_dir / "raw.jsonl"
        self.ver_fp = self.data_dir / "verified.jsonl"
        for fp in (self.raw_fp, self.ver_fp):
            if not fp.exists():
                fp.write_text("")

    def append_raw(self, rec: Dict) -> None:
        with self.raw_fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def append_verified(self, rec: Dict) -> None:
        with self.ver_fp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def find_doc(self, cid: str) -> Optional[Dict]:
        for fp in (self.raw_fp, self.ver_fp):
            with fp.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    if obj.get("cid") == cid:
                        return obj
        return None

    def search(self, q: str, limit: int = 10) -> List[Dict]:
        terms = [t for t in re.split(r"\W+", q.lower()) if t]
        scored = []
        with self.raw_fp.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                text = (obj.get("text") or "").lower()
                score = sum(text.count(t) for t in terms)
                if score:
                    obj["_score"] = score
                    scored.append(obj)
        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:limit]

    @staticmethod
    def now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())