import base64
import hashlib
import os
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings

IV_LEN = 12
TAG_LEN = 16

def _get_derived_key() -> bytes:
    raw = (settings.ENCRYPTION_KEY or settings.JWT_SECRET or "").encode("utf-8")
    return hashlib.sha256(raw).digest()

def encrypt(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypts plaintext using AES-256-GCM.
    Returns base64(iv || tag || ct) matching Node crypto.js.
    """
    if plaintext is None or plaintext == "":
        return None
    key = _get_derived_key()
    iv = os.urandom(IV_LEN)
    aesgcm = AESGCM(key)
    # cryptography AESGCM.encrypt returns (ciphertext + tag)
    ct_and_tag = aesgcm.encrypt(iv, str(plaintext).encode("utf-8"), None)
    ct = ct_and_tag[:-TAG_LEN]
    tag = ct_and_tag[-TAG_LEN:]
    
    # Pack as iv + tag + ct to match Node layout
    packed = iv + tag + ct
    return base64.b64encode(packed).decode("utf-8")

def decrypt(ciphertext_b64: Optional[str]) -> Optional[str]:
    """
    Decrypts base64(iv || tag || ct) encrypted by either Node or Python.
    """
    if not ciphertext_b64:
        return None
    try:
        data = base64.b64decode(ciphertext_b64)
        if len(data) < IV_LEN + TAG_LEN + 1:
            return None
        iv = data[:IV_LEN]
        tag = data[IV_LEN:IV_LEN + TAG_LEN]
        ct = data[IV_LEN + TAG_LEN:]
        
        # cryptography AESGCM expects (ciphertext + tag)
        ct_and_tag = ct + tag
        key = _get_derived_key()
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(iv, ct_and_tag, None)
        return decrypted.decode("utf-8")
    except Exception as e:
        print(f"[crypto] Decrypt error: {e}")
        return None

def mask_secret(s: Optional[str]) -> str:
    """Masks secret keeping first 4 and last 4 characters."""
    if not s:
        return ""
    str_val = str(s)
    if len(str_val) <= 8:
        return "••••••••"
    return f"{str_val[:4]}••••••••{str_val[-4:]}"

def hash_api_key(plain: str) -> str:
    """Computes SHA-256 hex digest of plain API key."""
    return hashlib.sha256(str(plain).encode("utf-8")).hexdigest()
