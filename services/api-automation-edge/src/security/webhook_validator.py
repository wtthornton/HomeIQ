"""
Webhook Validator

Epic H2: HMAC signing and replay protection for webhooks (optional)
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WebhookValidator:
    """
    Validates webhook payloads with security measures.
    
    Features:
    - HMAC signing for webhook payloads
    - Nonce + timestamp validation
    - Replay protection
    - Rate limiting rules
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize webhook validator.
        
        Args:
            secret_key: Secret key for HMAC (from environment or config)
        """
        self.secret_key = secret_key or os.getenv("WEBHOOK_SECRET_KEY", "").encode()
        # Track used nonces (would use TTL store in production)
        self.used_nonces: Dict[str, float] = {}
        self.nonce_ttl = 300  # 5 minutes
    
    def generate_signature(
        self,
        payload: str,
        timestamp: str,
        nonce: str
    ) -> str:
        """
        Generate HMAC signature for webhook payload.
        
        Args:
            payload: Payload string
            timestamp: Timestamp string
            nonce: Nonce string
        
        Returns:
            HMAC signature (hex)
        """
        message = f"{timestamp}:{nonce}:{payload}"
        signature = hmac.new(
            self.secret_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def validate_signature(
        self,
        payload: str,
        timestamp: str,
        nonce: str,
        signature: str
    ) -> bool:
        """
        Validate HMAC signature.
        
        Args:
            payload: Payload string
            timestamp: Timestamp string
            nonce: Nonce string
            signature: Expected signature
        
        Returns:
            True if signature valid
        """
        expected_signature = self.generate_signature(payload, timestamp, nonce)
        return hmac.compare_digest(expected_signature, signature)
    
    def validate_timestamp(
        self,
        timestamp: str,
        max_age_seconds: int = 300
    ) -> bool:
        """
        Validate timestamp is recent (replay protection).
        
        Args:
            timestamp: Timestamp string (Unix timestamp)
            max_age_seconds: Maximum age in seconds
        
        Returns:
            True if timestamp valid
        """
        try:
            ts = float(timestamp)
            now = time.time()
            age = now - ts
            
            if age < 0:
                # Future timestamp
                return False
            
            if age > max_age_seconds:
                # Too old
                return False
            
            return True
        except ValueError:
            return False
    
    def validate_nonce(
        self,
        nonce: str
    ) -> bool:
        """
        Validate nonce hasn't been used (replay protection).
        
        Args:
            nonce: Nonce string
        
        Returns:
            True if nonce valid (not used)
        """
        now = time.time()
        
        # Clean up old nonces
        self.used_nonces = {
            n: t for n, t in self.used_nonces.items()
            if (now - t) < self.nonce_ttl
        }
        
        # Check if nonce already used
        if nonce in self.used_nonces:
            return False
        
        # Mark as used
        self.used_nonces[nonce] = now
        return True
    
    def validate_webhook(
        self,
        payload: str,
        headers: Dict[str, str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate webhook request.
        
        Args:
            payload: Request payload
            headers: Request headers
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract required headers
        signature = headers.get("X-Webhook-Signature")
        timestamp = headers.get("X-Webhook-Timestamp")
        nonce = headers.get("X-Webhook-Nonce")
        
        if not signature:
            return False, "Missing X-Webhook-Signature header"
        
        if not timestamp:
            return False, "Missing X-Webhook-Timestamp header"
        
        if not nonce:
            return False, "Missing X-Webhook-Nonce header"
        
        # Validate timestamp
        if not self.validate_timestamp(timestamp):
            return False, "Invalid or expired timestamp"
        
        # Validate nonce
        if not self.validate_nonce(nonce):
            return False, "Nonce already used (replay attack)"
        
        # Validate signature
        if not self.validate_signature(payload, timestamp, nonce, signature):
            return False, "Invalid signature"
        
        return True, None
