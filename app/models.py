from typing import List, Optional
from pydantic import BaseModel, Field

class IngestResponse(BaseModel):
    cid: str
    sha256: str
    title: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = "CC-BY-SA-4.0"

class DocMeta(BaseModel):
    cid: str
    sha256: str
    title: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    content_type: Optional[str] = None
    path: Optional[str] = None
    ingested_at: str

class SearchHit(BaseModel):
    cid: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    score: float

class VerifyProposal(BaseModel):
    summary: str = Field(..., description="Concise statement being verified")
    evidence_cids: List[str] = Field(default_factory=list)
    method: str = "peer_review"

class VerifyVote(BaseModel):
    claim_id: int
    reviewer: str
    decision: str  # verified|contested|rejected
    notes: Optional[str] = None
