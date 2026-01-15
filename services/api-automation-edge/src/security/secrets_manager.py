"""
Secrets Management

Epic H1: Encrypt tokens at rest and redact in logs
"""

import base64
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages secrets with encryption at rest.
    
    Features:
    - Encrypt tokens at rest
    - Redact in logs
    - Token rotation support
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize secrets manager.
        
        Args:
            encryption_key: Optional encryption key (generates if not provided)
        """
        if encryption_key:
            self.key = encryption_key
        else:
            # Generate or load key from environment
            key_env = os.getenv("SECRETS_ENCRYPTION_KEY")
            if key_env:
                self.key = base64.urlsafe_b64decode(key_env.encode())
            else:
                # Generate key from password (not secure for production - should use proper key management)
                password = os.getenv("SECRETS_PASSWORD", "default-password-change-in-production")
                salt = os.getenv("SECRETS_SALT", "default-salt").encode()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                self.key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        self.cipher = Fernet(base64.urlsafe_b64encode(self.key))
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext.
        
        Args:
            plaintext: Plaintext string
        
        Returns:
            Encrypted string (base64)
        """
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext.
        
        Args:
            ciphertext: Encrypted string (base64)
        
        Returns:
            Decrypted string
        """
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self.cipher.decrypt(encrypted)
        return decrypted.decode()
    
    def store_token(self, token_id: str, token: str) -> str:
        """
        Store encrypted token.
        
        Args:
            token_id: Token identifier
            token: Plaintext token
        
        Returns:
            Encrypted token string
        """
        encrypted = self.encrypt(token)
        logger.info(f"Stored encrypted token: {token_id}")
        return encrypted
    
    def retrieve_token(self, encrypted_token: str) -> str:
        """
        Retrieve and decrypt token.
        
        Args:
            encrypted_token: Encrypted token string
        
        Returns:
            Decrypted token
        """
        return self.decrypt(encrypted_token)
    
    def redact_in_logs(self, value: str) -> str:
        """
        Redact value in logs (simple truncation).
        
        Args:
            value: Value to redact
        
        Returns:
            Redacted string
        """
        if len(value) > 8:
            return value[:4] + "..." + value[-4:]
        return "[REDACTED]"
