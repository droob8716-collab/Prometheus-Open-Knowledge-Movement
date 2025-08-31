import hashlib
from pathlib import Path
from datetime import datetime

def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def guess_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(('.txt', '.md')):
        return 'text'
    if lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return 'image'
    if lower.endswith(('.pdf', )):
        return 'pdf'
    if lower.endswith(('.mp3', '.wav', '.m4a', '.flac', '.ogg')):
        return 'audio'
    if lower.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        return 'video'
    return 'binary'

def extract_text_stub(content: bytes, content_type: str) -> str:
    # Minimal extractor: for text files, decode; otherwise return empty string.
    if content_type == 'text':
        try:
            return content.decode('utf-8', errors='ignore')
        except Exception:
            return ''
    return ''
