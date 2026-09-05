import base64
import os
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def _get_fernet() -> Fernet:
    """
    Derive a deterministic Fernet key from the Django SECRET_KEY.
    """
    secret = settings.SECRET_KEY.encode()
    salt = b'v4-studio-salt' # Fixed salt for deterministic key derivation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    return Fernet(key)

def encrypt_string(plaintext: str) -> str:
    """
    Encrypts a string using AES (Fernet).
    """
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()

def decrypt_string(ciphertext: str) -> str:
    """
    Decrypts a string that was encrypted with encrypt_string.
    """
    if not ciphertext:
        return ""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
