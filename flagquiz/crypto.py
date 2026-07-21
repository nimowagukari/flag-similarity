import base64
import hashlib

from cryptography.fernet import Fernet


def build_fernet(secret_key: str) -> Fernet:
    """SECRET_KEYからFernet鍵を導出する。専用の鍵管理を増やさないための簡略化。"""
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
